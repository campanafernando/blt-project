# AI log

A dated record of the rounds of work with AI agents on this project: what I asked for, what came
back, what was wrong, and how I found out. The code was written by the agents; this log is the
part I did: scoping, reviewing, running and correcting. See [`GENAI.md`](../../GENAI.md) for the
summary and for the companion orchestration repository.

Each entry has a goal, the method, what was accepted, what was corrected and why.

---

## 2026-11-10 — Initial scaffold

**Goal:** the Django + DRF + React + HTMX base.

**Tool:** OpenCode with `deepseek-v4.1-flash`. The prompt is in
[`01-scaffold-prompt.md`](01-scaffold-prompt.md).

**Accepted without changes:** the settings structure driven by environment variables; the SimpleJWT
and drf-spectacular configuration.

**Corrected:**
- A permission class nobody used was removed (0% coverage exposed it).
- The OpenAPI schema was repaired with explicit parameters and response serializers.
- Throttle state leaked between tests; the cache is cleared per test.
- The API and the HTMX client disagreed on 404 versus 403.
- The MinIO image was replaced by a pinned build from source.

**Discarded:** repository and use-case layers, which added ceremony without a rule to put in them;
`drf-yasg`, which is Swagger 2 only and no longer actively developed.

**Lesson:** the prompt sets the rules; the failures were in what the prompt did not say.

---

## 2026-11-10 — Spec from an issue

**Goal:** one bounded GenAI feature, with no free-form prompt.

**Accepted:** the JSON contract and the fixed system prompt; storing the model, the prompt version,
the latency and the input size with each spec.

**Corrected:**
- Gitea returns `pull_request: null` on regular issues, and the first guard rejected every issue.
- The provider needs an `x-opencode-session` header; without it the call was a 400.
- Publishing needed an explicit decision: writing is opt-in, never a side effect of generating.

**Discarded:** free chat, streaming, multiple providers, and creating tasks from the spec (postponed
to keep a single write path, then added with a confirmation step).

**Lesson:** the value of a GenAI feature is the contract around it, not the model call.

---

## 2026-11-11 — Audit and refactor with parallel sub-agents

**Goal:** audit the whole project, then fix what the audit found: security, the service layer, the
UI, and the missing "tasks from a spec" feature.

**Method:** I read the code myself, wrote a ranked list of findings, and split the fixes into eight
workstreams with disjoint file ownership so no two agents edited the same file. Each agent got its
files, the contract it had to keep and the checks it had to pass; I integrated the results and ran
everything together.

**Accepted:** a repository allowlist for the issue flow; model output rendered as plain text before
it is published; an idempotent publish claim; narrower user and config endpoints; a separate
publish throttle; `NUM_PROXIES`; a Gitea bot that is not an admin; per-service environment in
Compose; the HackSoft naming (`task_*` services, `task_list`/`task_get`/`task_summary` selectors,
an exception handler for Django exceptions, `BaseModel`, a `CheckConstraint` on `completed_at`); the
HTMX views reusing the services; jargon removed from both UIs; spec to tasks (endpoint, React
dialog, MCP tool with `confirm`).

**Corrected during integration:**
- The HTMX form stayed prefilled after a successful create.
- `published` counted the `pending` publish marker as published.
- A test created a done task without `completed_at`, which the new constraint rejects.
- A Postgres role script had never worked: psql does not expand variables inside a `$$` block.

**Deviation kept on purpose:** one API class per URL, not one per resource, to keep the published
paths, operation ids and schema.

**Live run.** The stack was recreated from scratch and exercised end to end. It found three things
that tests with mocks had not:
- the Gitea seed got 403, because creating a repository needs the `write:user` scope; the token now
  has every scope, which is a decision for a local test stack, with the repository allowlist as
  the guard;
- the MinIO read-only user could not list the bucket, because the built-in `readonly` policy has no
  `ListBucket`; it now has a policy scoped to the bucket, and writes and deletes were checked to be
  denied;
- a real spec generation failed with "invalid JSON": reasoning tokens share `max_tokens`, so longer
  answers were cut off. The cap is 4,000, and a truncated or empty answer has its own message. The
  failure was intermittent and was reproduced by forcing a small limit, not by waiting for it.

**A misread instruction, reverted.** An ambiguous request to make the repository self-contained was
taken as "move tooling into it". The intent was the opposite. The move was stopped and reverted
file by file, because the moved files already had edits from two agents.

**Verified:** 186 tests at 96.8% coverage, `ruff`, `manage.py check`, `makemigrations --check`,
OpenAPI validation with no warnings, React typecheck and build, `docker compose config -q`.

**Lesson:** disjoint ownership kept parallel work from colliding, but every seam (a constraint
against test data, a marker against a counter, SQL against psql variables, token scope against the
seed) showed up only when the pieces ran together against real services. And an ambiguous
instruction is cheaper to confirm than to move and revert.

---

## 2026-11-11 — UI aligned with ballastlane.com

**Goal:** make the fonts, colours and components of both clients match the Ballast Lane site.

**Method:** the first palette was recalled, not measured. I read the computed styles of the live
site in a headless browser (body, headings, buttons, links, navigation, fields, labels, cards,
footer), wrote them down as one token table, and gave the same table to two agents with disjoint
files. The measurement corrected three assumptions: the body font is Space Grotesk, not Poppins;
the primary button is orange with dark text, not blue with white text; and the corners are 8 px for
controls and 10 px for cards.

**Verification:** a script compares 60 computed values in both running clients with the measured
tokens (all match), checks that no font other than Space Grotesk and IBM Plex Mono loads, computes
the WCAG contrast of the key pairs (all at least 4.5:1), and takes screenshots that I looked at.

**Corrected or kept on purpose:** orange text fails AA on light backgrounds, so orange is used only
for fills and borders; an HTMX mobile bug (the check button clipped by a CSS specificity clash) was
fixed along the way; no dark theme.

**Lesson:** "follows the site" is only a claim until the numbers are read from the site and compared
with the running app.

---

## 2026-11-11 — Task table alignment

**Goal:** a screenshot showed status badges drifting per row, the edit icon sliding when a task could
not be deleted, and the same labels repeated on every row.

**Method:** I named the causes from the screenshot (no status column, an actions cell whose width
depended on permissions, per-row labels), wrote one spec for both clients (a fixed grid, what each
per-row difference looks like, tooltips, hover) and gave it to two agents in parallel. The check was
a script: it creates deliberately uneven rows (a 140-character title, no date, no assignee, overdue,
due today and tomorrow, done, created by someone else) and measures every cell's position in both
clients at five widths.

**Result and a correction:** 56 checks pass. Reading the screenshots side by side still found three
inconsistencies the numbers did not (HTMX dates in a different font and without a leading zero, and
an extra badge that made overdue rows taller), which I fixed afterwards.

---

## 2026-11-11 — Secrets in files, and a password rotation

**Goal:** no password or key in code, documentation, `.env`, tests or a container's environment,
with every login still working.

**Design:** one mechanism: files in `secrets/`, mounted by Compose under `/run/secrets` and read by
`config/secret_files.py` (the environment is only a fallback for CI). `make env` creates them and
moves any value still in an old `.env`, unchanged, so existing logins and volumes needed no change.
A shared password that had appeared in earlier commits was then retired with `make password`, which
also issues a new Django key so no earlier session or token survives.

**Checked, not assumed:** every migrated value was compared by hash with the old one; a scan of
`docker inspect` for all 13 containers found no secret value; each service was listed to confirm it
reads only what it needs (the worker does not see the shared password or the AI key); a token and a
refresh token issued before the rotation get 401.

**What my first check missed:** `gitea admin user change-password` marks the account "must change
password" unless told otherwise, and Gitea then refuses its API. My first login check counted any
page other than the login form as success, which included the forced-change page, so it passed while
the bot was blocked; a 403 on the API exposed it. The init now passes `--must-change-password=false`,
the check classifies the landing page, the two other accounts are updated instead of only created,
and old API tokens are revoked because Gitea keeps them alive after a password change.

**Lesson:** a check that cannot fail is not a check. The second look found what the first one
accepted.
