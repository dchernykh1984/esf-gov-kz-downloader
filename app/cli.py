"""Command line entry point: download incoming documents and print them to PDF."""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app import api, labels, render, signing

DEFAULT_OUTPUT = Path("downloads")
NCANODE_URL_ENV = "ESF_NCANODE_URL"

_DATE_EXAMPLE = "2026-01-01T00:00:00+05:00"


class UsageError(RuntimeError):
    """Raised for input the user can fix."""


def moment(text: str) -> datetime:
    """Parse a timestamp, insisting on an explicit UTC offset.

    Without an offset the API would silently shift the period by several hours
    and drop documents at either edge, so an offset-less value is refused
    rather than guessed at.
    """
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"{text!r} is not a valid timestamp, expected e.g. {_DATE_EXAMPLE}"
        ) from None
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError(
            f"{text!r} has no time zone. Add the offset, e.g. {_DATE_EXAMPLE} "
            "(Kazakhstan is +05:00)."
        )
    return parsed


def statuses(allowed: tuple[str, ...]):
    """Build a parser for a comma-separated status list."""

    def parse(text: str) -> list[str]:
        chosen = [item.strip().upper() for item in text.split(",") if item.strip()]
        unknown = [item for item in chosen if item not in allowed]
        if unknown:
            raise argparse.ArgumentTypeError(
                f"unknown status {', '.join(unknown)}. Allowed: {', '.join(allowed)}"
            )
        return chosen

    return parse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="esf-download",
        description=(
            "Download incoming invoices (ESF) and acts (AWP) from the IS ESF API "
            "and render each one to PDF next to its original XML."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            f"Timestamps require an explicit UTC offset, e.g. {_DATE_EXAMPLE}.\n\n"
            "Invoice statuses:\n  "
            + "\n  ".join(_wrap(api.INVOICE_STATUSES))
            + "\n\nAct statuses:\n  "
            + "\n  ".join(_wrap(api.AWP_STATUSES))
            + "\n\nAll statuses are included unless --esf-status/--awp-status say "
            "otherwise.\nGive only the invoice dates to skip acts, or only the act "
            "dates to skip invoices."
        ),
    )

    parser.add_argument("--tin", required=True, help="BIN of the company to act for")
    parser.add_argument("--iin", required=True, help="IIN of the key holder")
    parser.add_argument(
        "--key", required=True, type=Path, help="path to the .p12 key container"
    )

    parser.add_argument("--esf-from", type=moment, help="invoices issued from")
    parser.add_argument("--esf-to", type=moment, help="invoices issued up to")
    parser.add_argument("--awp-from", type=moment, help="acts from")
    parser.add_argument("--awp-to", type=moment, help="acts up to")

    parser.add_argument(
        "--esf-status",
        type=statuses(api.INVOICE_STATUSES),
        default=list(api.INVOICE_STATUSES),
        help="comma-separated invoice statuses (default: all)",
    )
    parser.add_argument(
        "--awp-status",
        type=statuses(api.AWP_STATUSES),
        default=list(api.AWP_STATUSES),
        help="comma-separated act statuses (default: all)",
    )

    parser.add_argument(
        "--lang",
        choices=labels.LANGUAGES,
        default=labels.RUS,
        help="captions on the printed form (default: rus)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--ncanode-url",
        default=os.environ.get(NCANODE_URL_ENV, signing.DEFAULT_URL),
        help=f"NCANode base URL (env {NCANODE_URL_ENV}, default {signing.DEFAULT_URL})",
    )
    parser.add_argument(
        "--refetch",
        action="store_true",
        help="download again even when the XML is already on disk",
    )
    parser.add_argument(
        "--render-only",
        action="store_true",
        help="rebuild PDFs from XML already downloaded, without calling the API",
    )
    return parser


def _wrap(items: tuple[str, ...], per_line: int = 3) -> list[str]:
    return [
        ", ".join(items[start : start + per_line])
        for start in range(0, len(items), per_line)
    ]


@dataclass
class Tally:
    """What a run did, reported at the end."""

    written: int = 0
    skipped: int = 0
    failed: int = 0

    def report(self) -> str:
        return f"written {self.written}, skipped {self.skipped}, failed {self.failed}"


def _period(start: datetime | None, end: datetime | None, name: str):
    """Validate one of the two date pairs; returns the pair or None if unused."""
    if start is None and end is None:
        return None
    if start is None or end is None:
        raise UsageError(f"--{name}-from and --{name}-to must be given together")
    if start > end:
        raise UsageError(f"--{name}-from is later than --{name}-to")
    return start, end


def _target(out: Path, kind: str, status: str, registration_number: str) -> Path:
    """Where a document is filed.

    Status is part of the path so that a revoked or cancelled document can
    never be mistaken for a live one when the folder is handed to an
    accountant.
    """
    safe = registration_number.replace("/", "-") or "unknown"
    return out / kind / status.lower() / safe


def _store(document: api.Document, out: Path, language: str, tally: Tally) -> None:
    """Write one document's XML and PDF."""
    base = _target(out, document.kind, document.status, document.registration_number)
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".xml").write_text(document.body, encoding="utf-8")
    render.render(
        kind=document.kind,
        body=document.body,
        registration_number=document.registration_number,
        status=document.status,
        destination=base.with_suffix(".pdf"),
        language=language,
    )
    tally.written += 1


def _download(args: argparse.Namespace, tally: Tally) -> None:
    """Open a session, walk both document types, close the session."""
    # Everything that can be checked without the key is checked first, so a
    # bad period never costs the user a password prompt.
    esf = _period(args.esf_from, args.esf_to, "esf")
    awp = _period(args.awp_from, args.awp_to, "awp")
    if not args.key.is_file():
        raise UsageError(f"no key container at {args.key}")

    key_password = getpass.getpass("Key password: ")
    client = api.EsfApi()

    def sign(ticket: str) -> str:
        return signing.sign_xml(
            ticket, args.key, key_password, ncanode_url=args.ncanode_url
        )

    client.open_session(iin=args.iin, tin=args.tin, sign=sign)
    try:
        sources = []
        if esf:
            sources.append(
                client.incoming_invoices(esf[0], esf[1], args.esf_status),
            )
        if awp:
            sources.append(
                client.acts(awp[0], awp[1], args.awp_status, args.tin),
            )

        for source in sources:
            for document in source:
                base = _target(
                    args.out,
                    document.kind,
                    document.status,
                    document.registration_number,
                )
                if not args.refetch and base.with_suffix(".xml").exists():
                    tally.skipped += 1
                    continue
                try:
                    _store(document, args.out, args.lang, tally)
                except (render.RenderError, OSError) as exc:
                    tally.failed += 1
                    print(
                        f"! {document.registration_number}: {exc}",
                        file=sys.stderr,
                    )
    finally:
        client.close_session()


def _render_only(args: argparse.Namespace, tally: Tally) -> None:
    """Rebuild PDFs from the XML already on disk."""
    for path in sorted(args.out.rglob("*.xml")):
        kind = path.relative_to(args.out).parts[0]
        try:
            render.render(
                kind=kind,
                body=path.read_text(encoding="utf-8"),
                registration_number=path.stem,
                status=path.parent.name.upper(),
                destination=path.with_suffix(".pdf"),
                language=args.lang,
            )
            tally.written += 1
        except (render.RenderError, OSError) as exc:
            tally.failed += 1
            print(f"! {path.name}: {exc}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if not (argv if argv is not None else sys.argv[1:]):
        parser.print_help()
        return 2
    args = parser.parse_args(argv)

    tally = Tally()
    try:
        if args.render_only:
            _render_only(args, tally)
        else:
            if not (args.esf_from or args.esf_to or args.awp_from or args.awp_to):
                raise UsageError(
                    "give a period: --esf-from/--esf-to and/or --awp-from/--awp-to"
                )
            _download(args, tally)
    except (UsageError, signing.SigningError, api.ApiError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130

    print(tally.report())
    return 1 if tally.failed else 0
