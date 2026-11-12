# BLT

Task management reference project: a Django/DRF API with JWT and Celery, a React
client, and an alternative server-rendered client built with HTMX + Alpine.js over
the **same service layer**.

Built as a senior full-stack exercise. The goal is not feature count; it is a codebase
where every decision can be explained in a review.

**Start here**

| | |
|---|---|
| [`GENAI.md`](GENAI.md) | the GenAI part: the prompt, the output, how it was validated and corrected, and the AI feature |
| [Quick start](#quick-start-one-command-everything-seeded) | one command, everything seeded |
| [`docs/design-decisions.md`](docs/design-decisions.md) | why it is built this way, including the service layer |

## What is inside

| Path | Contents |
|---|---|
| `api/` | Django 6, DRF, SimpleJWT, drf-spectacular, django-filter, Celery |
| `api/tasks/` | Task domain: models, services, selectors, filters, serializers, views, tests |
| `api/accounts/` | JWT login, refresh, current user, assignable users |
| `api/core/` | Shared base model, pagination, DRF exception handler |
| `api/specs/` | GenAI: implementation spec generated from a Gitea issue, then tasks from it |
| `api/hypermedia/` | HTMX + Alpine client rendered by Django templates |
| `web/` | React 19 + Vite + TypeScript + TanStack Query |
| `mcp_server/` | The same spec flow exposed as MCP tools for CLI agents |
| `infra/minio/` | MinIO built from the pinned release (images are no longer published) |

## Stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.12, Django 6.0 |
| API | DRF 3.18, SimpleJWT, drf-spectacular, django-filter |
| Data | PostgreSQL 16 (Compose) or SQLite (zero-setup local) |
| Async | Celery 5.5 + Redis 7 |
| Frontend | React 19, Vite 7, TypeScript, TanStack Query 5, React Hook Form |
| Styling | Tailwind CSS 4, design tokens from Ballast Lane's public site |
| Tests | pytest, pytest-django, pytest-cov (95.7% coverage) |
| Infra | Docker multi-stage, Compose, Nginx, Mailpit, Gitea, MinIO (profile) |

## Quick start (one command, everything seeded)

```sh
git clone https://github.com/campanafernando/blt-project && cd blt-project
BLT_PASSWORD='<password from the submission e-mail>' make up   # .env and secrets, build, start, seed, then prints the addresses
```

The credentials are sent separately with the submission, not written in the repository. The
password is shared by the three seeded users (**fernando**, **ballast**, **lane**) and by Gitea
(login **blt@mail.com**, user `blt`). `make up` stores it in `secrets/blt_password`.

`make up` is idempotent: run it again at any time and it only fills in what is missing. It
starts db, redis, mailpit, gitea, api, worker, beat and web, and waits for the seed, which
creates:

- three users, **fernando**, **ballast** and **lane**, all with the same password, which is the
  file `secrets/blt_password` (`BLT_PASSWORD=... make env` sets it);
- 19 sample tasks, some created by one person for another, so each board is different;
- the Gitea repository `blt/tasks` with 13 issues (details below).

To use the AI features, put the key in `secrets/opencode_api_key` (or run
`OPENCODE_API_KEY=... make env`) and run `make up` again; without it everything else works and spec generation reports that it is
unavailable.

- App through Nginx: <http://127.0.0.1:8080>
- HTMX client: <http://127.0.0.1:8080/app/>
- API: <http://127.0.0.1:8000>
- Mailpit (assignment e-mails): <http://127.0.0.1:8025>
- Gitea (issues): <http://localhost:3000/blt/tasks/issues> — sign in with **blt@mail.com**
  and the shared password (`secrets/blt_password`; user `blt`, owner of the repository);
  `ballast` and `lane` exist in Gitea with the same password — seeded with 13 issues: four feature requests, eight that mirror the tasks of `ballast` and
  `lane` (same title and assignee), and #13 ("Export the task list to CSV"), which has no task
  and is meant for trying the spec flow

The Gitea login is `GITEA_EMAIL` from `.env` plus the shared password from `secrets/blt_password`.
The Gitea bot account and its API token are provisioned on first start. The bot is not an
instance admin; its token has every scope on purpose, because this is a local test stack
and the app is meant to use the whole Gitea API. The app itself is limited by the allowlist below. If you reset the Gitea
data volume, remove `giteasecrets` as well (`docker compose down -v`).

`GITEA_ALLOWED_REPOS` (comma-separated, default `GITEA_REPO`) limits which repositories the
spec flow may read or publish to. When set it must include `GITEA_REPO`, otherwise
bootstrap fails. Compose gives each service only the variables it needs. Behind a proxy,
set `NUM_PROXIES`; the bundled Nginx overwrites `X-Forwarded-For`.

The spec flow needs Gitea. With `make api` only, start it separately with `make gitea`
or point `GITEA_API_URL` at any instance.

Storage profile (MinIO + bucket bootstrap):

```sh
make up-full
# then run the API with object storage enabled
STORAGE_BACKEND=s3 docker compose up -d --build api worker
```

MinIO stopped publishing ready-made images, so `infra/minio/Dockerfile` builds the
pinned release from source. First build takes a few minutes; that is why it is a
profile and not part of `make up`.

## Quick start (no Docker)

Only the API and the clients, with SQLite; there is no Gitea, so the spec flow is off.
Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), Node 22+.

```sh
BLT_PASSWORD='<password from the submission e-mail>' make setup   # .env, secrets, venv, dependencies, migrate, seed
make api        # http://127.0.0.1:8000
make web        # http://127.0.0.1:5173  (another terminal)
```

- React client: <http://127.0.0.1:5173>
- HTMX client: <http://127.0.0.1:8000/app/>
- API docs: <http://127.0.0.1:8000/api/docs/>
- Admin: <http://127.0.0.1:8000/admin/>

`make env` (run by `setup`, `api`, `worker` and `up`) creates `.env` from `.env.example` when it
does not exist, and the files in `secrets/` when they do not exist. `.env` holds plain
configuration only; passwords and keys are never in it and never in the repository.

| Secret file | Used by |
|---|---|
| `secrets/blt_password` | the three seeded users and the Gitea accounts (`BLT_PASSWORD=... make env` sets your own) |
| `secrets/postgres_password` | Postgres and the Django services |
| `secrets/django_secret_key` | Django (signs sessions and JWTs) |
| `secrets/minio_root_password`, `secrets/minio_ro_secret` | MinIO and its read-only user |
| `secrets/opencode_api_key` | the AI provider; empty means the AI features are off |
| `secrets/email_host_password` | SMTP login, empty for the local Mailpit |

To change the shared password later (users and Gitea alike), run `make password`: it asks for the
new value, writes `secrets/blt_password`, issues a new Django key (every session and token issued
before stops working), recreates the API so the seed sets the new password, and re-runs the Gitea
init, which updates the three Gitea accounts and revokes the old API tokens. `BLT_PASSWORD=... make
password` does the same without the prompt.

In Docker each secret is a file under `/run/secrets`, mounted only into the services that need
it, so none of them appears in `docker inspect` or in a container's environment. Outside Docker
the same files are read from `secrets/`. The directory is `700` and git-ignored; the files are
readable (`644`) because containers run as other users and need to read their mount. If an older
`.env` still holds secrets, `make env` moves them into `secrets/` with the same values and removes
them from `.env`, so existing logins and data volumes keep working.

Seeded users (created by the seed, not shown on the login pages): **fernando**, **ballast**
and **lane**, all with the password in `secrets/blt_password`. The seed also loads 19 sample tasks (some created
by one person for another, so each user sees a different board) and resets those passwords on
every run.

Local defaults use SQLite, in-memory cache and eager Celery, so no Redis is needed to
run the app. Compose switches all three to the real services.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/v1/auth/token/` | Login (JWT pair) |
| POST | `/api/v1/auth/refresh/` | Rotate refresh token |
| GET | `/api/v1/auth/me/` | Current user |
| GET | `/api/v1/auth/users/` | Active users for assignment (`id`, `username`, `first_name`, `last_name`) |
| GET | `/api/v1/tasks/` | List with filters + pagination |
| POST | `/api/v1/tasks/` | Create |
| GET | `/api/v1/tasks/{id}/` | Detail |
| PATCH | `/api/v1/tasks/{id}/` | Update |
| DELETE | `/api/v1/tasks/{id}/` | Delete (creator only) |
| POST | `/api/v1/tasks/{id}/complete/` | Complete (idempotent) |
| POST | `/api/v1/tasks/{id}/reopen/` | Reopen |
| POST | `/api/v1/tasks/{id}/assign/` | Assign to an active user |
| GET | `/api/v1/tasks/summary/` | Counts by status and overdue |
| GET | `/api/v1/specs/config/` | `ai_enabled` and `publish_enabled` only |
| GET | `/api/v1/specs/` | Recent specs for the current user |
| POST | `/api/v1/specs/` | Generate a spec from a Gitea issue URL (`issue_url`) or from a typed subject (`subject`), one of the two |
| GET | `/api/v1/specs/{id}/` | Spec detail |
| POST | `/api/v1/specs/{id}/publish/` | Create a Gitea issue with the spec (409 if already published) |
| POST | `/api/v1/specs/{id}/tasks/` | Create up to 10 tasks from chosen steps (no model call) |

Filters: `status`, `due_date_after`, `due_date_before`, `assigned_to`, `overdue`,
`search`, `page`, `page_size`.

## Architecture

```
React (Vite) ─────┐
                  ├──▶ views → services → selectors → models
HTMX + Alpine ────┘         (Django 6 / DRF)
```

Views validate input and call a service; services own the rules; selectors own what a user
may see. `hypermedia/views.py` calls the same `tasks.services` and `tasks.selectors`, so
"only the creator deletes" and "completing twice keeps the original timestamp" exist once.

Layers, service and selector names and the GenAI flow: [`docs/architecture.md`](docs/architecture.md).
Why they are built this way: [`docs/design-decisions.md`](docs/design-decisions.md).

## Tests

```sh
make test
```

221 tests, 95.71% statement coverage, enforced at 80% in `pyproject.toml`.

What is covered beyond the happy path:

- complete twice keeps the first `completed_at`; reopening clears it; the database rejects
  a done task without `completed_at`
- assigning an inactive user is rejected
- a stranger gets 404, not 403, for a task they cannot see
- an assignee can see a task but cannot delete it, through the API and through HTMX
- date range with a single bound, overdue filter, search across title and description
- throttling on login, refresh rotation, inactive users excluded from assignment
- e-mail is sent on commit, not on rollback
- the seed command is idempotent
- HTMX create returns an out-of-band update and a 422 form on invalid input
- spec flow: repository allowlist, plain-text rendering of model output, publish claim,
  tasks from a spec

Not covered: there is no browser or E2E test of the React and HTMX flows.

Lint and format: `make lint` runs ruff on `api/` and `mcp_server/` and `tsc` on `web/`. The
`.pre-commit-config.yaml` runs ruff, ruff-format and basic file hygiene on every commit; enable it
once with `uvx pre-commit install` (or `pip install pre-commit && pre-commit install`).

## GenAI: spec from an issue or a subject

One fixed task, no chat. The input is one of two things, a Gitea issue URL or a subject typed by a
person (10 to 2,000 characters); either way it is passed to the model as data, never as instruction:

```
POST /api/v1/specs/  {"issue_url": "http://localhost:3000/blt/tasks/issues/1"}   issue → spec
POST /api/v1/specs/  {"subject": "Export the task list to CSV, with the filters"}   subject → spec
  → validate → (fetch issue) → fixed prompt → JSON contract → persist
POST /api/v1/specs/{id}/publish/                                                    spec → new Gitea issue
```

The model must return exactly:

```json
{"summary": "...", "acceptance_criteria": ["..."], "implementation_steps": ["..."],
 "risks": ["..."], "out_of_scope": ["..."], "size": "S|M|L"}
```

Anything outside that shape is a provider error (502), not something rendered to the
user. The issue body is treated as untrusted data and truncated at 12k chars.

Guardrails: `spec` throttle of 10/hour on `POST /specs/` only, `spec_publish` throttle of
30/hour, 45s timeout, no tools or code execution, provider errors not echoed, repository
allowlist (`GITEA_ALLOWED_REPOS`), model output written to the issue as plain text, and the
API key never reaches the browser. Publishing the spec back as a Gitea issue requires a
token or basic auth; without it the button is disabled and the endpoint returns 503.
Publishing is claimed first (marker `pending`), so concurrent calls cannot create two
issues; if the process dies after the claim, reset `published_issue_url` by hand.

A generated spec can then become tasks: pick steps in the **Create tasks** dialog (React) or
call `POST /api/v1/specs/{id}/tasks/`. Each task gets a `Source: <issue url>` line (`Source: spec #<id>` for a subject spec). No
second model call.

The same flow is available to CLI agents through the MCP server in
[`mcp_server/`](mcp_server/README.md) — five tools, same services, same validation.
`create_tasks_from_spec` returns a draft and writes only with `confirm=true`.

Design notes: [`docs/ai/04-spec-feature.md`](docs/ai/04-spec-feature.md).

## Generative AI

The exercise asks for the prompt, the output, the validation, and the corrections: they are
answered in [`GENAI.md`](GENAI.md). The supporting detail is in [`docs/ai/`](docs/ai/):

- [`01-scaffold-prompt.md`](docs/ai/01-scaffold-prompt.md) — the prompt and its constraints
- [`02-review.md`](docs/ai/02-review.md) — what the model got wrong and what changed
- [`03-decisions.md`](docs/ai/03-decisions.md) — trade-offs reviewed by hand
- [`04-spec-feature.md`](docs/ai/04-spec-feature.md) — the spec-from-issue feature
- [`05-ai-log.md`](docs/ai/05-ai-log.md) — the dated log of every round of work with the agents

The short version: AI wrote a plausible first draft; the review caught a dead permission
class, a leaked throttle in tests, a schema generation failure, and a 404/403 mismatch
between the API and the HTMX client. None of those were visible without running the code.

## Two clients

React consumes JSON; HTMX consumes HTML fragments; both call the same services and
selectors. The reasoning is in [`docs/design-decisions.md`](docs/design-decisions.md).

The HTMX client shows the patterns that matter in that stack:

- server-rendered partials with `hx-get`/`hx-target`/`hx-swap`
- out-of-band swap after create, so the dialog and the table update in one response
- `HX-Trigger` to close the dialog without client-side state duplication
- 422 responses swapped into the form (configured in `responseHandling`)
- Alpine for local UI state only: the create dialog
- progressive enhancement: every action has a normal form/link fallback

## UI

Both clients share one design language, taken from [ballastlane.com](https://ballastlane.com).
The values below were measured in a real browser (computed styles), not guessed:

| Token | Value |
|---|---|
| Page / panel / ink / muted | `#F4F6FA` / `#FFFFFF` / `#0B1220` / `#5B6475` |
| Borders / field border | `#DCE2EC` / `#7D879A` |
| Blue (links, accents) / orange (primary action) | `#2B50BA` / `#FE5A0B`, hover `#FF7633` |
| Text on orange | ink `#0B1220`, not white |
| Footer | `#0B1220` background, `#B7C0D1` text |
| Fonts | Space Grotesk (text, headings, buttons, inputs), IBM Plex Mono (navigation, labels, badges) |
| Headings | 700, tracking -0.035em; the last word of a page title is blue, as in the site's hero |
| Primary button | orange fill, ink text, 8px radius, 12px 18px padding, 15px/500 |
| Fields | `#F4F6FA` fill, 1px `#7D879A`, 8px radius, 12px 14px padding |
| Cards | white, 1px `#DCE2EC`, 10px radius, no shadow |

The task list is a fixed grid in both clients (task, status, due date, assignee, actions), so
every column starts at the same x in every row; below 1024 px it becomes stacked cards. What
differs per row is shown without moving the columns: a due caption ("12 days overdue", "Due
today", "Due tomorrow", "Completed 11 Nov", "No due date"), an initials avatar with a "You" tag
and "from <name>" when someone else created the task, an italic "Unassigned", an orange stripe
for overdue, a line-through for done, tooltips on the icon buttons, and a row hover. Long text is
cut with an ellipsis and keeps the full text in a tooltip. A fixed actions slot keeps the edit
icon in place even when the user cannot delete the task.

Orange is used only for fills, borders and the overdue marker: orange text on a light
background fails WCAG AA, so the Overdue badge uses `#B13A00` (5.43:1). Every text and
background pair in the badges is at least 4.5:1. The tokens live in one place per client
(`web/src/index.css` and `api/hypermedia/static/hypermedia/app.css`). Not copied from the
site: the light/dark switch. Dates are shown in English. The HTMX scripts are loaded from a
CDN with SRI hashes; fonts load from Google Fonts.

## Trade-offs and limits

- **Tokens in `localStorage`.** Simple and stateless, but exposed to XSS. Production
  should use `HttpOnly` cookies with CSRF, or a backend-for-frontend. Documented on purpose.
- **SQLite by default.** Zero setup for reviewers; Compose runs PostgreSQL.
- **No automated browser or React component tests.** The API owns the rules and is
  covered; the two client flows are exercised by a manual browser smoke test.
- **React filters are not in the URL**; the HTMX filters are.
- **Tailwind CSS, `class-variance-authority`, `clsx` and `tailwind-merge` in `web/`.**
  Decided: the React client keeps Tailwind utilities over the shared design tokens, the
  HTMX client uses plain CSS, and no component library is used.
- **API docs use drf-spectacular, not drf-yasg.** drf-yasg only generates Swagger 2.0 and
  is no longer actively developed; drf-spectacular emits OpenAPI 3, validates the schema
  in `make schema` (`--fail-on-warn`) and serves Swagger UI at `/api/docs/`.
- **Dependencies are pinned with uv, not declared in `pyproject.toml`.** `requirements.in`
  and `requirements-dev.in` are compiled to `requirements*.txt` (`uv pip compile`);
  `pyproject.toml` holds the ruff, pytest and coverage configuration.
- **`unblock_account()` in `specs/gitea.py` is probably redundant**, since Compose already
  creates the Gitea user without a forced password change. It is kept because the seed
  still calls it and it works on a fresh volume.
- **`seed` bypasses the services on purpose** (it writes fixtures directly).
- **A publish marker `pending` needs a manual reset** if the process dies mid-publish
  (edit `published_issue_url` of the spec in the Django admin).
- **`Spec` does not use `core.models.BaseModel`.**
- **`is_overdue` is derived.** No nightly job can leave it stale; the cost is a computed
  property on read.
- **Hypermedia client has no drag-and-drop and no edit dialog.** It covers create,
  complete, reopen, delete and filters — enough to prove the architecture.
- **No deploy target yet.** Everything runs locally with Compose.

## Next steps

1. A public demo (Railway or a VPS) with seeded data.
2. Browser tests of the React and HTMX flows; React component tests with Vitest.
3. Self-host the fonts.
4. GenAI backlog: text → task draft, issue triage before the spec, per-user AI budget and
   token usage logging, golden-issue evals.
5. Attachment upload using the MinIO profile.
