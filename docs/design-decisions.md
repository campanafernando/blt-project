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
service and selector names follow the HackSoft styleguide; the deviations are listed in
[Review against the HackSoft styleguide](#review-against-the-hacksoft-django-styleguide).

## Why a service layer

The pattern is the Service Layer from Martin Fowler's *Patterns of Enterprise Application
Architecture*: the endpoints are thin controllers that only validate input, delegate to a
transactional service layer and shape the response. Here that layer is `tasks/services.py`
(rules, `@transaction.atomic`), with `tasks/selectors.py` for reads. It was chosen for two
audiences.

**AI agents (CLI and IDE).** An agent working in a codebase has a noisy context and tends to
hallucinate structure: it invents a helper, puts a rule in a serializer, or copies a rule into a
second view. A predictable layout keeps it inside the pattern: rules in `services.py`, reads in
`selectors.py`, views that only delegate. A fixed place for each kind of code also makes
continuous, modular testing possible: an agent that changes one rule runs the tests of that one
service.

**Humans.**

- *Predictability:* "where is the rule?" has one answer. `task_delete` holds the delete rule for
  both the API and the HTMX client.
- *Testability:* services and selectors are plain functions with keyword-only arguments, so
  `tasks/tests/test_services.py` and `test_selectors.py` call them directly, with no
  `RequestFactory`, no `APIClient` and no view mocks. Endpoint tests then only prove the wiring.
- *No fat models or fat views:* models keep data invariants, views stay a few lines long.
- *Low cyclomatic complexity per file:* each service does one operation, so no file mixes
  parsing, rules, queries and response building.

The cost is indirection: a reader follows view → service → selector instead of one class.

### Review against the HackSoft Django-Styleguide

Followed, checked in code:

- Services are keyword-only (`def task_create(*, actor, title, ...)`), named `<entity>_<action>`, wrapped in
  `@transaction.atomic`, and call `full_clean()` before saving. (`test_services_are_keyword_only`
  checks that positional calls raise `TypeError`.)
- Selectors (`task_list`, `task_get`, `task_summary`, `assignee_list`) own the visibility scope
  and return querysets or plain data; they do not change data.
- Input is validated by an `InputSerializer` attribute on the view class (a plain
  `serializers.Serializer`, not a `ModelSerializer`). Most are nested; `TaskListApi` points it at
  the module-level `TaskInputSerializer` in `tasks/serializers.py`, because `specs` reuses the
  same item shape for tasks created from a spec.
- Views are thin: validate, call a service, return a `Response`. The HTMX views in
  `hypermedia/views.py` call the same services and selectors.

Deviations:

- **One `APIView` per URL, not one API per operation.** The styleguide asks for one API class
  per operation, so a CRUD resource is four classes. Here a class maps to a URL, so
  `TaskListApi` holds `GET` (list) and `POST` (create) and `TaskDetailApi` holds `GET`, `PATCH`
  and `DELETE`. It keeps the published paths, operation ids and OpenAPI component names
  unchanged (`ref_name` on each input serializer), with an explicit `@extend_schema` on each
  method, and "what does `POST /tasks/1/complete/` do" is answered by reading about 15 lines.
  The cost is that a class can hold more than one operation.
- **Output serializers live in `tasks/serializers.py`**, not in a nested `OutputSerializer`,
  because `TaskSerializer` is reused by several views and by `SpecTasksCreateApi`. The only nested
  `OutputSerializer` is in `specs/views.py` (`SpecTasksCreateApi`).
- **Errors are Django `ValidationError` and `PermissionDenied`**, translated to the DRF shape by
  `core/exceptions.py`, instead of a custom application error. The one custom exception,
  `SpecAlreadyPublishedError`, also lives in `core/exceptions.py` as a plain `Exception` (not a DRF
  one), so `specs/services.py` stays free of HTTP types; the handler maps it to 409.
- **Not every input serializer is nested.** `specs` and `tasks` follow the same service and
  selector pattern (`spec_generate`, `spec_publish`, `spec_tasks_create`, `spec_list`,
  `spec_get`, all keyword-only), but the issue URL or subject input is `SpecCreateSerializer` in
  `specs/serializers.py`, not nested in the view.
  `accounts` has no services or selectors module; its views are read-only or delegate to
  SimpleJWT, and `UserListApi` reuses `tasks.selectors.assignee_list` and `UserBriefSerializer`
  instead of its own query and serializer.
- **`task_update` takes a `data` dict** (the validated fields), not one argument per field.

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

## On Clean Architecture

The exercise asks for Clean Architecture. This project is layered and pragmatic, and it is **not**
pure Clean Architecture.

- **What holds.** Views validate and respond, services decide, selectors scope what a person may
  see, models keep invariants. The `tasks` services import no DRF, and both clients (React over the
  API, HTMX over Django views) call the same services and selectors, so a rule exists once.
- **Where it stops short.** Services use the Django ORM directly, so the rules are not independent of
  the database (there is no repository interface). There are no use-case classes or DTOs. The `specs`
  adapters (`generator.py`, `gitea.py`) raise DRF `APIException` subclasses for provider errors, so
  that part of the flow is tied to DRF's error handling. The dependency direction is held by
  convention (`AGENTS.md`) and review, not by a tool such as import-linter.
- **Why.** A repository layer over one ORM with one implementation, or a use-case class around a
  function, would wrap rules that do not exist; the decision is recorded in
  [`ai/03-decisions.md`](ai/03-decisions.md). If the data layer had to change, services and selectors
  are the seam.

## On TDD

Not TDD. Tests were written with each rule, after it. What the project does keep is a service test
and an endpoint test for every rule, an 80% coverage floor in `make test`, and bugs reproduced by a
failing test before the fix when they were found later (the throttle on listing specs is an example,
in [`../GENAI.md`](../GENAI.md)).

## Why the spec flow is bounded

One fixed task, no chat: the input is a Gitea issue URL or a short typed subject (data, never
instruction), the output is a JSON contract, anything else is a 502. The value is the contract around the model call.
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
