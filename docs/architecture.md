# Architecture — overview

How the code is laid out and what each part does today. The reasons behind the choices
(two clients, `APIView`, JWT in `localStorage`, SQLite default, security model) are in
[`design-decisions.md`](design-decisions.md).

```
React (Vite) ─────┐
                  ├──▶ views → services → models
HTMX + Alpine ────┘          └─▶ selectors → QuerySet
                                    │
              Postgres ◀── Django ──┴──▶ Redis ──▶ Celery
                              │
                           Gitea (issues)
```

The API returns JSON; the `hypermedia` app renders HTML. Both call the same services and
selectors. The spec flow talks to Gitea through `api/specs/gitea.py`.

## Layers

| Layer | File | May | May not |
|---|---|---|---|
| View | `tasks/views.py`, `hypermedia/views.py` | Validate input, call a service, pick the status code | Query the ORM for a rule |
| Serializer | `InputSerializer` in the view class (`TaskListApi` aliases the shared `TaskInputSerializer` from `tasks/serializers.py`, which `specs` also reuses), `tasks/serializers.py` (output) | Validate the contract, shape the output | Decide a rule |
| Service | `tasks/services.py` | Rules, state transitions, schedule effects | Build an HTTP response |
| Selector | `tasks/selectors.py`, `tasks/filters.py` | Visibility scope, filters, aggregations | Change data |
| Model | `tasks/models.py`, `core/models.py` | Data invariants, constraints, derived properties | Know about the request |

Names follow the HackSoft styleguide. Deviations (one `APIView` per URL, so a list class holds
`GET` and `POST`; output serializers in `tasks/serializers.py`) are in
[`design-decisions.md`](design-decisions.md#review-against-the-hacksoft-django-styleguide).

- Services are keyword-only and atomic, call `full_clean()` and raise Django
  `ValidationError` / `PermissionDenied`: `task_create`, `task_update`, `task_complete`,
  `task_reopen`, `task_assign`, `task_delete`.
- Selectors: `task_list`, `task_get`, `task_summary`, `assignee_list`. `task_list` raises a Django
  `ValidationError` for an invalid filter value (the API turns it into a 400); the HTMX board catches it
  and shows the unfiltered list.
- `core/exceptions.py` is the DRF exception handler. It turns the Django exceptions into
  the DRF error shape (`detail`, or field → list).
- `core.models.BaseModel` (abstract) gives `created_at` / `updated_at`. `Task` uses it;
  `Spec` does not yet.
- E-mail sending lives in `tasks/notifications.py` (`assignment_notify_send`,
  `due_soon_digest_send`, `_recipient`). The Celery tasks in `tasks/tasks.py` only call those.
  `services.py` imports `notify_assignment` from `tasks/tasks.py` at the top of the file; this
  is safe because `tasks.py` no longer imports `services`, so there is no import cycle (the
  previous version imported it inside a function to avoid one).

## Visibility

`selectors.task_list` and `selectors.task_get` scope to `created_by = user OR
assigned_to = user`. Another user's task answers **404**, not 403, so the API does not
confirm it exists. Deleting is the only action restricted to the creator
(`services.task_delete`, 403 for the assignee). The HTMX client calls the same service; the
delete rule is not repeated in a view.

## Status transitions

All through `services`, from the dedicated endpoints, `PATCH` and HTMX:

- completing a completed task keeps `completed_at` (idempotent)
- reopening a task that is not done is a no-op
- `PATCH` to `done` sets `completed_at`; leaving `done` clears it
- a `CheckConstraint` (`task_completed_at_iff_done`) enforces it in the database

## Notifications

Services schedule `notify_assignment.delay(task_id)` (the Celery task in `tasks/tasks.py`, which
calls `tasks/notifications.py`) with `transaction.on_commit`, so a
rolled-back transaction sends nothing. Tests capture the callback with
`django_capture_on_commit_callbacks`. If the broker is down the error appears in the
process log after commit, not in the request. `send_due_soon_digest` sends one e-mail per
task, not one per person.

## `is_overdue`

Derived, not stored. The `overdue=true` filter and `task_summary` apply the same rule in the
query (`due_date < today AND status != done`).

## HTMX client

`hypermedia/views.py` validates the form with a Django form and calls `task_create`,
`task_complete`, `task_reopen`, `task_delete`. A create response returns:

1. the form, re-rendered (target `#task-form`; 422 with errors when invalid)
2. the updated rows through `hx-swap-oob` on `#board-body`
3. `HX-Trigger: task-created`, so Alpine closes the dialog

Alpine only owns the dialog open/closed flag. Filters send one `hx-get` and push the URL.

## Authentication

| Client | Mechanism |
|---|---|
| React | JWT in the `Authorization` header, single-flight refresh in `web/src/lib/api.ts` |
| HTMX | Django session, CSRF in the form and in `hx-headers` |

DRF uses JWT as the default authenticator; template views use `login_required`. The admin
uses the session. `GET /auth/users/` (operation `list_users`, schema `UserBrief`, built from
`selectors.assignee_list`) returns only `id`, `username`, `first_name`,
`last_name`.

## GenAI flow

`POST /api/v1/specs/` takes an issue URL or a typed subject. For an issue it fetches it from Gitea;
for a subject (target repository `GITEA_REPO`) it does not. Either way it sends the same fixed prompt
(`spec-v2`) to the OpenCode inference API, validates the JSON contract and stores a `Spec`
(`source` is `issue` or `subject`).

- Spec rules are in `specs/services.py` (`spec_generate`, `spec_publish`, `spec_tasks_create`);
  reads are in `specs/selectors.py` (`spec_list`, `spec_get`), both keyword-only like `tasks`.
- `POST /specs/{id}/publish/` creates a Gitea issue from the rendered Markdown. Model
  output is rendered as plain text. The publish is claimed first (`published_issue_url =
  "pending"`) so concurrent calls cannot create two issues. If the process dies after the
  claim, the marker stays and must be reset by hand. A second publish raises
  `core.exceptions.SpecAlreadyPublishedError`, which `core/exceptions.py` maps to 409.
- `POST /specs/{id}/tasks/` creates up to 10 tasks from chosen steps through
  `specs.services.spec_tasks_create` → `task_create`, in one transaction. Each task gets a
  `Source: <issue url>` line in its description (`Source: spec #<id>` for a subject spec). No extra LLM call.
- Repositories are limited by `GITEA_ALLOWED_REPOS` (default `GITEA_REPO`).
- Throttles: `spec` 10/h on `POST /specs/` only, `spec_publish` 30/h.
- `GET /specs/config/` returns only `ai_enabled` and `publish_enabled`.

The issue body is untrusted data, truncated at 12k chars; the model has no tools. See
[`ai/04-spec-feature.md`](ai/04-spec-feature.md).

## Known gaps

- `page_size` is validated by the paginator, not by the schema.
- No optimistic locking: concurrent edits are last-write-wins.
- `Spec` does not use `BaseModel`.
- `seed` writes through the ORM on purpose, not through the services.
- The React filters are not in the URL.
- No browser or E2E test of the React and HTMX flows.
