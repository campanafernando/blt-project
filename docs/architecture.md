# Architecture — implementation decisions

## Layers

```
HTTP ──▶ View ──▶ Serializer ──▶ Service ──▶ Model
                                   │
                                   └──▶ Selector ──▶ QuerySet
```

| Layer | File | May | May not |
|---|---|---|---|
| View | `tasks/views.py`, `hypermedia/views.py` | Validate input, pick the status code, call a service | Know the ORM or decide a rule |
| Serializer | `tasks/serializers.py` | Validate the contract, shape the output | Write to the database directly |
| Service | `tasks/services.py` | Rules, state transitions, schedule effects | Build an HTTP response |
| Selector | `tasks/selectors.py` | Visibility scope, aggregations | Change data |
| Model | `tasks/models.py` | Data invariants, derived properties | Know about the request |

## Visibility

`tasks_for(user)` returns `created_by = user OR assigned_to = user`. Detail lookups use
the same scope, so another user's task answers **404**, not 403. That avoids confirming
the resource exists.

Deleting is the only action restricted to the creator (403 when the caller is only the
assignee).

## Status transitions

Every change goes through `services`:

- completing an already completed task does not change `completed_at` (idempotent)
- reopening a task that is not done is a no-op
- changing to `done` through PATCH sets `completed_at`
- leaving `done` clears `completed_at`

All three entry points (dedicated endpoint, PATCH, HTMX) use the same service.

## Notifications

`transaction.on_commit` schedules `notify_assignment.delay(task_id)`. If the transaction
rolls back, no email exists for a task that was never saved. In tests the callback is
captured by `django_capture_on_commit_callbacks`.

Sending does not block the response: the API returns 201 even if the broker is slow. If
the broker is down, the error shows up in the process log after commit, not in the request.

## `is_overdue`

Derived, not stored. It avoids a nightly job and stale state. The `overdue=true` filter
replicates the rule in SQL (`due_date < today AND status != done`).

## Two clients, one rule

The HTMX client imports `TaskCreateSerializer` and the services. The form uses the same
field names as the API. A create response returns:

1. the reset form (target `#task-form`)
2. the updated rows through `hx-swap-oob`
3. `HX-Trigger: task-created` so Alpine can close the dialog

No list state is kept in Alpine. It only owns the dialog open/closed flag.

## Authentication

| Client | Mechanism |
|---|---|
| React | JWT in the `Authorization` header, single-flight refresh in `web/src/lib/api.ts` |
| HTMX | Django session, CSRF in the form and in `hx-headers` |

Both coexist because DRF uses JWT as the default authenticator and template views use
`login_required`. The admin uses the session.

## Why `APIView` and not `ViewSet`

A ViewSet hides the endpoint map behind a router. Here every operation is a class with
one method and one `@extend_schema`. In review, "what does `POST /tasks/1/complete/` do"
is answered by reading 15 lines. The cost is more classes; the gain is explainability.

## Database

PostgreSQL in Compose; SQLite when `DB_ENGINE` is not `postgres`. The reason is
that a reviewer can run `make setup && make test` without Docker. No feature depends on
Postgres-specific SQL.

## GenAI flow

`POST /api/v1/specs/` accepts an issue URL, fetches the ticket from Gitea, sends a fixed
prompt to the OpenCode inference API, validates the JSON contract and persists a `Spec`.
`POST /specs/{id}/publish/` creates an issue in Gitea with the rendered markdown.

The issue body is untrusted data, truncated at 12k chars. The model has no tools and no
database access; its output is validated before storage. See
[`ai/04-spec-feature.md`](ai/04-spec-feature.md).

## Known gaps

- `page_size` is validated by the paginator, not by the schema.
- No optimistic locking: concurrent edits are last-write-wins.
- The daily digest sends one email per task, not one aggregated email per person.
