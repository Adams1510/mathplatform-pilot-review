# M1 Integers technical review package

This is a sanitized, synthetic-only technical review package for the current M1 Integers foundation. It is for code review and local engineering exercise. It is not a student-ready pilot and it contains no private Q02 representation, controlled marking material, learner-body content, participant data, credentials, Git history, or deployment configuration.

## What the package demonstrates

- A Django topic shell with M1 Integers navigation, metadata-only activity links, accessibility help, liveness/readiness endpoints, CSRF protection, and response headers.
- A synthetic-only readiness form and durable token-state fixture. It uses three non-educational tokens and a local SQLite database.
- Revision conflict handling, idempotent save handling, synthetic-state expiry/purge logic, session use, and client-side IndexedDB draft recovery.
- Unit/integration tests for the topic shell, security headers, synthetic state, and selected browser checks.

The topic route intentionally does not render learning objects. The displayed activity links are placeholders and return an unavailable state. The synthetic route is a technical fixture only.

## What remains incomplete

- No student learning objects, diagnostic flow, marking, recommendations, reviewer workflow, participant policy, or production deployment.
- No PostgreSQL exercise in this package. SQLite allows local review of the synthetic flow but cannot prove row-locking or concurrency behaviour on the intended database.
- No browser binaries are included. Browser checks require a reviewer-managed Playwright installation and are optional.
- The source worktree's Q02 modules, manifests, private loader, preview route, tests, and reconciliation scripts are deliberately absent.
- This package includes no hosting, identity, cloud, evidence-system, key-management, incident-channel, backup, or operational implementation.

## Prerequisites

- Python 3.13.
- `uv` for locked Python dependency installation. The lock file is included.
- Node.js only for optional browser accessibility checks; `package-lock.json` pins `axe-core`.

## Install and run locally

Run these commands in this package directory. They install only the locked dependencies described in `uv.lock` and `package-lock.json`.

```powershell
uv sync --frozen
npm ci
uv run python manage.py migrate --settings=config.settings.review
uv run python manage.py runserver 127.0.0.1:8000 --settings=config.settings.review
```

Open `http://127.0.0.1:8000/`. Use `/_readiness/` and `/_synthetic/state/` only as synthetic technical fixtures. Stop the server with `Ctrl+C`. To remove local synthetic runtime state, delete `review.sqlite3` after stopping the server; it is ignored by Git.

## Run checks

```powershell
uv run ruff check .
uv run python manage.py check --settings=config.settings.review
uv run python manage.py makemigrations --check --dry-run --settings=config.settings.review
uv run pytest
uv run coverage run -m pytest
uv run coverage report
```

For optional browser checks, install browsers under the reviewer's tooling policy, start the local server, then set `RUN_BROWSER_TESTS=1` before running pytest. These checks are not independent accessibility QA.

## Historical evidence and package checks

Historical source-worktree records report Development tests and boundary checks at prior immutable baselines. They are background only and are not reproduced or independently accepted by this package.

Assess this package from its own check output. The handoff report records the checks attempted during preparation and any blockers. It does not claim independent review, operational readiness, student readiness, Q02 verification, or a production result.

## Review focus

Start with [SENIOR-CODER-CHECKLIST.md](SENIOR-CODER-CHECKLIST.md), record issues using [FINDINGS-TEMPLATE.md](FINDINGS-TEMPLATE.md), and read [HANDOFF-REPORT.md](HANDOFF-REPORT.md) for scope, included files, exclusions, and remaining pilot work.
