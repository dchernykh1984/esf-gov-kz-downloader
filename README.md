# esf-gov-kz-downloader

A small script that downloads documents from Kazakhstan's IS ESF
(Информационная система электронных счетов-фактур) through its SOAP API at
`https://esf.gov.kz:8443/esf-web/ws/api1`.

> Status: project scaffolding only. The downloader itself is not implemented
> yet.

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
- A way to produce a GOST 2015 XMLDsig signature. Python cannot do this on its
  own; [NCANode](https://github.com/ncanode-kz/NCANode) run locally in Docker
  is the headless option.

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
