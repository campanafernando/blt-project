# BLT specs over MCP

The same spec flow is available to CLI agents, not only to the web UI. The server
exposes five tools and calls `specs.services` directly — no duplicated logic.

## Tools

| Tool | Input | Output |
|---|---|---|
| `list_open_issues` | `repo`, `limit` | Open issues in a public repository |
| `generate_spec` | `issue_url` | Validated spec persisted for the `cli` user |
| `list_specs` | `limit` | Recent specs generated from the CLI |
| `publish_spec` | `spec_id` | Creates the Gitea issue and returns the URL |
| `create_tasks_from_spec` | `spec_id`, `assignee_username`, `confirm` | Draft of tasks from the steps; writes only with `confirm=true` after human review |

## Setup

```sh
cd blt-project
make setup          # creates api/.venv and installs dev requirements (includes mcp)
```

The server needs the `opencode_api_key` secret (generation) and a Gitea token or the `blt_password`
secret (publishing), exactly like the API: both are files in `secrets/`, not `.env` entries.

## Clients

- **OpenCode**: the repository `opencode.json` already registers `blt-specs`.
- **Claude Code / Cursor / any MCP client**: `.mcp.json` at the repository root.
- **Manual stdio check**:

```sh
bash mcp_server/run.sh
```

## Example prompts

```text
List the open issues in blt/tasks.
Generate a spec for http://localhost:3000/blt/tasks/issues/1
Publish spec 3 as an issue and show me the link.
```

## Why it exists

The exercise asks for fluency with GenAI tools. The UI proves the product flow; the
MCP server proves the same capability is available where engineering work actually
happens — the terminal, with the same validation and the same rate limit scope.
