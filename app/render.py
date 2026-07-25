"""Rendering document XML into a printable PDF.

The blank is described as an HTML template and converted with xhtml2pdf, which
is pure python: the script runs on a locked-down corporate Windows machine
where installing the system libraries weasyprint needs is not practical.
"""

from __future__ import annotations

import io
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

from app.documents import parse_document
from app.labels import RUS, label

_ROOT = Path(__file__).resolve().parent
FONT_DIR = _ROOT.parent / "fonts"
TEMPLATE_DIR = _ROOT / "templates"

TEMPLATES = {"esf": "invoice.html", "awp": "awp.html"}

# Placeholder for an absent value. Besides matching the paper blank, it keeps
# every column non-empty: xhtml2pdf collapses a fully empty column and lets
# the neighbouring text bleed across it.
DASH = "\u2014"

# The document element sits inside a container in some exports.
_DOCUMENT_TAGS = ("invoice", "awp")


class RenderError(RuntimeError):
    """Raised when a document could not be turned into a PDF."""


def _environment() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _resolve_asset(uri: str, _rel: str) -> str:
    """Map the font URLs used by the stylesheet onto real paths."""
    if uri.startswith("fonts/"):
        return str(FONT_DIR / uri.removeprefix("fonts/"))
    return uri


def render(
    kind: str,
    body: str,
    registration_number: str,
    status: str,
    destination: Path,
    language: str = RUS,
) -> None:
    """Write the printed form for one document to `destination`."""
    template_name = TEMPLATES.get(kind)
    if template_name is None:
        raise RenderError(f"no template for document kind {kind!r}")

    html = (
        _environment()
        .get_template(template_name)
        .render(
            doc=parse_document(body, _DOCUMENT_TAGS),
            registration_number=registration_number,
            status=status,
            L=lambda key: label(key, language),
            DASH=DASH,
        )
    )

    buffer = io.BytesIO()
    result = pisa.CreatePDF(
        html, dest=buffer, encoding="utf-8", link_callback=_resolve_asset
    )
    if result.err:
        raise RenderError(f"xhtml2pdf reported {result.err} error(s)")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(buffer.getvalue())
