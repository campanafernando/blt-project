# GenAI feature — spec from issue

A small, bounded use of a language model: turn one GitHub issue into a structured
implementation spec, persist it, and optionally publish it back as an issue.

The point is not "AI chat". The point is a **contract**: one input, one fixed prompt,
one output schema, one persisted record.

## Flow

```
POST /api/v1/specs/ {issue_url}
  parse + validate GitHub URL      → 400 on anything else
  GET api.github.com/.../issues/N  → 404 / 502 on failure
  build fixed prompt (spec-v1)     → issue body truncated at 12k chars
  POST OpenCode /chat/completions  → response_format=json_object
  parse + validate schema          → 502 if outside contract
  persist Spec                     → model, prompt version, latency, input size
```

`POST /api/v1/specs/{id}/publish/` creates an issue in the same repository with the
rendered markdown and stores the resulting URL and number on the spec.

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
   issue text.

That does not make injection impossible; it makes the blast radius "a weird spec".

## Failure mapping

| Situation | Status | User message |
|---|---|---|
| URL not a GitHub issue | 400 | Use an issue URL |
| Issue missing / private | 404 | Issue não encontrada |
| GitHub auth or rate limit | 502 | GitHub recusou a requisição |
| AI key absent | 503 | Geração desabilitada |
| Provider timeout | 502 | O provedor não respondeu a tempo |
| Invalid JSON or schema | 502 | Spec fora do contrato |
| Publish without token | 503 | Publicação desabilitada |
| Spec already published | 409 | Já publicada, com o link |

## Measured

Real call on issue #1 (attachments), model `deepseek-v4.1-flash`:

- 14.7s end to end, 9.2s in the provider
- 7 acceptance criteria, 7 steps, 5 risks; size `M`
- cost reported by the provider: below USD 0.001

## MCP / CLI

`mcp_server/server.py` exposes `list_open_issues`, `generate_spec`, `list_specs` and
`publish_spec`. It calls the same `specs.services` used by the API, wrapped in
`sync_to_async`. Configuration lives in `.mcp.json` and `opencode.json`.

## What was cut

- Creating tasks automatically from the spec (the obvious next step, and a write path).
- Free-text input, chat history, streaming, prompt editing in the UI.
- Multiple providers and model fallback.
- Embeddings or repository context — the issue is the only source.
