# Architecture decisions

Short format: context, decision, consequence. What was discarded appears at the end of
each item, because the review question is usually "why not X?".

## 1. Django 6.0 instead of 5.2 LTS

**Context:** the target stack uses Django 6.x; my production history is 5.2 LTS.
**Decision:** 6.0 on Python 3.12, verifying DRF 3.18, SimpleJWT 5.5, spectacular 0.29 and
django-filter 25 in practice (install + suite + schema).
**Consequence:** alignment with the target and template partials in the HTMX client.
Risk: a less mature third-party ecosystem; mitigated by pins and CI.
**Discarded:** 5.2 LTS, safer but does not demonstrate the requested stack.

## 2. SQLite by default, PostgreSQL in Compose/CI

**Context:** the exercise accepts both; the reviewer must run it without friction.
**Decision:** `DB_ENGINE=sqlite` by default; Compose and CI use Postgres 16.
**Consequence:** `make setup && make test` works without Docker. The risk is a feature
depending on Postgres-specific behavior and passing unnoticed — that is why CI runs on
Postgres.
**Discarded:** requiring Postgres everywhere; more faithful, worse for quick evaluation.

## 3. Explicit `APIView`, no ViewSet

**Context:** the domain has six operations with their own rules (complete, reopen, assign).
**Decision:** one class per operation, with `@extend_schema`.
**Consequence:** the endpoint map is readable in the file; every response has an explicit
status. Cost: more classes than a ViewSet.
**Discarded:** `ModelViewSet` + `@action`; less code, but it hides transitions and makes
idempotency harder to explain in review.

## 4. Service and selector instead of repository/use case

**Context:** "Clean Architecture" in a brief usually becomes ceremonial layers.
**Decision:** three layers with real responsibility: view (HTTP), service (rules),
selector (query/scope). No DTO, repository or abstract interface.
**Consequence:** the rule exists once and is testable without HTTP. What does not exist
does not need explaining.
**Discarded:** full hexagonal architecture; more layers, no additional rule.

## 5. JWT in `localStorage`

**Context:** stateless API + SPA without a backend-for-frontend.
**Decision:** access and refresh in `localStorage`, single-flight refresh in `apiFetch`.
**Consequence:** simple and CSRF-free for the API; exposed to XSS. In production, an
`HttpOnly` cookie with `SameSite` and CSRF, or a BFF.
**Discarded:** session cookie for React; it would require CSRF on every mutation and a
same-origin proxy the exercise does not ask for.

## 6. drf-spectacular instead of drf-yasg

**Context:** the brief mentions drf-yasg, which is unmaintained and generates Swagger 2.
**Decision:** drf-spectacular, OpenAPI 3, with `--validate --fail-on-warn` in `make check`.
**Consequence:** a valid schema enters CI; the React client could be generated from it.
Cost: explicit annotations on every view.
**Discarded:** drf-yasg; matches the text, worse technical decision.

## 7. HTMX client in the same codebase

**Context:** the role uses HTMX + Alpine as the SSR default and React for legacy.
**Decision:** a `hypermedia` app inside the Django project, calling the same services.
**Consequence:** proves the rule is not tied to DRF. One deploy serves both.
**Discarded:** a separate Django project; would duplicate settings, migrations and rules.

## 8. `transaction.on_commit` for email

**Context:** assigning a task triggers a notification.
**Decision:** schedule the Celery task only after commit, with `on_commit`.
**Consequence:** there is never an email for a task that failed to save. In tests the
callback is captured explicitly.
**Discarded:** direct `.delay()`; simpler, but it notifies before the data is guaranteed.

## 9. Derived `is_overdue`

**Context:** "overdue" changes as the day passes.
**Decision:** a computed property and an equivalent SQL filter.
**Consequence:** never stale; negligible cost at this domain's volume.
**Discarded:** a boolean updated by a job; needs a job and suffers drift.

## 10. MinIO behind a profile

**Context:** MinIO images are no longer published; building takes minutes.
**Decision:** a local Dockerfile with a pinned release, behind the `storage` profile.
**Consequence:** `make up` starts in seconds with the essentials; storage is optional and
documented.
**Discarded:** MinIO on the default path; would slow down the reviewer's first run.

## 11. Gitea instead of GitHub for the issue flow

**Context:** the GenAI flow needs an issue tracker; the demo must run locally and not
depend on a personal account or rate limits.
**Decision:** Gitea in Compose, seeded by a management command. The integration speaks the
Gitea REST API and accepts token or basic auth.
**Consequence:** the full loop (issue → spec → issue) runs offline, in a disposable
environment. The cost is one more container.
**Discarded:** GitHub API; works, but requires a personal token with `issues:write` and
makes the demo depend on network and account state.
