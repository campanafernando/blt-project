# BLT project — agent rules

## Structure

- `api/` — Django 6 + DRF. Domain app in `tasks/`, authentication in `accounts/`.
- `api/specs/` — GenAI spec flow; talks to Gitea.
- `api/hypermedia/` — HTMX + Alpine client. No business rules here.
- `web/` — React + Vite. `src/lib/api.ts` is the only HTTP layer.
- `mcp_server/` — MCP tools over the same services.

## Boundaries

- A view validates, calls a service and responds. It never queries the ORM for a rule.
- Rules live in `tasks/services.py`; queries in `tasks/selectors.py`; filters in `tasks/filters.py`.
- `hypermedia` uses `forms.Form` only to validate the shape of the input. The rules still come
  from `tasks.services` and `tasks.selectors`. Never duplicate a rule there.
- A React component never builds a URL or reads a token. Use `apiFetch` and feature hooks.

## Quality

- `make test` enforces at least 80% coverage.
- `make check` runs the lock check, ruff, pytest, the schema check and the web build.
- API errors follow the DRF shape; the frontend reads `detail` and field-to-list maps.
- No warnings in the browser console.

## Operations

- Local: SQLite + in-memory cache + eager Celery, no Docker required.
- Compose: Postgres, Redis, Mailpit, Gitea, API, worker, beat, web. MinIO behind the
  `storage` profile.
- `.env` is plain configuration only; `.env.example` documents every key. Passwords and keys are
  files under `secrets/` (git-ignored), created by `make env`. Never put a secret in `.env`,
  code or documentation.

## Forbidden

- Committing without authorization.
- Duplicating a rule between the API and the HTMX client.
- Adding a dependency without a demonstrated need.
- Leaving `manage.py check`, ruff or `tsc` with an error.
