# End-to-end round (2026-11-12)

A manual round on the running Compose stack: API behaviour, the React client and the HTMX client
in Chromium (desktop 1440 px and phone 390 px), live model and tracker calls, and a cleanup that
leaves the data as it found it. It is **not** an automated suite in this repository: the script
is Node with `playwright-core` and lives outside it, because adding a browser dependency and a
Docker-driving harness was not worth it for this delivery. This page records what was checked and
what it found, so the round can be repeated.

## How it ran

- `make up` first (the images are built from `api/uv.lock`), then the round on the live stack.
- Four throwaway users (`e2e_a`, `e2e_b`, `e2e_c`, one inactive) with a random password, so no
  seeded account or secret was read or touched. Every record they made carries the `e2e_` prefix or
  belongs to one of them.
- Phases: setup, API, React (desktop, an assignee's view, phone), HTMX (desktop and phone), login
  throttling, cleanup. Cleanup always runs last and is checked against the numbers taken before.

## What was checked

| Area | Checks |
|---|---|
| Auth | 401 without a token; wrong password; inactive user; refresh rotation and the old refresh token refused; `/auth/users/` leaks no e-mail |
| Tasks | create (trim, blank, 201 characters, inactive assignee); pagination (page size, next, previous, bad page); every filter and a combination; complete is idempotent; reopen; PATCH rules; assign; visibility (404 for a stranger, 403 for an assignee who deletes); summary; delete |
| Async | the assignment e-mail reaches Mailpit through Celery and Redis |
| Docs | Swagger UI and the OpenAPI 3 schema are served |
| Specs | input validation (neither, both, short, long, bad URL, foreign repository); **live**: subject → spec → Gitea issue → spec from that issue, second publish 409, tasks from a spec (Source line, limit of 10, all-or-nothing), a stranger gets 404 |
| React | login (wrong and right), board, create/edit/complete/reopen/delete with confirmation, filters and a debounced search, pagination, reload keeps the session, sign out, the Specs tab (both modes, counter, live generation, publish, tasks from the spec), an assignee sees no Delete on someone else's task |
| HTMX | login redirect, board, new-task dialog, a 422 for a 201-character title shown in the form, filter with a pushed URL, debounced search, complete/reopen/delete in place, a forged delete of someone else's task is a 403 |
| Layout | no horizontal scroll at either width; table columns start at the same x in every row (desktop); cards fit at 390 px; tap targets measured |
| Console | no warnings, no errors, no failed requests in any run |
| Throttle | the login endpoint answers 429 with `Retry-After` after a burst, never a 5xx |
| Cleanup | users, tasks, specs and the issues they published removed; throttle counters and their e-mails cleared; user, task, spec, Gitea-issue and e-mail counts equal the baseline |

## Result

Final pass: **API 29, React 52, HTMX 36, throttle 2, cleanup 3, all passing**. Gitea was back to
its 13 seeded issues and no `e2e_` user remained.

## Defects found, and what became of them

| Found | Where | Fixed by |
|---|---|---|
| `?status=bogus`, a bad date or a bad assignee id returned 200 with everything: the filter was dropped silently | API | `task_list` raises a validation error; the API answers 400 with the field, the HTMX board falls back to the unfiltered list instead of an error page. Tests: selector, endpoint, view |
| "Unassigned" rendered as "Unassignea": the slant of the italic last letter was clipped by `overflow: hidden` | both clients, desktop | right padding on the label |
| The "Due until" date was cut off on a phone | HTMX | the filters are one column below 520 px |
| The summary had four cards in React and five in HTMX | React | the "Done" card |
| The row Delete button was announced as "Delete" with no task name in HTMX, and the same generic name on every row in React | both | the button names the task, as Complete and Reopen already did |

## Observed, not changed

- `overdue=maybe` is read as "not filtered": django-filter treats an unknown boolean as empty by design.
- The "overdue only" checkbox is 16 px on a phone; its label is clickable, so tapping the text works.
- Chromium reports a `DELETE` answered with `204 No Content` as `net::ERR_ABORTED` even for a bare
  `fetch` with no React involved (checked in isolation); the server and the app behave correctly,
  so the round ignores that one event.
- A toast can cover the top-right navigation for a few seconds on the Specs page.
- The HTMX client has no edit dialog and shows no message when a forged delete is refused (the
  button is hidden for a non-creator, so only a hand-made request reaches that path).

## Not covered

Cross-browser (Chromium only), keyboard-only navigation, screen-reader output, load, and the
`storage` (MinIO) profile.
