# Design decisions

Why the project is built this way. For how the code is laid out today (layers, service and
selector names, endpoints, GenAI flow) read [`architecture.md`](architecture.md). The shorter,
numbered list of trade-offs reviewed by hand is [`ai/03-decisions.md`](ai/03-decisions.md).

## Why two clients

The target stack uses HTMX + Alpine as the server-rendered default and React for legacy
interfaces. BLT shows both halves over one domain:

- `web/` — React SPA, server state in TanStack Query, forms in React Hook Form.
- `hypermedia/` — Django pages, HTMX partials, Alpine for local UI state.

The point is that **the rule exists once**. If the React client is removed the API
remains; if the API is dropped the HTMX client still works. Both call the same services and
selectors; the delete rule is written only in `task_delete`, and
`hypermedia/tests/test_delete_rule.py` checks the HTMX path returns its message with 403.

## Why layers, and why not more

Views validate, services decide, selectors scope, models keep invariants. There is no
repository, use-case or DTO layer: they added ceremony without a rule to put in them. The
service and selector names follow the HackSoft styleguide.

One deliberate deviation: the styleguide groups an endpoint family in one API class; here
there is **one `APIView` per URL**. It keeps the published paths, operation ids and OpenAPI
component names unchanged, and "what does `POST /tasks/1/complete/` do" is answered by
reading about 15 lines. The cost is more classes.

## Why `APIView` and not `ViewSet`

A ViewSet hides the endpoint map behind a router. A class with one method and one
`@extend_schema` is explicit in review.

## Why 404 for another user's task

Detail lookups use the visibility selector, so a stranger gets 404, not 403, and cannot
confirm the task exists. Only delete is restricted to the creator.

## Why `is_overdue` is derived

Storing it needs a nightly job and can go stale. The cost is computing it on read, which is
irrelevant at this volume.

## Why notifications use `on_commit`

A rolled-back transaction must not leave an e-mail for a task that never existed. The API
returns 201 before the e-mail leaves; a slow or dead broker does not block the request.

## Why two authentication mechanisms

React uses JWT (access 30 min, refresh 7 days, rotation and blacklist); HTMX uses the Django
session with CSRF. Both coexist. The refresh token in `localStorage` is a documented
trade-off: production should use an `HttpOnly` cookie with `SameSite` and CSRF, or a
backend-for-frontend. See [`ai/03-decisions.md`](ai/03-decisions.md).

## Why SQLite by default

A reviewer runs `make setup && make test` without Docker. Compose runs PostgreSQL, and no
feature depends on Postgres-specific SQL.

## Why the spec flow is bounded

One fixed task, no free-form prompt: the input is a Gitea issue URL, the output is a JSON
contract, anything else is a 502. The value is the contract around the model call.
Publishing and task creation are separate, explicit actions; creating tasks from a spec
adds no model call. The hardening (repository allowlist, plain-text rendering of model output,
idempotent publish claim, throttles) is described in [`../GENAI.md`](../GENAI.md).

## Why Gitea

It is a local issue tracker that runs in Compose with no account and no network, so anyone who
clones the repository gets a tracker with seeded issues. What depends on it, and how to remove the
dependency, is in section 4 of [`../GENAI.md`](../GENAI.md). The adapter (`specs/gitea.py`) is small
enough to add another tracker.

## Limits

- No multitenancy: a task belongs to its creator and one assignee.
- No attachments, comments or change history.
- `hypermedia` has no inline editing and no drag-and-drop.
- One tracker (Gitea) is supported.
