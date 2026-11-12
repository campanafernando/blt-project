# Review of the AI-generated code

A record of what the model produced, how the defect was found, and what changed. Every
item below happened in this repository and was found by running the code.

## 1. Dead permission class

**Generated:** `tasks/permissions.py` with `IsCreator`, a `BasePermission` subclass.
**Problem:** no view used it. The delete check was inlined in the view.
**Detection:** `pytest --cov` showed 0% for the file; reading confirmed no import.
**Fix:** file removed. An unused permission class suggests the rule exists in two places —
worse than not existing.
**Lesson:** low coverage in a small file is usually dead code, not a missing test.

## 2. Test reaching into client internals

**Generated:** `assigned_to=auth.handler._force_user` to build the "assignee cannot
delete" scenario.
**Problem:** `_force_user` is a private attribute of `APIClient`; the test passed by
accident and would break on any refactor.
**Fix:** the test receives the `user` fixture and uses `assigned_to=user`.
**Lesson:** if a test needs an underscore, the scenario is assembled wrong.

## 3. Invalid OpenAPI schema

**Generated:** `parameters=[TaskFilter]` inside an `APIView`, and `MeApi`/`UserListApi`
without `@extend_schema`.
**Problem:** `spectacular --validate --fail-on-warn` failed with "could not resolve
parameter annotation" and "unable to guess serializer". The README promised `/api/docs/`,
so this broke a deliverable, not a detail.
**Fix:** parameters declared with `OpenApiParameter` (status, dates, assigned_to, overdue,
search, page, page_size) and `@extend_schema(responses=...)` on both account views.
**Lesson:** the schema is a test. If it does not run in the delivery check, it rots.

## 4. Throttle leaking between tests

**Generated:** login with `throttle_scope = "login"` (10/min) and `LocMemCache`.
**Problem:** the suite signed in on almost every test; from the tenth request on, calls
became 429 and 15 tests failed in cascade. The error looked like broken authentication.
**Detection:** the message was `assert 429 == 200` inside the login fixture.
**Fix:** `cache.clear()` before and after each test, in an autouse fixture.
**Lesson:** throttling is global state. Any test that authenticates must clear the cache.

## 5. 403 vs 404 across clients

**Generated:** in the HTMX client, deleting another user's task returned 403.
**Problem:** the API answers 404 so it does not reveal that the resource exists. The HTMX
client did it differently for the same rule.
**Fix:** the test was changed to 404 and the behavior documented. The view uses the same
scope selector; the difference was only the expectation.
**Lesson:** two clients over one rule need a contract test comparing status codes, not
just the happy path.

## 6. Assertion on a DRF validation message

**Generated:** a test expecting the Portuguese validation message in the HTML.
**Problem:** `allow_blank=False` fires before `validate_title`, with a different (translated) message.
The test failed even though the response was correct (422 + form).
**Fix:** assert on structure (`id="task-form"` and status 422), not on text.
**Lesson:** asserting on a message is asserting on a translation. Assert on the contract.

## 7. Coverage started at 83%, not 97%

**Generated:** tests covering the happy path of the views.
**Problem:** `seed_demo` and the Celery digest were at 0% and 55%; the requirement was
80%, but the number hid real gaps.
**Fix:** a test for the idempotent seed and the digest (one task, one done, one without an
assignee), plus the service edge cases.
**Lesson:** coverage is a clue, not a goal. What matters is the edge nobody wrote.

## 8. MinIO without a published image

**Generated:** `image: minio/minio:latest` in Compose.
**Problem:** the official repository no longer exists; `docker compose up` would fail.
**Fix:** build the pinned release from source, behind the `storage` profile.
**Lesson:** AI-generated infrastructure assumes the image exists. Validate with
`docker compose build`, not by reading.

## 9. Versions assumed, not verified

**Generated:** Django 5.2 LTS out of habit.
**Decision:** moving to Django 6.0 requires checking DRF, SimpleJWT, spectacular and
django-filter. The check was installing and running the suite on Python 3.12 — it passed.
**Lesson:** "compatible" is the result of execution, not the model's memory.

## 10. Gitea returns `pull_request: null` on regular issues

**Generated:** the pull-request guard used `if "pull_request" in data`.
**Problem:** Gitea includes the key with `null` for every issue, so every URL was rejected
as a pull request. GitHub omits the key, which is why the first version worked.
**Fix:** `data.get("pull_request") is not None`; test keeps an explicit `{}` case.
**Lesson:** provider compatibility is a runtime property. The same API shape is not the
same payload.

## What the AI did well

- Layer structure consistent with the pattern already used in production
  (view → service → selector).
- JWT, pagination and throttling configured without inventing a library.
- Edge-case tests when the prompt listed the edge explicitly.
- React forms and components with no console warnings.

The pattern: **the more explicit the acceptance criteria, the better the output.**
