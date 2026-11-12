# GenAI feature — spec from issue

A small, bounded use of a language model: turn one Gitea issue into a structured
implementation spec, persist it, and optionally publish it back as an issue.

The point is not "AI chat". The point is a **contract**: one input, one fixed prompt,
one output schema, one persisted record.

## Flow

```
POST /api/v1/specs/ {issue_url}
  parse + validate issue URL       → 400 on anything else
  GET Gitea /api/v1/.../issues/N   → 404 / 502 on failure
  build fixed prompt (spec-v1)     → issue body truncated at 12k chars
  POST OpenCode /chat/completions  → response_format=json_object
  parse + validate schema          → 502 if outside contract
  persist Spec                     → model, prompt version, latency, input size
```

`POST /api/v1/specs/{id}/publish/` creates an issue in the same repository with the
rendered markdown and stores the resulting URL and number on the spec. The repository must
be in `GITEA_ALLOWED_REPOS` (default: `GITEA_REPO`). The publish is claimed first by
setting `published_issue_url` to `pending`; if the process dies after that, reset the
field by hand.

`POST /api/v1/specs/{id}/tasks/` creates up to 10 tasks from the steps the user picks. It
calls `task_create` for each one in one transaction and adds a `Source: <issue url>`
line to the description. It makes no model call.

## Output contract

```json
{
  "summary": "string",
  "acceptance_criteria": ["string"],
  "implementation_steps": ["string"],
  "risks": ["string"],
  "out_of_scope": ["string"],
  "size": "S | M | L"
}
```

Validated by `SpecPayloadSerializer` with list size limits. The response is stored as
structured fields plus a rendered `body_markdown`, so the published issue does not
depend on the model formatting.

## Prompt injection

The issue body is user-controlled. Controls:

1. The system prompt states the issue is data and instructions inside it must be ignored.
2. The issue is sent as a JSON object, not concatenated into the instruction.
3. The model has no tools, no database access, and no code execution.
4. Output is schema-validated; unknown keys and wrong types fail the request.
5. Nothing from the output is executed — it is displayed and, on publish, posted as
   issue text. The Markdown renderer (`specs/rendering.py`) writes model output as plain text:
   it strips links, images, HTML and bare URLs and escapes block syntax.

That does not make injection impossible; it makes the blast radius "a weird spec".

## Failure mapping

| Situation | Status | User message |
|---|---|---|
| URL is not an issue | 400 | Use an issue URL |
| Issue missing / private | 404 | Issue not found |
| Gitea auth or rate limit | 502 | Gitea refused the request |
| AI key absent | 503 | Generation disabled |
| Provider timeout | 502 | The provider did not answer in time |
| Invalid JSON or schema | 502 | Spec outside the contract |
| Publish without credentials | 503 | Publishing disabled |
| Spec already published | 409 | Spec already published. |

## Measured

Real call on Gitea issue #1 (attachments), model `deepseek-v4.1-flash`:

- 19.3s end to end, 19.2s in the provider
- 6 acceptance criteria, 6 steps, 5 risks; size `L`

## MCP / CLI

`mcp_server/server.py` exposes `list_open_issues`, `generate_spec`, `list_specs`,
`publish_spec` and `create_tasks_from_spec` (draft only unless `confirm=true`). It calls the same `specs.services` used by the API, wrapped in
`sync_to_async`. Configuration lives in `.mcp.json` and `opencode.json`.

## What was cut

- Creating tasks automatically from the spec. Tasks are created only after the user picks
  the steps (React dialog) or confirms the draft (MCP `confirm=true`).
- Free-text input, chat history, streaming, prompt editing in the UI.
- Multiple providers and model fallback.
- Embeddings or repository context — the issue is the only source.
