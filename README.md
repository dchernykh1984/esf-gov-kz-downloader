# esf-gov-kz-downloader

A small script that downloads documents from Kazakhstan's IS ESF
(Информационная система электронных счетов-фактур) through its SOAP API at
`https://esf.gov.kz:8443/esf-web/ws/api1`.

It runs on a locked-down corporate Windows machine, so everything except the
signature service is plain pip: PDFs are produced with `xhtml2pdf`, which needs
no system libraries.

## How the API works

The API is SOAP (Apache CXF), not REST. Authentication is a two-step flow that
uses the same NCA RK signature key you log into the web portal with:

1. `AuthService.createAuthTicket(iin)` returns an unsigned XML ticket.
2. You sign that ticket as XMLDsig and pass it to
   `SessionService.createSessionSigned(tin, signedAuthTicket)`, which returns a
   `sessionId`.
3. Every subsequent call carries that `sessionId`.

The older `createSession` method, which took a bare certificate, stopped
working for GOST 2015 keys on 1 August 2023.

Invoices come back from `InvoiceService.queryInvoice`, `queryInvoiceById` and
`queryUpdates` as full XML in the `invoiceBody` field. The API does not render
PDFs.

## Requirements

- Python 3.14
- [uv](https://docs.astral.sh/uv/)
- An NCA RK signature key (`.p12`) registered in IS ESF
- [NCANode](https://github.com/ncanode-kz/NCANode) running locally. Keys issued
  since 2023 use GOST 2015, which no pure-python library can sign, so the
  ticket is signed there. It ships as a standalone zip (needs a JRE) as well as
  a Docker image; the script only needs its HTTP endpoint.

## Setup

### 1. Clone the project

```sh
git clone git@github.com:dchernykh1984/esf-gov-kz-downloader.git
cd esf-gov-kz-downloader
```

### 2. Install dependencies

```sh
uv sync
```

### 3. Set up pre-commit hooks

```sh
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
```

The second command installs the commitizen hook that validates commit
messages. To run every hook against the whole tree:

```sh
uv run pre-commit run --all-files
```

## Usage

```sh
uv run python main.py --help
```

Run with no arguments to get the same help, including the full list of
statuses each document type accepts.

Download last month's incoming invoices and acts:

```sh
uv run python main.py \
  --tin 123456789021 --iin 123456789011 --key ~/keys/GOSTKNCA_....p12 \
  --esf-from 2026-06-01T00:00:00+05:00 --esf-to 2026-06-30T23:59:59+05:00 \
  --awp-from 2026-06-01T00:00:00+05:00 --awp-to 2026-06-30T23:59:59+05:00
```

The key password is asked for interactively; it is never taken from an
argument, where it would land in the shell history and be visible in `ps`.

### Options that matter

| Option | Effect |
|---|---|
| `--esf-from/--esf-to` | Period for invoices, by **issue date** |
| `--awp-from/--awp-to` | Period for acts. The API does not document which date it filters on |
| `--esf-status`, `--awp-status` | Comma-separated; all statuses by default |
| `--lang` | `rus` (default) or `kaz+rus` for bilingual captions |
| `--refetch` | Download again even when the XML is already on disk |
| `--render-only` | Rebuild PDFs from saved XML without calling the API |
| `--out` | Output directory, `downloads/` by default |

Giving only the invoice dates skips acts, and vice versa.

**Timestamps need an explicit UTC offset** (`+05:00` for Kazakhstan since
1 March 2024). A value without one is refused rather than guessed at, because
the wrong offset silently shifts the period and drops documents at either edge.

### Output layout

```
downloads/
  esf/delivered/ESF-123456789021-20260615-12345678.xml
  esf/delivered/ESF-123456789021-20260615-12345678.pdf
  esf/canceled/ESF-...
  awp/confirmed/AWP-...
```

Documents are filed under their status so a revoked or cancelled one cannot be
mistaken for a live one. The XML is the legally significant document; the PDF
is a rendering of it and carries no legal force.

### Rate limits

The API allows 3000 calls a day per IP and asks that sessions be opened no more
than once every five minutes. One run opens a single session and closes it, so
a normal backfill is well inside the budget; do not put the script on a
short-interval timer.

## What is not implemented

- Acts are filtered to incoming ones on our side, because `queryAwp` has no
  direction parameter. This has not been verified against live data.
- Kazakh captions cover the settled accounting terms only. Entries without a
  confirmed translation fall back to Russian. Have the wording reviewed before
  relying on `--lang kaz+rus`.

## Handling credentials

Your key container and its password are the only things standing between the
internet and your tax account. The repository is set up so they cannot be
committed by accident:

- `.gitignore` excludes `*.p12`, `*.pfx`, `*.jks`, `*.key`, `*.pem`, `.env*`
  and `config/`
- the `detect-private-key` and `gitleaks` pre-commit hooks reject staged
  secrets
- a CI job scans the working tree with gitleaks

Keep the key outside the repository and pass its location and password through
environment variables. Downloaded invoices are taxpayer data — `downloads/`
and `out/` are ignored for the same reason.

## Dependency updates

Dependabot opens update PRs monthly for both `uv` dependencies and GitHub
Actions. It has no `workflow_dispatch` trigger, so to run it on demand use the
**Check for updates** button under *Insights → Dependency graph → Dependabot*.

`pip-audit` runs as a blocking CI job on every pull request.

## Contributing

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/);
`cz check` enforces this both locally and in CI. Before requesting a review,
make sure the CI pipeline passes on your pull request, then request a review
from [@dchernykh1984](https://github.com/dchernykh1984).

## License

MIT — see [LICENSE](LICENSE).
