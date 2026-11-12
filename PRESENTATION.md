# BLT: my thought process

BLT (Backlog, Lists & Tasks) is my answer to the Python technical exercise. This document is the presentation: what I
understood, what I decided and why, how I worked, and what I would not claim. The GenAI part, which the exercise
treats as mandatory, is in [`GENAI.md`](GENAI.md); the setup, the architecture and the decisions in full are in
[`README.md`](README.md).

## Delivery checklist

- One public repository, this one. The complete solution is here.
- `GENAI.md` at the root, as requested, and this presentation.
- No symlinks anywhere in the repository.
- Setup instructions and seeded data: the [README](README.md#quick-start-one-command-everything-seeded).
- A plus: the whole stack is also hosted on Railway, with the same seeded data
  (see [section 8](#8-the-hosted-demo)).

## 1. The user story

> As someone who organizes work, I want to record tasks, assign them to someone and track what is late, so I do not
> miss deadlines and know who owns what.

From that, the requirements became rules I could test:

- You see the tasks you created and the tasks assigned to you, and nothing else. A stranger gets a 404, not a 403, so
  the task cannot be confirmed to exist.
- Only the creator deletes. Anyone with access can complete or reopen.
- Completing twice keeps the original `completed_at`; reopening clears it. The database enforces it with a constraint.
- You cannot assign a task to an inactive user, and the assignee is e-mailed in the background, only after the change
  is committed.
- "Overdue" is computed from the due date, never stored, so it cannot go stale.
- The list is paginated and filters by status, due date, assignee, overdue and text.

## 2. How I read the exercise

| The exercise asks for | Where it is |
|---|---|
| CRUD, assign, complete, filters by status and due date | the API; filters also by assignee, overdue and text |
| JWT | SimpleJWT, access 30 min, refresh 7 days with rotation and a blacklist |
| Pagination | 10 per page, up to 100 |
| PostgreSQL or SQLite | both: SQLite by default so a reviewer runs it without Docker, PostgreSQL in Compose |
| Tests, at least 80% | 231 tests, 95.75% coverage; every rule has a service test and an endpoint test |
| Dockerfile and docker-compose | multi-stage images; Compose runs Postgres, Redis, Mailpit, Gitea, the API, a worker, a scheduler and the web client |
| README, Swagger, `pyproject.toml`, pre-commit | README; Swagger UI from `drf-spectacular` (OpenAPI 3, validated in `make schema`; `drf-yasg` is Swagger 2 and no longer actively developed); dependencies and tool configuration in `api/pyproject.toml`, locked with `uv`; ruff and hygiene hooks |
| Rate limiting | DRF throttles per scope: login 10/min, spec generation 10/hour, publishing 30/hour |
| Background processing | Celery + Redis: the assignment e-mail and a daily digest |
| Responsive React client with CRUD | React 19, TypeScript, TanStack Query; a fixed table grid that becomes stacked cards below 1024 px |
| Seeded data and credentials | `make up` seeds three users, 19 tasks and a Gitea with 13 issues |
| GenAI, mandatory | [`GENAI.md`](GENAI.md) |

**What I added on purpose.** A second, server-rendered client with HTMX and Alpine over the *same* services, to show
that the rules live in one place and are not tied to a UI. One bounded GenAI feature: turn a tracker issue, or a
typed subject, into an implementation spec, publish it back as an issue and turn its steps into tasks. And the hosted
demo.

**What I left out on purpose:** multi-tenancy, attachments, comments, history, drag-and-drop and a free-form AI chat.
They are listed as limits, not hidden.

## 3. The architecture

```
React (Vite) ──JSON──┐
                     ├──► views ──► services (rules) ──► models / PostgreSQL
HTMX + Alpine ─HTML──┘        └──► selectors (who sees what)
                                     │
                         Celery + Redis (e-mail, daily digest)
                                     │
        specs: issue or subject ─► model ─► JSON contract ─► stored spec ─► tasks / published issue
                                   ▲
                                Gitea (the tracker)
```

I chose a **Service Layer** (Martin Fowler, *Patterns of Enterprise Application Architecture*): views are thin
controllers that only validate and delegate to services; selectors own the reads; models keep invariants. Two reasons.
For people: it is predictable (a calculation rule is in `services.py`, a heavy listing in `selectors.py`), the rules
are plain functions that are tested without request mocks, and models and views do not grow fat. For AI agents, which
suffer from noisy context and from writing code outside the project's pattern: a fixed layout keeps them inside it
and makes continuous, modular testing possible. I follow the HackSoft Django styleguide (keyword-only services,
selectors, thin views) and the README lists where I bend it.

| Decision | Why |
|---|---|
| Thin explicit `APIView`s, no `ViewSet` | the endpoint map is readable in `urls.py`; the rule behind `POST /tasks/1/complete/` is about 15 lines |
| One class per URL | keeps the published paths and the OpenAPI contract unchanged (the styleguide says one API per operation; this is a deviation) |
| 404 for another user's task | a stranger cannot learn that it exists |
| Derived `is_overdue` | no nightly job, nothing to go stale |
| E-mail on `transaction.on_commit` | a rolled-back change never notifies anyone |
| JWT for React, session with CSRF for HTMX | each client uses what fits it; the refresh token in `localStorage` is a documented trade-off |
| A repository allowlist and plain-text rendering in the AI flow | the model's text is untrusted, and the AI cannot be pointed at any repository |

**On Clean Architecture.** The architecture is layered and pragmatic, and it is **not** pure Clean Architecture.
Services do not import DRF (the `specs` adapters do raise DRF exceptions for provider errors), and both clients call
the same services and selectors. But services use the Django ORM directly, there are no repository interfaces,
use-case classes or DTOs, because they would wrap rules that do not exist, and the dependency direction is held by
convention and review, not by a tool. I would defend that choice, and I would also say where it stops short.

## 4. The two clients

React consumes JSON; HTMX consumes HTML fragments. In HTMX, a filter is one `hx-get` that swaps the rows and pushes
the URL, a create returns the updated rows through `hx-swap-oob` and an `HX-Trigger` that closes the dialog, and
Alpine only holds whether the dialog is open. The delete rule exists once, in `task_delete`, and a test checks that
the HTMX path returns its message with a 403. If the React client were removed the API would remain; if the API were
dropped the HTMX client would still work.

## 5. The GenAI feature

The feature goes both ways with the tracker: **issue → spec** (paste the link of a Gitea issue), **subject → spec**
(type one sentence), **spec → a new Gitea issue** (published once; a second time is a 409), and **spec → tasks**
(only the steps a person picks, never automatically). The same flow is exposed to terminal agents as an MCP server.

- **The contract.** One fixed prompt, `spec-v2`, generic over both inputs. The input goes to the model as a JSON
  object, never inside the instruction, and the answer must match a schema (summary, acceptance criteria, steps,
  risks, out of scope, size). Anything else is refused with a plain message. A vague input becomes a stated
  assumption in the risks, not an invented fact.
- **The guardrails.** The issue or subject is untrusted data; the model has no tools; the output is stripped of links,
  images and HTML before it is published; only an allowlisted repository can be read or written; generation is limited
  per user and per hour; publishing is claimed first so two clicks cannot create two issues.
- **A real run**, on the hosted demo: a subject became a spec in about 20 seconds, was published as an issue in Gitea,
  and that new issue was fed back in as a link and produced another spec.
- **Honest limits.** The size estimate is not stable between runs; one provider and one model; Gitea is the only
  adapter (another tracker is a new adapter, not a rewrite); the MCP tools skip the HTTP rate limits.

Everything about it, including the prompt, is in [`GENAI.md`](GENAI.md#part-1-applied-ai-in-the-product).

## 6. How I worked, and how the code was produced

**I built this with AI coding agents, under my direction.** I set the architecture, the business rules, the prompts and
the scope of each agent, and I reviewed every result. The conventions the agents followed were set by me: the naming of
files and symbols, the styleguide, and how each layer is created and what it may hold; I audited each commit against
those directives and sent back what broke them.

My order of work:

1. **The contract and the rules first**: the business rules as testable sentences, the structure, and the checks every
   result had to pass (tests, coverage, OpenAPI validation, lint).
2. **The API with tests**, then the React client against the contract.
3. **The HTMX client**, as proof that the rules exist once.
4. **The GenAI feature**, kept small and bounded.
5. **An audit of my own work**, which found real problems and fixed them.
6. **Running it for real**: the stack rebuilt from scratch and driven with a headless browser. Most of the defects worth
   knowing about appeared only there, not in the unit tests.

**The tooling.** I used OpenCode with parallel sub-agents, each with a written scope and the files it owns; two
read-only specialist agents, one for the task rules and one for the spec flow, that review changes against them; CodeGraph to
query the code structurally before changing it; read-only MCP servers over the database and the object store, so an
agent sees real data without a write credential; and review skills for a second look at each change. The prompt I would
use, the corrections table and the log of every round are in
[`GENAI.md`](GENAI.md#part-2-tooling-and-how-the-code-was-produced).

*Honorable mention, for curiosity only:* the way the agents were run lives in a small separate repository I made on
the side. It is not part of this delivery, nothing here depends on it, and everything needed to evaluate the work is in
this repository. It is described in [`GENAI.md`](GENAI.md#22-the-orchestration-repository), for anyone who is curious.

**What the AI got wrong, found by running the code**, four examples from a longer table:

- A throttle on the whole spec list view made reading the history spend the *generation* quota (found by a test that
  lists twelve times).
- A model output limit of 1,200 tokens cut longer answers, and they surfaced as "invalid JSON" (a real call, then a
  fix and a message for a cut-off answer).
- A "read-only" database role granted on every table exposed password hashes and refresh tokens (reading what the
  grant covered; it is now two tables and a view).
- Publishing a spec twice created two issues (reading the check-then-write; now the publish is claimed first).

## 7. Over-review with AI: an end-to-end round in a real browser

After the code passed its tests, I used AI a second time to over-review it. An end-to-end script drove the **running
stack in Chromium**, at desktop and at phone width, through the API, the React client and the HTMX client, with the
real model and the real Gitea, using throwaway users and a cleanup checked against the counts taken before. A second
pass reviewed the whole project: read-only reviewers, a clean clone without the AI key, and the pre-commit hooks.

The final pass was API 29, React 52, HTMX 36, throttling 2 and cleanup 3 checks, all passing, and it found **five
defects that I fixed**: an invalid filter value silently returned everything (now a 400), the italic "Unassigned"
clipped in both clients, a date cut off on a phone in the HTMX client, a missing "Done" card in the React summary,
and row buttons without the task's name for screen readers. The clean clone also found a test that only passed
because the AI key existed on my machine.

It is a manual round, not a suite in the repository: committing it would add a browser dependency and a harness that
drives Docker. What it checked and what it found are in
[`GENAI.md`](GENAI.md#over-review-with-ai-the-end-to-end-round).

## 8. The hosted demo

As a plus, the stack runs on Railway with the same seeded users, password and data as `make up`: nine services (the
web client, the API, a Celery worker and scheduler, a one-shot seed, Gitea, Mailpit, Postgres and Redis), where only the
web client, Gitea and Mailpit are public. I built it from the structure of another project of mine that is already
published there, with the Railway CLI and MCP, and compared the hosted and the local data item by item (19 tasks, 13
issues). The infrastructure is described in `infra/railway/` and recreated, or checked against what runs, by one idempotent script, `infra/railway/deploy.py`. I could also have declared it
with Terraform, and would, if you prefer that. How it was built, and what went wrong on the way, is in the README
([Hosting on Railway](README.md#hosting-on-railway)) and in [`GENAI.md`](GENAI.md#29-hosting-the-project-the-railway-cli-and-mcp-on-the-base-of-ana).

## 9. What I would not claim

- **Not TDD**, which the exercise calls preferable. Tests came with each rule, after it. What I kept: a service test and
  an endpoint test for every rule, an 80% coverage floor, and a failing test before the fix for bugs found later.
- **Not pure Clean Architecture** (section 3).
- **No load testing.** Performance choices (query shape, indexes, pagination) are reasoned and checked, not measured
  under load.
- **No automated browser tests in the repository.** The two clients were exercised by the manual round in section 7;
  the rules are covered by the API tests.
- **The GenAI feature needs the AI key and a tracker.** Gitea ships in Compose and on the hosted demo; the key is a
  secret and is not in the repository. Without a key everything else works and spec generation says it is unavailable.
- **A deliberately simple demo setup**: one shared password for the seeded users and Gitea, and a Gitea token with every
  scope in the local stack. Both are for a demo and are documented as such; the refresh token in `localStorage` is a
  documented trade-off.

## 10. Try it

**Hosted** (credentials are sent with the submission):

- App: <https://web-production-c97d5880.up.railway.app> (the HTMX client is under `/app/`)
- Gitea: <https://gitea-production-2ea7f1ac.up.railway.app> (login `blt@mail.com`)
- Users: `fernando`, `ballast`, `lane`

**Locally:**

```sh
git clone https://github.com/campanafernando/blt-project && cd blt-project
BLT_PASSWORD='<password from the submission e-mail>' make up
```

A five-minute path: sign in to the React client and show the board and its filters; create a task and assign it to
someone, then open Mailpit to see the e-mail the worker sent; open the HTMX client and see the same rules; open Gitea,
take issue #13, generate a spec in the **Specs** tab (*From an issue*), create tasks from two of its steps and publish
it back as an issue; then try *From a subject*, with one sentence of your own.

## 11. What I would do next

- Browser tests of the React and HTMX flows in the repository, and React component tests.
- The AI backlog, in order of value: text to a task draft, issue triage before the spec (questions when the issue is
  vague), a per-user AI budget with token usage logged, and golden-issue checks that assert the schema without the
  network.
- Attachments through the MinIO profile that already exists.
- Tighten the Gitea token scopes and the shared demo password before any shared deployment; self-host the fonts.
