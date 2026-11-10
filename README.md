# BLT

Task management reference project: a Django/DRF API with JWT and Celery, a React
client, and an alternative server-rendered client built with HTMX + Alpine.js over
the **same service layer**.

Built as a senior full-stack exercise. The goal is not feature count; it is a codebase
where every decision can be explained in a review.

## What is inside

| Path | Contents |
|---|---|
| `api/` | Django 6, DRF, SimpleJWT, drf-spectacular, django-filter, Celery |
| `api/tasks/` | Task domain: models, services, selectors, filters, serializers, views, tests |
| `api/accounts/` | JWT login, refresh, current user, assignable users |
| `api/hypermedia/` | HTMX + Alpine client rendered by Django templates |
| `web/` | React 19 + Vite + TypeScript + TanStack Query |
| `infra/minio/` | MinIO built from the pinned release (images are no longer published) |

## Stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.12, Django 6.0 |
| API | DRF 3.18, SimpleJWT, drf-spectacular, django-filter |
| Data | PostgreSQL 16 (Compose/CI) or SQLite (zero-setup local) |
| Async | Celery 5.5 + Redis 7 |
| Frontend | React 19, Vite 7, TypeScript, TanStack Query 5, React Hook Form |
| Styling | Tailwind CSS 4, design tokens from Ballast Lane's public site |
| Tests | pytest, pytest-django, pytest-cov (97% coverage) |
| Infra | Docker multi-stage, Compose, Nginx, Mailpit, MinIO (profile) |

## Quick start (no Docker)

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22+.

```sh
cp .env.example .env
make setup      # venv, dependencies, migrate, seed
make api        # http://127.0.0.1:8000
make web        # http://127.0.0.1:5173  (another terminal)
```

- React client: <http://127.0.0.1:5173>
- HTMX client: <http://127.0.0.1:8000/app/>
- API docs: <http://127.0.0.1:8000/api/docs/>
- Admin: <http://127.0.0.1:8000/admin/>

Demo credentials: **demo / demo12345** (also `maria / demo12345`).

Local defaults use SQLite, in-memory cache and eager Celery, so no Redis is needed to
run the app. Compose switches all three to the real services.

## Quick start (Docker)

```sh
cp .env.example .env
# set POSTGRES_PASSWORD and S3_SECRET_KEY in .env
make up          # db, redis, mailpit, api, worker, beat, web
```

- App through Nginx: <http://127.0.0.1:8080>
- HTMX client: <http://127.0.0.1:8080/app/>
- API: <http://127.0.0.1:8000>
- Mailpit (assignment e-mails): <http://127.0.0.1:8025>

Storage profile (MinIO + bucket bootstrap):

```sh
make up-full
# then run the API with object storage enabled
STORAGE_BACKEND=s3 docker compose up -d --build api worker
```

MinIO stopped publishing ready-made images, so `infra/minio/Dockerfile` builds the
pinned release from source. First build takes a few minutes; that is why it is a
profile and not part of `make up`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/token/` | Login (JWT pair) |
| POST | `/api/v1/auth/refresh/` | Rotate refresh token |
| GET | `/api/v1/auth/me/` | Current user |
| GET | `/api/v1/auth/users/` | Active users for assignment |
| GET | `/api/v1/tasks/` | List with filters + pagination |
| POST | `/api/v1/tasks/` | Create |
| GET | `/api/v1/tasks/{id}/` | Detail |
| PATCH | `/api/v1/tasks/{id}/` | Update |
| DELETE | `/api/v1/tasks/{id}/` | Delete (creator only) |
| POST | `/api/v1/tasks/{id}/complete/` | Complete (idempotent) |
| POST | `/api/v1/tasks/{id}/reopen/` | Reopen |
| POST | `/api/v1/tasks/{id}/assign/` | Assign to an active user |
| GET | `/api/v1/tasks/summary/` | Counts by status and overdue |

Filters: `status`, `due_date_after`, `due_date_before`, `assigned_to`, `overdue`,
`search`, `page`, `page_size`.

## Architecture

```
React (Vite) ─────┐
                  ├──▶ views → services → selectors → models
HTMX + Alpine ────┘         (Django 6 / DRF)
```

- **Views** validate input, call a service, and return a response.
- **Services** own business rules: complete, reopen, assign, update transitions.
- **Selectors** own what a user may see and how queries are shaped.
- **Serializers** own the contract. The HTMX views reuse the same serializer.

`hypermedia/views.py` calls `tasks.services` and `tasks.selectors` directly. There is
no second implementation of "only the creator deletes" or "completing twice keeps the
original timestamp".

See [`docs/architecture.md`](docs/architecture.md) for the full reasoning.

## Tests

```sh
make test
```

54 tests, 97% statement coverage, enforced at 80% in `pyproject.toml`.

What is covered beyond the happy path:

- complete twice keeps the first `completed_at`
- reopening a task clears `completed_at`
- assigning an inactive user is rejected
- a stranger gets 404, not 403, for a task they cannot see
- an assignee can see a task but cannot delete it
- date range with a single bound, overdue filter, search across title and description
- throttling on login, refresh rotation, inactive users excluded from assignment
- e-mail is sent on commit, not on rollback
- the seed command is idempotent
- HTMX create returns an out-of-band update and a 422 form on invalid input

## Generative AI

The exercise asks for the prompt, the output, the validation, and the corrections.
Those are in [`docs/ai/`](docs/ai/):

- [`01-scaffold-prompt.md`](docs/ai/01-scaffold-prompt.md) — the prompt and its constraints
- [`02-review.md`](docs/ai/02-review.md) — what the model got wrong and what changed
- [`03-decisions.md`](docs/ai/03-decisions.md) — trade-offs reviewed by hand

The short version: AI wrote a plausible first draft; the review caught a dead permission
class, a leaked throttle in tests, a schema generation failure, and a 404/403 mismatch
between the API and the HTMX client. None of those were visible without running the code.

## Why there are two clients

The target stack is HTMX + Alpine for server-rendered screens, with React for legacy
interfaces. Building both on one domain proves the important part: **the business rule
exists once**. The React client consumes JSON; the HTMX client consumes HTML fragments.
Both call the same services and selectors.

The HTMX client also demonstrates the patterns that matter in that stack:

- server-rendered partials with `hx-get`/`hx-target`/`hx-swap`
- out-of-band swap after create, so the dialog and the table update in one response
- `HX-Trigger` to close the dialog without client-side state duplication
- 422 responses swapped into the form (configured in `responseHandling`)
- Alpine for local UI state only: the create dialog
- progressive enhancement: every action has a normal form/link fallback

## UI

The palette, type scale and spacing follow Ballast Lane's public design tokens
(`#F4F6FA` background, `#0B1220` ink, `#2B50BA` blue, `#FE5A0B` accent, Space Grotesk /
Poppins / IBM Plex Mono). Component patterns (button variants, native dialog, feedback
states) are adapted from my ANA project, which uses the same conventions.

## Trade-offs and limits

- **Tokens in `localStorage`.** Simple and stateless, but exposed to XSS. Production
  should use `HttpOnly` cookies with CSRF, or a backend-for-frontend. Documented on purpose.
- **SQLite by default.** Zero setup for reviewers; Compose and CI run PostgreSQL.
- **No React component tests.** The API owns the rules and is covered. Component tests
  are the next step, not a silent omission.
- **`is_overdue` is derived.** No nightly job can leave it stale; the cost is a computed
  property on read.
- **Hypermedia client has no drag-and-drop and no edit dialog.** It covers create,
  complete, reopen, delete and filters — enough to prove the architecture.
- **No deploy target yet.** Everything runs locally with Compose.

## Next steps

1. GitHub Actions: API tests on PostgreSQL, web typecheck and build.
2. A public demo (Railway or a VPS) with seeded data.
3. React component tests with Vitest + Testing Library.
4. Attachment upload using the MinIO profile.
