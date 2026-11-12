# BLT

Task management reference project: a Django/DRF API with JWT and Celery, a React client, and an alternative
server-rendered client built with HTMX + Alpine.js over the **same service layer**. Built as a senior full-stack
exercise: the goal is not feature count, it is a codebase where every decision can be explained in a review.

> *As someone who organizes work, I want to record tasks, assign them to someone and track
> what is late, so I do not miss deadlines and know who owns what.*

**Start here**

| | |
|---|---|
| [`GENAI.md`](GENAI.md) | applied AI in the product, and the tooling behind the code |
| [`PRESENTATION.md`](PRESENTATION.md) | my thought process: the story, the decisions, how I worked, what I would not claim |
| [Hosting on Railway](#hosting-on-railway) | the live demo, its nine services and how to recreate them |
| [Quick start](#quick-start-one-command-everything-seeded) | one command, everything seeded |
| [Architecture](#architecture) | layers, visibility, transitions, notifications, authentication, the HTMX client |
| [Design decisions](#design-decisions) | why it is built this way, including the service layer |
| [Demo script](#demo-script) | the five-minute walkthrough |

## Contents

- [What is inside](#what-is-inside)
- [Stack](#stack)
- [Quick start (one command, everything seeded)](#quick-start-one-command-everything-seeded)
- [Quick start (no Docker)](#quick-start-no-docker)
- [Commands and configuration](#commands-and-configuration)
- [Hosting on Railway](#hosting-on-railway)
- [Endpoints](#endpoints)
- [Architecture](#architecture)
- [Design decisions](#design-decisions)
- [Tests and quality](#tests-and-quality)
- [UI](#ui)
- [Demo script](#demo-script)
- [Generative AI](#generative-ai)
- [Trade-offs and limits](#trade-offs-and-limits)
- [Next steps](#next-steps)

## What is inside

| Path | Contents |
|---|---|
| `api/` | Django 6, DRF, SimpleJWT, drf-spectacular, django-filter, Celery |
| `api/tasks/` | Task domain: models, services, selectors, filters, serializers, views, tests |
| `api/accounts/` | JWT login, refresh, current user, assignable users |
| `api/core/` | Shared base model, pagination, DRF exception handler |
| `api/specs/` | The AI feature: implementation spec from a Gitea issue or a subject, then tasks from it (see [`GENAI.md`](GENAI.md)) |
| `api/hypermedia/` | HTMX + Alpine client rendered by Django templates |
| `web/` | React 19 + Vite + TypeScript + TanStack Query |
| `mcp_server/` | The spec flow exposed as MCP tools for CLI agents (see [`GENAI.md`](GENAI.md)) |
| `infra/` | The infrastructure in one place: `compose.yaml` (the local stack), `gitea/` (Gitea plus an account bootstrap: the image Compose and Railway both run), `minio/` (MinIO built from the pinned release; images are no longer published) and `railway/` (the hosted stack: manifest, variables, deploy script) |
| `scripts/` | `make-secrets.sh` (creates `.env` secrets as files), `rotate-password.sh` (`make password`) |

## Stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.12, Django 6.0 |
| API | DRF 3.18, SimpleJWT, drf-spectacular, django-filter |
| Data | PostgreSQL 16 (Compose) or SQLite (zero-setup local) |
| Async | Celery 5.5 + Redis 7 |
| Frontend | React 19, Vite 7, TypeScript, TanStack Query 5, React Hook Form |
| Styling | Tailwind CSS 4, design tokens from Ballast Lane's public site |
| Tests | pytest, pytest-django, pytest-cov (95.8% coverage) |
| Infra | Docker multi-stage, Compose, Nginx, Mailpit, Gitea, MinIO (profile) |

## Quick start (one command, everything seeded)

```sh
git clone https://github.com/campanafernando/blt-project && cd blt-project
BLT_PASSWORD='<password from the submission e-mail>' make up   # .env and secrets, build, start, seed, then prints the addresses
```

The credentials are sent separately with the submission, not written in the repository. The password is shared by the
three seeded users (**fernando**, **ballast**, **lane**) and by Gitea (login **blt@mail.com**, user `blt`). `make up`
stores it in `secrets/blt_password`.

`make up` is idempotent: run it again at any time and it only fills in what is missing. It starts db, redis, mailpit,
gitea, api, worker, beat and web, and waits for the seed, which creates:

- three users, **fernando**, **ballast** and **lane**, all with the same password, which is the file
  `secrets/blt_password` (`BLT_PASSWORD=... make env` sets it);
- 19 sample tasks, some created by one person for another, so each board is different;
- the Gitea repository `blt/tasks` with 13 issues (details below).

To use the AI features, put the key in `secrets/opencode_api_key` (or run `OPENCODE_API_KEY=... make env`) and run
`make up` again; without it everything else works and spec generation reports that it is unavailable.

- App through Nginx: <http://127.0.0.1:8080>
- HTMX client: <http://127.0.0.1:8080/app/>
- API: <http://127.0.0.1:8000>
- Mailpit (assignment e-mails): <http://127.0.0.1:8025>
- Gitea (issues): <http://localhost:3000/blt/tasks/issues> — sign in with **blt@mail.com** and the shared password
  (`secrets/blt_password`; user `blt`, owner of the repository); `ballast` and `lane` exist in Gitea with the same
  password — seeded with 13 issues: four feature requests, eight that mirror the tasks of `ballast` and `lane` (same
  title and assignee), and #13 ("Export the task list to CSV"), which has no task and is meant for trying the spec
  flow

The Gitea login is `GITEA_EMAIL` from `.env` plus the shared password from `secrets/blt_password`. Gitea runs from
`infra/gitea`: the stock image plus a small bootstrap that creates `blt`, `ballast` and `lane` with the shared password
every time it starts (an existing account only gets its password reset). None of them is an instance admin. The app
talks to Gitea as `blt` with that password, limited by the allowlist below; there is no API token to provision or
rotate.

`GITEA_ALLOWED_REPOS` (comma-separated, default `GITEA_REPO`) limits which repositories the spec flow may read or
publish to. When set it must include `GITEA_REPO`, otherwise bootstrap fails. Compose gives each service only the
variables it needs. Behind a proxy, set `NUM_PROXIES`; the bundled Nginx overwrites `X-Forwarded-For`.

The spec flow needs Gitea. With `make api` only, start it separately with `make gitea` or point `GITEA_API_URL` at any
instance.

Storage profile (MinIO + bucket bootstrap):

```sh
make up-full
# then run the API with object storage enabled
STORAGE_BACKEND=s3 docker compose -f infra/compose.yaml --env-file .env up -d --build api worker
```

MinIO stopped publishing ready-made images, so `infra/minio/Dockerfile` builds the pinned release from source. First
build takes a few minutes; that is why it is a profile and not part of `make up`.

## Quick start (no Docker)

Only the API and the clients, with SQLite; there is no Gitea, so the spec flow is off. Requires Python 3.12+,
[uv](https://docs.astral.sh/uv/), Node 22+.

```sh
BLT_PASSWORD='<password from the submission e-mail>' make setup   # .env, secrets, dependencies (uv sync), migrate, seed
make api        # http://127.0.0.1:8000
make web        # http://127.0.0.1:5173  (another terminal)
```

- React client: <http://127.0.0.1:5173>
- HTMX client: <http://127.0.0.1:8000/app/>
- API docs: <http://127.0.0.1:8000/api/docs/>
- Admin: <http://127.0.0.1:8000/admin/>

Seeded users (created by the seed, not shown on the login pages): **fernando**, **ballast** and **lane**, all with the
password in `secrets/blt_password`. The seed also loads 19 sample tasks (some created by one person for another, so
each user sees a different board) and resets those passwords on every run.

## Commands and configuration

### Make targets

| Target | What it does |
|---|---|
| `make env` | Creates `.env` from `.env.example` if missing, and the files in `secrets/` if missing (`scripts/make-secrets.sh`). Run by `setup`, `api`, `worker`, `up`, `up-full`, `gitea` |
| `make password` | Rotates the shared password (users and Gitea) and the Django key; see below. `BLT_PASSWORD=... make password` skips the prompt |
| `make install` | `uv sync` in `api/` and `npm install` in `web/` |
| `make lock` / `make lock-check` | `uv lock` refreshes `api/uv.lock`; `uv lock --check` fails if it is out of date |
| `make migrate` / `make seed` | Apply migrations / load the seed (runs `migrate` first) |
| `make setup` | `env` + `install` + `seed`: everything for the no-Docker run |
| `make api` | Django dev server on `0.0.0.0:8000` |
| `make worker` | Celery worker (only needed with Redis and `CELERY_TASK_ALWAYS_EAGER=false`) |
| `make web` | Vite dev server on 5173 |
| `make test` | pytest with coverage, fails below 80% |
| `make cov` | Same, plus an HTML coverage report |
| `make lint` | `ruff check` on `api/` and `mcp_server/`, and `tsc` on `web/` |
| `make schema` | Writes `api/schema.yaml` with `--validate --fail-on-warn` |
| `make check` | `lock-check`, `lint`, `test`, `schema`, then the web build |
| `make up` / `make up-full` | Build and start the Compose stack and wait for the seed; `up-full` adds the `storage` profile (MinIO) |
| `make ready` | Prints the addresses and logins (run by `up`) |
| `make gitea` | Starts only Gitea and its seed |
| `make issues` | Prints the Gitea issues URL |
| `make down` / `make logs` / `make ps` | Stop the stack / follow logs / list services (`docker compose` on `infra/compose.yaml`) |
| `make clean` | Removes `api/.venv`, `web/node_modules`, `web/dist`, the SQLite file, static and media, and tool caches (not Docker volumes) |

### Dependencies

Dependencies and tool configuration (ruff, pytest, coverage) live in `api/pyproject.toml`, locked in `api/uv.lock`.
Runtime packages are in `[project]`, dev tools in the `dev` dependency group. Edit `pyproject.toml`, run `make lock`,
then `make install` (or `uv sync` in `api/`). `make check` fails if the lock is out of date; the Docker build installs
from the lock with `uv sync --frozen --no-dev`.

### Pre-commit

`.pre-commit-config.yaml` runs ruff (with `--fix`) and ruff-format on `api/`, plus basic file hygiene (trailing
whitespace, end of file, YAML, merge conflicts, files over 512 KB) on every commit. `mcp_server/` is covered by `make
lint` instead. Enable it once with `uvx pre-commit install` (or `pip install pre-commit && pre-commit install`).

### `.env` and `secrets/`

`make env` creates `.env` from `.env.example` when it does not exist, and the files in `secrets/` when they do not
exist. `.env` holds plain configuration only; passwords and keys are never in it and never in the repository.

| Secret file | Used by |
|---|---|
| `secrets/blt_password` | the three seeded users and the Gitea accounts (`BLT_PASSWORD=... make env` sets your own) |
| `secrets/postgres_password` | Postgres and the Django services |
| `secrets/django_secret_key` | Django (signs sessions and JWTs) |
| `secrets/minio_root_password`, `secrets/minio_ro_secret` | MinIO and its read-only user |
| `secrets/opencode_api_key` | the AI provider; empty means the AI features are off |
| `secrets/email_host_password` | SMTP login, empty for the local Mailpit |

To change the shared password later (users and Gitea alike), run `make password`: it asks for the new value, writes
`secrets/blt_password`, issues a new Django key (every session and token issued before stops working), recreates the
API so the seed sets the new password, and recreates Gitea, whose bootstrap sets the new password on its three
accounts. `BLT_PASSWORD=... make password` does the same without the prompt.

In Docker each secret is a file under `/run/secrets`, mounted only into the services that need it, so none of them
appears in `docker inspect` or in a container's environment. Outside Docker the same files are read from `secrets/`.
The directory is `700` and git-ignored; the files are readable (`644`) because containers run as other users and need
to read their mount. If an older `.env` still holds secrets, `make env` moves them into `secrets/` with the same
values and removes them from `.env`, so existing logins and data volumes keep working.

### Settings worth knowing

| Variable | Default (`.env.example`) | Compose | Effect |
|---|---|---|---|
| `DB_ENGINE` | `sqlite` | `postgres` | Database backend |
| `REDIS_URL` | empty: in-memory cache | `redis://redis:6379/0` | Cache, Celery broker and result backend |
| `CELERY_TASK_ALWAYS_EAGER` | `true`: tasks run in the request process, no worker | `false` | Whether Celery tasks go to the worker |
| `GITEA_ALLOWED_REPOS` | `blt/tasks` | same | Repositories the spec flow may read or publish to; must include `GITEA_REPO` |
| `NUM_PROXIES` | `0` | `0` | Trusted proxies in front of the API, for throttling by client address; the bundled Nginx overwrites `X-Forwarded-For` |
| `STORAGE_BACKEND` | `filesystem` | `filesystem` | `s3` uses MinIO (`make up-full`) |
| `ACCESS_TOKEN_MINUTES` / `REFRESH_TOKEN_DAYS` | 30 / 7 | same | JWT lifetimes |

Local defaults use SQLite, in-memory cache and eager Celery, so no Redis is needed to run the app. Compose switches
all three to the real services.

## Hosting on Railway

The same stack runs on [Railway](https://railway.com) with the same seeded users, password and data as
`make up`. Live demo: the app at <https://web-production-c97d5880.up.railway.app> (React, and the HTMX client
under `/app/`) and Gitea at <https://gitea-production-2ea7f1ac.up.railway.app>, where the AI feature reads
issues and publishes specs. Users are `fernando`, `ballast` and `lane` and the Gitea login is `blt@mail.com`;
the password is the one sent with the submission. Railway's generic `*.up.railway.app` domains are used: no
custom domain and no CDN in front.

| Service | Source | Public | What it does |
|---|---|---|---|
| `web` | `web/` (nginx + the React build) | yes | static files; proxies `/api/`, `/app/`, `/admin/` to `api` |
| `api` | `api/Dockerfile`, `SERVICE_ROLE=api` | no | applies migrations, seeds, serves with gunicorn; healthcheck `/api/schema/` |
| `worker` | same image, `SERVICE_ROLE=worker` | no | Celery worker (assignment e-mails) |
| `beat` | same image, `SERVICE_ROLE=beat` | no | Celery beat (daily digest) |
| `seed` | same image, `SERVICE_ROLE=seed` | no | one shot: creates the Gitea repository and the 13 issues, then stops; redeploy it to run again |
| `gitea` | `infra/gitea` (Gitea 1.24.6 + a bootstrap script, the same image Compose runs), volume on `/data` | yes | the tracker; creates the `blt`, `ballast` and `lane` accounts when it starts; sign-up is closed |
| `mailpit` | image `axllent/mailpit`, behind a login | yes | catches the assignment e-mails |
| `Postgres`, `Redis` | Railway templates (Postgres 18 with SSL, with a volume) | no | database; Celery broker and cache |

Only `web`, `gitea` and `mailpit` have a public domain. The databases and the API are reachable only on
Railway's private network (`*.railway.internal`); there is no public TCP proxy on Postgres or Redis.

**How it starts with the data.** There is no dump to restore: the data is produced by the same commands as
locally, so it is identical and reproducible. `api` runs `manage.py seed` (3 users, 19 tasks), `gitea` creates
its three accounts, and `seed` runs `gitea_bootstrap` (repository `blt/tasks` and 13 issues, the last one,
#13, left free for the spec flow). Both environments were compared item by item: titles, descriptions,
statuses, creators, assignees and due dates of the 19 tasks, and number, title and assignees of the 13 issues.
A raw database dump would also carry password hashes and Gitea's internal keys, which belong to one
environment.

**One image, several processes.** Railway deploys every service of a directory with the same settings, so
`api/entrypoint.sh` picks the process from `SERVICE_ROLE` (`api`, `worker`, `beat`, `seed`). With no role it
runs the command it was given, which is what Compose does. Compose uses the same role for its one-shot Gitea
seed, so the two environments share that mechanism.

**Configuration.** No file holds a secret. The app already falls back from `secrets/<name>` to the
environment variable `<NAME>`, so on Railway the secrets are variables (`DJANGO_SECRET_KEY`, `BLT_PASSWORD`,
`OPENCODE_API_KEY`) and the rest are references such as `${{Postgres.PGHOST}}` and
`${{gitea.RAILWAY_PRIVATE_DOMAIN}}`. Behind Railway's TLS edge, `TRUST_FORWARDED_PROTO=true` makes Django
trust `X-Forwarded-Proto` and keep the cookies HTTPS-only, and `NUM_PROXIES=2` (the edge and nginx) makes the
rate limits count the client's address, not Railway's. nginx reads `PORT` and `API_UPSTREAM` at start and
resolves the API per request, so it starts even before the API is up.

**Create, check or update it.** What runs is described by `infra/railway/`: `services.json` (the directory each
service is built from, its variable files, its settings and public port) and the `.env` files with the non-secret
variables and their references, some shared by several services. One script reads them:

```sh
railway login
infra/railway/deploy.py --check      # compares the folder with what runs on Railway; changes nothing
infra/railway/deploy.py --dry-run    # shows what it would do
infra/railway/deploy.py              # project, services, volume, domains, variables, first deploys
railway up api --path-as-root -s api -e production -d     # redeploy one service after a change
railway service logs -s api          # runtime logs
```

`--check` prints names, never values, and is what keeps the folder honest: it compares every variable, setting, image,
volume and domain, and reports anything on Railway that is in no file here. Today it reports that Railway matches the
folder (7 services, 2 databases). The script is idempotent and sends secrets on stdin, never as arguments. It needs
`secrets/blt_password` and `secrets/opencode_api_key`. Railway is pay-per-use; check `railway usage`. To remove
everything, `railway delete` (it deletes the volumes and the databases too).

There is no `railway.toml`. Railway deprecated "Config as Code": services created after that cannot use it, and the
existing files stop being read on 2026-12-01, so a `railway.toml` here would be ignored. Its replacement is Railway's
own Infrastructure as Code file (`.railway/railway.ts`); this folder uses the CLI and the GraphQL API instead.

**Things that went wrong while setting it up**, so they do not cost time again:

- A variable named `HTTPS_PROXY` is read by `pip` as a proxy address: the image build failed. The flag is
  called `TRUST_FORWARDED_PROTO`.
- A reference variable is read when a container starts. `web` deployed before `api` existed and kept an empty
  `API_UPSTREAM` (nginx: "no host in upstream"); deploy `api` first, then `web`, or redeploy `web`.
- The first version of this setup had a `railway.toml` per service. None of them was ever read (see above): the
  hosted `web` and `gitea` had no healthcheck although their files declared one. `railway environment edit` also
  answered "no changes" without applying any. The settings are applied through the GraphQL API (`railway api`), and
  `--check` reads them back, so a message is never taken for evidence.
- A one-off job in the API container is possible through `preDeployCommand` (set, deploy, clear it); the
  `railway ssh` route needs an SSH key registered on the account. `--check` flags a pre-deploy command left behind.

**A note on Terraform.** I could have declared this infrastructure with Terraform as well (there is a community provider for Railway) and would, if you prefer it; for nine services one idempotent script was enough, and nothing here was applied with Terraform.

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

Filters: `status`, `due_date_after`, `due_date_before`, `assigned_to`, `overdue`, `search`, `page`, `page_size`. A bad
value (an unknown status, a malformed date, a non-numeric assignee) is a 400 naming the field; a blank value means "no
filter". Errors follow the DRF format (`detail`, or field → list); the React client reads both. Swagger UI is at
`/api/docs/`.

## Architecture

How the code is laid out and what each part does today. The reasons behind the choices are in [Design
decisions](#design-decisions).

```
React (Vite) ─────┐
                  ├──▶ views → services → models
HTMX + Alpine ────┘          └─▶ selectors → QuerySet
                                    │
              Postgres ◀── Django ──┴──▶ Redis ──▶ Celery
                              │
                           Gitea (issues)
```

The API returns JSON; the `hypermedia` app renders HTML. Both call the same services and selectors, so "only the
creator deletes" and "completing twice keeps the original timestamp" exist once. The spec flow talks to Gitea through
`api/specs/gitea.py`; how it works is in [`GENAI.md`](GENAI.md).

### Layers

| Layer | File | May | May not |
|---|---|---|---|
| View | `tasks/views.py`, `hypermedia/views.py` | Validate input, call a service, pick the status code | Query the ORM for a rule |
| Serializer | `InputSerializer` in the view class (`TaskListApi` aliases the shared `TaskInputSerializer` from `tasks/serializers.py`, which `specs` also reuses), `tasks/serializers.py` (output) | Validate the contract, shape the output | Decide a rule |
| Service | `tasks/services.py` | Rules, state transitions, schedule effects | Build an HTTP response |
| Selector | `tasks/selectors.py`, `tasks/filters.py` | Visibility scope, filters, aggregations | Change data |
| Model | `tasks/models.py`, `core/models.py` | Data invariants, constraints, derived properties | Know about the request |

Names follow the HackSoft styleguide; the deviations are listed in [Review against the HackSoft
Django-Styleguide](#review-against-the-hacksoft-django-styleguide).

- Services (keyword-only, atomic, call `full_clean()`, raise Django `ValidationError` / `PermissionDenied`):
  `task_create`, `task_update`, `task_complete`, `task_reopen`, `task_assign`, `task_delete`. Selectors: `task_list`,
  `task_get`, `task_summary`, `assignee_list`. `task_list` raises a Django `ValidationError` for an invalid filter
  value (the API turns it into a 400); the HTMX board catches it and shows the unfiltered list.
- `core/exceptions.py` is the DRF exception handler. It turns the Django exceptions into the DRF error shape
  (`detail`, or field → list).
- `core.models.BaseModel` (abstract) gives `created_at` / `updated_at`. `Task` uses it; `Spec` does not yet.
- The `specs` app follows the same service/selector pattern (`specs/services.py`, `specs/selectors.py`); the flow
  itself is described in [`GENAI.md`](GENAI.md).

### Visibility

`selectors.task_list` and `selectors.task_get` scope to `created_by = user OR assigned_to = user`. Another user's task
answers **404**, not 403, so the API does not confirm it exists. Deleting is the only action restricted to the creator
(`services.task_delete`, 403 for the assignee). The HTMX client calls the same service; the delete rule is not
repeated in a view.

### Status transitions

All through `services`, from the dedicated endpoints, `PATCH` and HTMX:

- completing a completed task keeps `completed_at` (idempotent)
- reopening a task that is not done is a no-op
- `PATCH` to `done` sets `completed_at`; leaving `done` clears it
- a `CheckConstraint` (`task_completed_at_iff_done`) enforces it in the database

### Notifications

Services schedule `notify_assignment.delay(task_id)` (the Celery task in `tasks/tasks.py`, which calls
`tasks/notifications.py`) with `transaction.on_commit`, so a rolled-back transaction sends nothing. Tests capture the
callback with `django_capture_on_commit_callbacks`. If the broker is down the error appears in the process log after
commit, not in the request. `send_due_soon_digest` sends one e-mail per task, not one per person.

E-mail sending lives in `tasks/notifications.py` (`assignment_notify_send`, `due_soon_digest_send`, `_recipient`); the
Celery tasks in `tasks/tasks.py` only call those. `services.py` imports `notify_assignment` from `tasks/tasks.py` at
the top of the file; this is safe because `tasks.py` no longer imports `services`, so there is no import cycle (the
previous version imported it inside a function to avoid one).

### `is_overdue`

Derived, not stored. The `overdue=true` filter and `task_summary` apply the same rule in the query (`due_date < today
AND status != done`).

### HTMX client

`hypermedia/views.py` validates the form with a Django form and calls `task_create`, `task_complete`, `task_reopen`,
`task_delete`. A create response returns:

1. the form, re-rendered (target `#task-form`; 422 with errors when invalid, configured in `responseHandling`)
2. the updated rows through `hx-swap-oob` on `#board-body`, so the dialog and the table update in one response
3. `HX-Trigger: task-created`, so Alpine closes the dialog without client-side state duplication

Alpine only owns the dialog open/closed flag. Filters send one `hx-get` and push the URL. The patterns this client
shows:

- server-rendered partials with `hx-get` / `hx-target` / `hx-swap`
- out-of-band swap after create
- `HX-Trigger` to close the dialog
- 422 responses swapped into the form
- Alpine for local UI state only: the create dialog
- progressive enhancement: every action has a normal form/link fallback

### Authentication

| Client | Mechanism |
|---|---|
| React | JWT in the `Authorization` header (access 30 min, refresh 7 days, rotation and blacklist), single-flight refresh in `web/src/lib/api.ts` |
| HTMX | Django session, CSRF in the form and in `hx-headers` |

DRF uses JWT as the default authenticator; template views use `login_required`. The admin uses the session. `GET
/auth/users/` (operation `list_users`, schema `UserBrief`, built from `selectors.assignee_list`) returns only `id`,
`username`, `first_name`, `last_name`.

## Design decisions

### Scope: story and rules

The story is at the top of this file. The flow: sign in; see my tasks (created by me or assigned to me), filtered by
status and due date; create a task with title, description, due date and assignee; edit, complete and reopen; delete a
task I created; generate a spec from a Gitea issue, publish it back, and turn chosen steps into tasks. The rules that
follow from it:

- A task is visible only to its creator or assignee.
- Only the creator deletes.
- Completing is idempotent: completing twice does not change `completed_at`.
- Reopening clears `completed_at`.
- Assigning requires an active user.
- `is_overdue` is derived: due date before today and status not done.
- A past due date is accepted (backfill) and shown as overdue.

Out of scope: comments, attachments, labels, subtasks; real-time notifications; multi-tenant organizations;
drag-and-drop; free-form AI chat.

### Django 6.0 instead of 5.2 LTS

The target stack uses Django 6.x; my production history is 5.2 LTS. 6.0 on Python 3.12, checked in practice against
DRF 3.18, SimpleJWT 5.5, spectacular 0.29 and django-filter 25 (install, suite, schema). It aligns with the target and
gives template partials in the HTMX client. Risk: a less mature third-party ecosystem, mitigated by pins and local
checks. **Discarded:** 5.2 LTS, safer but does not demonstrate the requested stack.

### Why two clients

The target stack uses HTMX + Alpine as the server-rendered default and React for legacy interfaces. BLT shows both
halves over one domain:

- `web/`: React SPA, server state in TanStack Query, forms in React Hook Form.
- `hypermedia/`: Django pages, HTMX partials, Alpine for local UI state.

The point is that **the rule exists once**. If the React client is removed the API remains; if the API is dropped the
HTMX client still works. Both call the same services and selectors; the delete rule is written only in `task_delete`,
and `hypermedia/tests/test_delete_rule.py` checks the HTMX path returns its message with 403. It also proves the rule
is not tied to DRF, and one deploy serves both. **Discarded:** a separate Django project for the HTMX client; it would
duplicate settings, migrations and rules.

### Why layers, and why not more

Views validate, services decide, selectors scope, models keep invariants. There is no repository, use-case or DTO
layer: they added ceremony without a rule to put in them ("Clean Architecture" in a brief usually becomes ceremonial
layers). The service and selector names follow the HackSoft styleguide; the deviations are listed
[below](#review-against-the-hacksoft-django-styleguide). **Discarded:** full hexagonal architecture; more layers, no
additional rule.

### Why a service layer

The pattern is the Service Layer from Martin Fowler's *Patterns of Enterprise Application Architecture*: the endpoints
are thin controllers that only validate input, delegate to a transactional service layer and shape the response. Here
that layer is `tasks/services.py` (rules, `@transaction.atomic`), with `tasks/selectors.py` for reads. It was chosen
for two audiences.

**AI agents (CLI and IDE).** An agent working in a codebase has a noisy context and tends to hallucinate structure: it
invents a helper, puts a rule in a serializer, or copies a rule into a second view. A predictable layout keeps it
inside the pattern: rules in `services.py`, reads in `selectors.py`, views that only delegate. A fixed place for each
kind of code also makes continuous, modular testing possible: an agent that changes one rule runs the tests of that
one service.

**Humans.** *Predictability:* "where is the rule?" has one answer (`task_delete` holds the delete rule for the API and
HTMX alike). *Testability:* services and selectors are plain functions with keyword-only arguments, so
`tasks/tests/test_services.py` and `test_selectors.py` call them directly, with no `RequestFactory`, no `APIClient` and
no view mocks; endpoint tests only prove the wiring. *No fat models or fat views:* models keep data invariants, views
stay a few lines long. *Low cyclomatic complexity per file:* each service does one operation.

The cost is indirection: a reader follows view → service → selector instead of one class.

### Review against the HackSoft Django-Styleguide

Followed, checked in code (service and selector names are under [Layers](#layers)):

- Services are keyword-only (`def task_create(*, actor, title, ...)`), named `<entity>_<action>`, wrapped in
  `@transaction.atomic`, and call `full_clean()` before saving; `test_services_are_keyword_only` checks that positional
  calls raise `TypeError`. Selectors own the visibility scope, return querysets or plain data and never change data.
- Input is validated by an `InputSerializer` attribute on the view class (a plain `serializers.Serializer`, not a
  `ModelSerializer`). Most are nested; `TaskListApi` points it at the module-level `TaskInputSerializer` in
  `tasks/serializers.py`, because `specs` reuses the same item shape for tasks created from a spec.
- Views are thin: validate, call a service, return a `Response`, in the HTMX views too.

Deviations:

- **One `APIView` per URL, not one API per operation.** The styleguide asks for one API class per operation, so a CRUD
  resource is four classes. Here a class maps to a URL, so `TaskListApi` holds `GET` (list) and `POST` (create) and
  `TaskDetailApi` holds `GET`, `PATCH` and `DELETE`. It keeps the published paths, operation ids and OpenAPI component
  names unchanged (`ref_name` on each input serializer), with an explicit `@extend_schema` on each method, and "what
  does `POST /tasks/1/complete/` do" is answered by reading about 15 lines. The cost is that a class can hold more
  than one operation.
- **Output serializers live in `tasks/serializers.py`**, not in a nested `OutputSerializer`, because `TaskSerializer`
  is reused by several views and by `SpecTasksCreateApi`. The only nested `OutputSerializer` is in `specs/views.py`
  (`SpecTasksCreateApi`).
- **Errors are Django `ValidationError` and `PermissionDenied`**, translated to the DRF shape by `core/exceptions.py`,
  instead of a custom application error. The one custom exception, `SpecAlreadyPublishedError`, also lives in
  `core/exceptions.py` as a plain `Exception` (not a DRF one), so `specs/services.py` stays free of HTTP types; the
  handler maps it to 409.
- **Not every input serializer is nested.** `specs` and `tasks` follow the same service and selector pattern
  (`spec_generate`, `spec_publish`, `spec_tasks_create`, `spec_list`, `spec_get`, all keyword-only), but the issue URL
  or subject input is `SpecCreateSerializer` in `specs/serializers.py`, not nested in the view. `accounts` has no
  services or selectors module; its views are read-only or delegate to SimpleJWT, and `UserListApi` reuses
  `tasks.selectors.assignee_list` and `UserBriefSerializer` instead of its own query and serializer.
- **`task_update` takes a `data` dict** (the validated fields), not one argument per field.

### Why `APIView` and not `ViewSet`

The domain has operations with their own rules (complete, reopen, assign). A ViewSet hides the endpoint map behind a
router; a class with one method and one `@extend_schema` is explicit in review, every response has an explicit status,
and the transitions and their idempotency are readable in the file. The cost is more classes than a ViewSet.
**Discarded:** `ModelViewSet` + `@action`; less code, but it hides transitions and makes idempotency harder to
explain.

### Why 404 for another user's task

Detail lookups use the visibility selector, so a stranger gets 404, not 403, and cannot confirm the task exists. Only
delete is restricted to the creator.

### Why `is_overdue` is derived

"Overdue" changes as the day passes. A computed property plus an equivalent SQL filter is never stale; storing it
needs a nightly job and can drift. The cost is computing it on read, which is irrelevant at this volume.
**Discarded:** a boolean updated by a job.

### Why notifications use `on_commit`

A rolled-back transaction must not leave an e-mail for a task that never existed, so the Celery task is scheduled only
after commit. The API returns 201 before the e-mail leaves; a slow or dead broker does not block the request. In tests
the callback is captured explicitly. **Discarded:** a direct `.delay()`; simpler, but it notifies before the data is
guaranteed.

### Why two authentication mechanisms

React uses JWT (access 30 min, refresh 7 days, rotation and blacklist) with a single-flight refresh in `apiFetch`;
HTMX uses the Django session with CSRF. Both coexist. Keeping the tokens in `localStorage` is simple and CSRF-free for
a stateless API plus SPA without a backend-for-frontend, but it is exposed to XSS: production should use an `HttpOnly`
cookie with `SameSite` and CSRF, or a backend-for-frontend. A documented trade-off, not an ideal. **Discarded:** a
session cookie for React; it would need CSRF on every mutation and a same-origin proxy the exercise does not ask for.

### Why SQLite by default

The exercise accepts both databases and the reviewer must run it without friction: `make setup && make test` works
without Docker, with `DB_ENGINE=sqlite` by default. Compose runs PostgreSQL 16, and no feature depends on
Postgres-specific SQL. The risk is a feature that depends on Postgres-specific behavior and passes unnoticed, which is
why the delivery check also runs on Postgres. **Discarded:** requiring Postgres everywhere; more faithful, worse for
quick evaluation.

### Why drf-spectacular, not drf-yasg

The brief mentions drf-yasg, which only generates Swagger 2.0 and is no longer actively developed. drf-spectacular
emits OpenAPI 3, validates the schema in `make schema` (`--validate --fail-on-warn`, part of `make check`) and serves
Swagger UI at `/api/docs/`. A valid schema enters the delivery check, and the React client could be generated from it.
Cost: explicit annotations on every view. **Discarded:** drf-yasg; matches the text, worse technical decision.

### Why dependencies live in `pyproject.toml`, locked with uv

One file holds the runtime packages, the dev group and the tool configuration, and `api/uv.lock` pins the resolution;
the Docker image installs from the same lock, so a local run and the container use the same versions.
See [Dependencies](#dependencies).

### Why MinIO is behind a profile

MinIO images are no longer published and building takes minutes, so a local Dockerfile builds a pinned release behind
the `storage` profile. `make up` starts in seconds with the essentials; storage is optional and documented.
**Discarded:** MinIO on the default path; it would slow down the reviewer's first run.

### Why Gitea

It is a local issue tracker that runs in Compose with no account and no network, so anyone who clones the repository
gets a tracker with seeded issues, and the loop issue → spec → issue runs offline in a disposable environment. The
adapter (`specs/gitea.py`) is small enough to add another tracker. What depends on it and how to remove the dependency
are in [`GENAI.md`](GENAI.md#part-1-applied-ai-in-the-product). **Discarded:** the GitHub API; it works, but needs a
personal token with `issues:write` and ties the demo to network and account state.

### Why Tailwind in `web/`

The React client keeps Tailwind utilities (with `class-variance-authority`, `clsx` and `tailwind-merge`) over the
shared design tokens, the HTMX client uses plain CSS, and no component library is used.

### On Clean Architecture

The exercise asks for Clean Architecture. This project is layered and pragmatic, and it is **not** pure Clean
Architecture.

- **What holds.** Views validate and respond, services decide, selectors scope what a person may see, models keep
  invariants. The `tasks` services import no DRF, and both clients (React over the API, HTMX over Django views) call
  the same services and selectors, so a rule exists once.
- **Where it stops short.** Services use the Django ORM directly, so the rules are not independent of the database
  (there is no repository interface). There are no use-case classes or DTOs. The `specs` adapters (`generator.py`,
  `gitea.py`) raise DRF `APIException` subclasses for provider errors, so that part of the flow is tied to DRF's error
  handling. The dependency direction is held by convention (`AGENTS.md`) and review, not by a tool such as
  import-linter.
- **Why.** A repository layer over one ORM with one implementation, or a use-case class around a function, would wrap
  rules that do not exist. If the data layer had to change, services and selectors are the seam.

### On TDD

Not TDD. Tests were written with each rule, after it. What the project does keep is a service test and an endpoint
test for every rule, an 80% coverage floor in `make test`, and bugs reproduced by a failing test before the fix when
they were found later (the throttle on listing specs is an example, in
[`GENAI.md`](GENAI.md#part-2-tooling-and-how-the-code-was-produced)).

## Tests and quality

```sh
make test
```

231 tests, 95.75% statement coverage, enforced at 80% in `pyproject.toml`. Test locations: `tasks/tests`,
`specs/tests`, `accounts/tests`, `core/tests`, `hypermedia/tests`. Tests use no `time.sleep`, real clock or network;
dates are frozen with `freezegun`.

What is covered beyond the happy path:

- complete twice keeps the first `completed_at`; reopening clears it; the database rejects a done task without
  `completed_at`
- assigning an inactive user is rejected
- a stranger gets 404, not 403, for a task they cannot see
- an assignee can see a task but cannot delete it, through the API and through HTMX
- date range with a single bound, overdue filter, search across title and description
- throttling on login, refresh rotation, inactive users excluded from assignment
- e-mail is sent on commit, not on rollback
- the seed command is idempotent
- HTMX create returns an out-of-band update and a 422 form on invalid input
- spec flow: repository allowlist, plain-text rendering of model output, publish claim, tasks from a spec

Not covered by the suite: there is no automated browser test or React component test; the two client flows were
exercised by the manual round below.

**Lint and format.** `make lint` runs ruff on `api/` and `mcp_server/` and `tsc` on `web/`; `make check` adds the lock
check, the tests, the schema check and the web build. Pre-commit is described in [Commands and
configuration](#pre-commit). Ruff: line length 100, double quotes, sorted imports. `manage.py check`, ruff and `tsc`
run with no warnings; the browser console is clean.

**Schema.** `make schema` writes `api/schema.yaml` with `--validate --fail-on-warn`, so a view without a proper
annotation fails the check.

### End-to-end round in Chromium (2026-11-12)

A manual round on the running Compose stack: API behaviour, the React client and the HTMX client in Chromium (desktop
1440 px and phone 390 px), live model and tracker calls, and a cleanup that leaves the data as it found it. It is
**not** an automated suite in this repository: the script is Node with `playwright-core` and lives outside it, because
adding a browser dependency and a Docker-driving harness was not worth it for this delivery. It used four throwaway
users (`e2e_a`, `e2e_b`, `e2e_c`, one inactive) with a random password, so no seeded account or secret was touched. It
covered auth (401, refresh rotation, no e-mail leaked by `/auth/users/`), tasks (validation, pagination, every filter,
idempotent complete, visibility, delete rules), the assignment e-mail through Celery and Redis into Mailpit, Swagger
and the schema, the spec flow live, the React and HTMX flows, layout at both widths (no horizontal scroll, aligned
columns), a clean browser console, the login throttle (429 with `Retry-After`, never a 5xx) and a cleanup checked
against the baseline (Gitea back to its 13 issues, no `e2e_` user left).

Final pass: **API 29, React 52, HTMX 36, throttle 2, cleanup 3, all passing.** Five defects were found and fixed:

| Found | Where | Fixed by |
|---|---|---|
| `?status=bogus`, a bad date or a bad assignee id returned 200 with everything: the filter was dropped silently | API | `task_list` raises a validation error; the API answers 400 with the field, the HTMX board falls back to the unfiltered list. Tests: selector, endpoint, view |
| "Unassigned" rendered as "Unassignea": the italic last letter was clipped by `overflow: hidden` | both clients, desktop | right padding on the label |
| The "Due until" date was cut off on a phone | HTMX | the filters are one column below 520 px |
| The summary had four cards in React and five in HTMX | React | the "Done" card |
| The row Delete button had no task name in its accessible name | both | the button names the task, as Complete and Reopen already did |

Observed, not changed: `overdue=maybe` is read as "not filtered" (django-filter treats an unknown boolean as empty);
the "overdue only" checkbox is 16 px on a phone, though its label is clickable; Chromium reports a `204` answer to
`DELETE` as `net::ERR_ABORTED` even for a bare `fetch` (the app behaves correctly, so the round ignores that event); a
toast can cover the top-right navigation for a few seconds on the Specs page; the HTMX client shows no message when a
forged delete is refused (the button is hidden for a non-creator). Not covered: other browsers, keyboard-only
navigation, screen-reader output, load, the `storage` profile. The full account is in
[`GENAI.md`](GENAI.md#over-review-with-ai-the-end-to-end-round).

## UI

Both clients share one design language, taken from [ballastlane.com](https://ballastlane.com). The values below were
measured in a real browser (computed styles), not guessed:

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

The task list is a fixed grid in both clients (task, status, due date, assignee, actions), so every column starts at
the same x in every row; below 1024 px it becomes stacked cards. What differs per row is shown without moving the
columns: a due caption ("12 days overdue", "Due today", "Due tomorrow", "Completed 11 Nov", "No due date"), an
initials avatar with a "You" tag and "from <name>" when someone else created the task, an italic "Unassigned", an
orange stripe for overdue, a line-through for done, tooltips on the icon buttons, and a row hover. Long text is cut
with an ellipsis and keeps the full text in a tooltip. A fixed actions slot keeps the edit icon in place even when the
user cannot delete the task.

Orange is used only for fills, borders and the overdue marker: orange text on a light background fails WCAG AA, so the
Overdue badge uses `#B13A00` (5.43:1). Every text and background pair in the badges is at least 4.5:1. The tokens live
in one place per client (`web/src/index.css` and `api/hypermedia/static/hypermedia/app.css`). Not copied from the
site: the light/dark switch. Dates are shown in English. The HTMX scripts are loaded from a CDN with SRI hashes; fonts
load from Google Fonts. The HTMX patterns are listed under [HTMX client](#htmx-client).

## Demo script

Five minutes. Goal: show decisions, not screens; every block has one architecture sentence.

**1. Opening (40s).** Open the React board, already signed in.

> This is BLT, a task manager with two clients on one API. The React client is the
> required deliverable; the HTMX client is a bonus because your stack is
> hypermedia-first. The important part is that both call the same service layer — the
> rule exists once.

**2. React + contract (90s).**

- Filter by status and by date. Show pagination.
- Create a task and assign it to yourself.
- Open Mailpit and show the email the **Celery worker** sent.
- Sentence: *"The API returns 201 before the email leaves; sending is scheduled with `on_commit`, so a transaction
  that rolls back never notifies anyone."*

**3. Code: the boundary (90s).** Open `api/tasks/views.py`, `services.py`, `selectors.py` in that order.

> The view only validates and calls the service. The service owns the rule. The selector
> owns what a user can see. That is why the HTMX view below can reuse both.

Open `api/hypermedia/views.py` and show that it imports `tasks.services`.

**4. HTMX + Alpine (70s).** Open `/app/`.

- Filter (partial swap).
- Create a task through the dialog: show the response with `hx-swap-oob` in DevTools.
- Complete a row: swap of a single `<tr>`.
- Sentence: *"Alpine only stores whether the dialog is open. There is no list state in the client."*

**5. Spec from issue or subject (60s, if time allows).** Open the **Spec** tab, generate from Gitea issue #1
(`http://localhost:3000/blt/tasks/issues/1`) or from a typed subject, publish it as an issue, and create two tasks
from its steps. What the model is given and how its output is checked is in
[`GENAI.md`](GENAI.md#part-1-applied-ai-in-the-product); the same flow runs in the terminal through the MCP tools.

**6. Quality (60s).**

- `make test` → 231 tests, ~96%.
- Show one edge-case test: `test_complete_is_idempotent`.
- Tell **one** defect the AI introduced and you caught by running the code (invalid schema or 404/403); the account is
  in [`GENAI.md`](GENAI.md#part-2-tooling-and-how-the-code-was-produced).

**Questions to steer toward**

- "Why not a ViewSet?" → explainability of the endpoint map.
- "Why SQLite by default?" → reviewer runs without Docker; Compose runs Postgres.
- "Why two clients?" → proves the rule is not tied to DRF.

**What not to show**

- Do not open `admin/` unless asked.
- Do not show the MinIO profile; mention it in one sentence if infra comes up.
- Do not defend `localStorage` as ideal; call it a documented trade-off.

## Generative AI

BLT has one AI feature: from a Gitea issue URL or a short typed subject, `POST /api/v1/specs/` returns a validated
implementation spec, which can be published back as a Gitea issue and turned into tasks (rows `/specs/` in
[Endpoints](#endpoints)). One fixed task, no chat. The same flow is exposed to CLI agents as MCP tools in
`mcp_server/`.

The tooling behind the code, and the orchestration repository, are in [`GENAI.md`](GENAI.md).

- [Part 1: applied AI in the product](GENAI.md#part-1-applied-ai-in-the-product)
- [Part 2: tooling, and how the code was produced](GENAI.md#part-2-tooling-and-how-the-code-was-produced)
- [Over-review with AI: the end-to-end round](GENAI.md#over-review-with-ai-the-end-to-end-round)

## Trade-offs and limits

Reasons for the first three are under [Design decisions](#design-decisions).

- **Tokens in `localStorage`**, exposed to XSS; production should use `HttpOnly` cookies with CSRF or a backend-for-frontend.
- **SQLite by default**; Compose runs PostgreSQL. `is_overdue` is derived, so it costs a computation on read.
- **No automated browser or React component tests.** The API owns the rules and is covered; the two client flows were
  exercised by the [manual end-to-end round](#end-to-end-round-in-chromium-2026-11-12).
- **React filters are not in the URL**; the HTMX filters are.
- **The HTMX client has no drag-and-drop, edit dialog or inline editing.** It covers create, complete, reopen, delete and
  filters, enough to prove the architecture.
- **`page_size` is validated by the paginator**, not by the schema.
- **No optimistic locking:** concurrent edits are last-write-wins.
- **`seed` bypasses the services on purpose** (it writes fixtures directly). `Spec` does not use `core.models.BaseModel`.
- **No multitenancy:** a task belongs to its creator and one assignee. No attachments, comments or change history.
- **One tracker (Gitea) is supported**, through a small adapter (`specs/gitea.py`). The limits of the AI feature itself
  are in [`GENAI.md`](GENAI.md).
- **Hosted by script, not by CI.** The Railway services are uploaded with `railway up` (see
  [Hosting on Railway](#hosting-on-railway)), so a push does not redeploy them, and there is no CI pipeline.

## Next steps

1. Connect the Railway services to GitHub so a push redeploys them, and add a CI run of `make check`.
2. Browser tests of the React and HTMX flows; React component tests with Vitest.
3. Self-host the fonts.
4. AI backlog (text → task draft, issue triage before the spec, per-user AI budget, golden-issue evals): see
   [`GENAI.md`](GENAI.md).
5. Attachment upload using the MinIO profile.
