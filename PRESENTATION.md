# BLT — my thought process

BLT (Backlog, Lists & Tasks) is my answer to the Python technical exercise. This document is the
presentation: what I understood, what I decided and why, how I worked, and what I would not claim.
The GenAI part, which the exercise treats as mandatory, is in [`GENAI.md`](GENAI.md).

## Delivery checklist

- One public repository, this one. The complete solution is here.
- `GENAI.md` at the root, as requested.
- A presentation: this file.
- No symlinks anywhere in the repository.
- Setup instructions and seeded data: [`README.md`](README.md), "Quick start".

## 1. The user story

> As someone who coordinates a small team, I want to create tasks, assign them to people and track
> their deadlines, so that nothing slips and everyone sees their own work.

From that, the exercise's requirements became concrete behaviour:

- You see the tasks you created and the tasks assigned to you, and nothing else.
- Only the creator can delete a task; anyone with access can complete or reopen it.
- Completing a task twice keeps the original completion time; reopening clears it.
- You cannot assign a task to an inactive user, and the assignee is e-mailed, in the background,
  and only after the change is committed.
- "Overdue" is computed from the due date, never stored, so it cannot go stale.
- The list is paginated and filters by status, due date, assignee and text.

## 2. How I read the exercise

**What it asks for**, and where it is: CRUD, assignment, completion and filters (the API, section
"Endpoints" of the README); JWT (SimpleJWT with refresh rotation); pagination; PostgreSQL or SQLite
(both: SQLite by default so a reviewer can run it without Docker, PostgreSQL in Compose); tests at 80%
or more (186 tests, 96.8%); Dockerfile and compose; README, Swagger and pre-commit; rate limiting
(per-scope throttles); Celery and Redis (assignment e-mails and a daily digest); a responsive React
client with CRUD; seeded data; and the GenAI section.

**What I added on purpose.** A second, server-rendered client with HTMX and Alpine over the *same*
services, to show that the rules live in one place and are not tied to a UI. And one bounded GenAI
feature: turn an issue from a tracker into an implementation spec, and the spec into tasks.

**What I left out on purpose:** multi-tenancy, attachments, comments and history. They are listed
as limits, not hidden.

**On Clean Architecture.** The architecture is layered and pragmatic: views validate and respond,
services decide, selectors scope what a user may see, models keep invariants. Services do not
depend on DRF, and the two clients call the same functions. It is **not** pure Clean Architecture:
the services still use the Django ORM directly, and I did not add repositories or use-case classes
because they would have wrapped rules that do not exist. I would defend that choice, and I would
also say where it stops short.

## 3. Architecture in one picture

```
React (Vite) ──JSON──┐
                     ├──► views ──► services (rules) ──► models / PostgreSQL
HTMX + Alpine ─HTML──┘        └──► selectors (who sees what)
                                     │
                         Celery + Redis (e-mail, daily digest)
                                     │
        specs: issue ─► model ─► JSON contract ─► stored spec ─► tasks / published issue
                  ▲
               Gitea (local tracker)
```

| Decision | Why |
|---|---|
| Services and selectors, thin explicit `APIView`s, no `ViewSet` | the rule behind `POST /tasks/1/complete/` is readable in about 15 lines |
| One API class per URL | keeps the published paths and the OpenAPI contract unchanged |
| 404, not 403, for another user's task | a stranger cannot learn that it exists |
| Derived `is_overdue` | no nightly job, nothing to go stale |
| E-mail on `transaction.on_commit` | a rolled-back change never notifies anyone |
| JWT for React, session with CSRF for HTMX | each client uses what fits it; the refresh token in `localStorage` is a documented trade-off |
| `drf-spectacular`, not `drf-yasg` | OpenAPI 3 and still maintained; the schema is validated in `make schema` |

The long version, one section per decision, is in [`docs/design-decisions.md`](docs/design-decisions.md),
and the layout of the code is in [`docs/architecture.md`](docs/architecture.md).

## 4. How I worked

The code was written by AI agents that I directed (details and evidence in [`GENAI.md`](GENAI.md)).
My order of work was:

1. **The contract and the rules first.** The business rules as testable sentences, the structure,
   and the checks every result had to pass (tests, coverage, OpenAPI validation, lint).
2. **The API with tests**, then the React client against the contract.
3. **The HTMX client**, as a proof that the rules exist once.
4. **The GenAI feature**, kept small and bounded.
5. **An audit of my own work**, which found real problems (a repository the spec flow could be
   pointed at, a read-only database role that could read password hashes, a throttle that charged
   reads against the generation quota) and fixed them.
6. **Running it for real.** The stack was rebuilt from scratch and driven with a headless browser.
   Most of the defects worth knowing about appeared only there, not in the unit tests.
7. **Measuring the UI instead of guessing.** The visual design follows ballastlane.com, but the
   values were read from the live site's computed styles and compared with the running app by a
   script, because I had been wrong about the font, the button colour and the corner radii.

## 5. What I would not claim

- **Not TDD.** Tests came with each rule, after it, not before.
- **Not pure Clean Architecture** (see above).
- **No load testing.** Performance choices (query shape, indexes, pagination) are reasoned and
  checked, not measured under load.
- **No automated browser tests.** The two clients were exercised with a manual headless-browser
  script; the rules are covered by the API tests.
- **The GenAI feature needs the AI key and a Gitea.** Gitea ships in Compose; the AI key does not
  ship in the repository (it is a secret). Without a key everything else works and spec generation
  says it is unavailable.
- **A deliberately simple local setup**: one shared password for the seeded users and a Gitea
  token with every scope. Both are for a local test stack and are documented as such.

## 6. Try it

```sh
git clone https://github.com/campanafernando/blt-project && cd blt-project
BLT_PASSWORD='<password>' make up
```

`make up` builds, starts everything, seeds three users (`fernando`, `ballast`, `lane`) with the
password you give, loads 19 sample tasks and a Gitea with 13 issues, and prints the addresses.
Issue #13 ("Export the task list to CSV") has no task and is there to try the spec flow.

A five-minute path: sign in to the React client and show the board and its filters; create a task and
assign it to someone, then open Mailpit to see the e-mail the worker sent; open the HTMX client and
see the same rules; open Gitea, take issue #13, generate a spec, create tasks from two of its steps
and publish it back as an issue. Section 3 of [`GENAI.md`](GENAI.md) explains what happens in that
last step.
