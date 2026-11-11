# Demo — five-minute script

Goal: show decisions, not screens. Every block has one architecture sentence.

## 1. Opening (40s)

> This is BLT, a task manager with two clients on one API. The React client is the
> required deliverable; the HTMX client is a bonus because your stack is
> hypermedia-first. The important part is that both call the same service layer — the
> rule exists once.

Open the React board, already signed in.

## 2. React + contract (90s)

- Filter by status and by date. Show pagination.
- Create a task assigned to Maria.
- Open Mailpit and show the email the **Celery worker** sent.
- Sentence: *"The API returns 201 before the email leaves; sending is scheduled with
  `on_commit`, so a transaction that rolls back never notifies anyone."*

## 3. Code — the boundary (90s)

Open `api/tasks/views.py`, `services.py`, `selectors.py` in that order.

> The view only validates and calls the service. The service owns the rule. The selector
> owns what a user can see. That is why the HTMX view below can reuse both.

Open `api/hypermedia/views.py` and show that it imports `tasks.services`.

## 4. HTMX + Alpine (70s)

Open `/app/`.

- Filter (partial swap).
- Create a task through the dialog: show the response with `hx-swap-oob` in DevTools.
- Complete a row: swap of a single `<tr>`.
- Sentence: *"Alpine only stores whether the dialog is open. There is no list state in
  the client."*

## 5. Spec from issue (60s, if time allows)

- Open the **Spec** tab and paste issue #1 from Gitea (`http://localhost:3000/blt/tasks/issues/1`).
- Show the generated spec: criteria, steps, risks, size, latency.
- Click **Publish as issue** and open the link created in Gitea.
- Sentence: *"The input is a URL, not a prompt. The model returns a JSON contract that we
  validate; anything else is a 502. The issue body is treated as untrusted data."*
- Mention the MCP: *"The same flow is available in the terminal through four MCP tools."*

## 6. Quality and AI (60s)

- `make test` → 87 tests, ~96%.
- Show one edge-case test: `test_complete_is_idempotent`.
- Open `docs/ai/02-review.md` and tell **one** defect the AI introduced and you caught by
  running the code (invalid schema or 404/403).
- Sentence: *"The prompt set the rules; the failures were in what the prompt did not say —
  global cache between tests, container permissions, HTTP status parity."*

## Questions you should steer toward

- "Why not a ViewSet?" → explainability of the endpoint map.
- "Why SQLite by default?" → reviewer runs without Docker; Compose runs Postgres.
- "Why two clients?" → proves the rule is not tied to DRF.

## What not to show

- Do not open `admin/` unless asked.
- Do not show the MinIO profile; mention it in one sentence if infra comes up.
- Do not defend `localStorage` as ideal; call it a documented trade-off.
