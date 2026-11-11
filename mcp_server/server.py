"""MCP server exposing the BLT spec flow to CLI agents.

Run from the repository root (see mcp_server/run.sh). Tools call the same
services used by the HTTP API; there is no second implementation.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from mcp.server.fastmcp import FastMCP
from specs import gitea, selectors, services
from specs.models import Spec

DEFAULT_REPO = os.getenv("GITEA_DEFAULT_REPO", "blt/tasks")
MAX_DRAFT_TASKS = 10

mcp = FastMCP("blt-specs")


def _cli_user():
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username="cli", defaults={"email": "cli@blt.local", "first_name": "CLI"}
    )
    # Owner of CLI specs only: it must not log in or appear in assignee lists.
    if created or user.is_active or user.has_usable_password():
        user.is_active = False
        user.set_unusable_password()
        user.save(update_fields=["password", "is_active"])
    return user


def _spec_dict(spec: Spec) -> dict:
    return {
        "id": spec.id,
        "issue_url": spec.issue_url,
        "issue_title": spec.issue_title,
        "size": spec.size,
        "summary": spec.summary,
        "acceptance_criteria": spec.acceptance_criteria,
        "implementation_steps": spec.implementation_steps,
        "risks": spec.risks,
        "out_of_scope": spec.out_of_scope,
        "model": spec.model,
        "prompt_version": spec.prompt_version,
        "latency_ms": spec.latency_ms,
        "published_issue_url": spec.published_issue_url or None,
    }


def _list_specs(limit: int) -> list[dict]:
    specs = selectors.specs_for(_cli_user())[:limit]
    return [_spec_dict(spec) for spec in specs]


def _generate(issue_url: str) -> dict:
    return _spec_dict(services.generate_spec(user=_cli_user(), issue_url=issue_url))


def _publish(spec_id: int) -> dict:
    spec = selectors.get_spec(_cli_user(), spec_id)
    if spec is None:
        raise ValueError(f"Spec {spec_id} not found for the CLI user.")
    return _spec_dict(services.publish_spec(spec=spec))


def _create_tasks(spec_id: int, assignee_username: str, confirm: bool) -> dict:
    cli = _cli_user()
    spec = selectors.get_spec(cli, spec_id)
    if spec is None:
        raise ValueError(f"Spec {spec_id} not found for the CLI user.")
    draft = [
        {"title": step[:200].rstrip(), "description": step if len(step) > 200 else ""}
        for step in spec.implementation_steps[:MAX_DRAFT_TASKS]
    ]
    if not confirm:
        return {"confirmed": False, "tasks": draft}
    assignee = get_user_model().objects.filter(username=assignee_username, is_active=True).first()
    if assignee is None:
        raise ValueError(f"No active user named '{assignee_username}'.")
    tasks = services.spec_tasks_create(
        spec=spec, actor=cli, tasks=[{**item, "assigned_to": assignee} for item in draft]
    )
    return {
        "confirmed": True,
        "tasks": [{"id": t.id, "title": t.title, "assigned_to": assignee.username} for t in tasks],
    }


@mcp.tool()
async def list_open_issues(repo: str = DEFAULT_REPO, limit: int = 10) -> list[dict]:
    """List open issues in a Gitea repository (owner/repo)."""
    return await sync_to_async(gitea.list_issues)(repo, min(max(limit, 1), 30))


@mcp.tool()
async def generate_spec(issue_url: str) -> dict:
    """Generate a validated implementation spec from a Gitea issue URL."""
    return await sync_to_async(_generate)(issue_url)


@mcp.tool()
async def list_specs(limit: int = 10) -> list[dict]:
    """List the most recent specs generated from the CLI."""
    return await sync_to_async(_list_specs)(min(max(limit, 1), 50))


@mcp.tool()
async def publish_spec(spec_id: int) -> dict:
    """Publish a generated spec as a Gitea issue in its source repository."""
    return await sync_to_async(_publish)(spec_id)


@mcp.tool()
async def create_tasks_from_spec(
    spec_id: int, assignee_username: str, confirm: bool = False
) -> dict:
    """Turn the implementation steps of a spec into tasks for an active user.

    With confirm=false (default) nothing is written: it returns the draft, one
    {title, description} per step (max 10). Writing requires confirm=true, and only
    after the human has reviewed the draft. Tasks are assigned to `assignee_username`,
    which must be an active user.
    """
    return await sync_to_async(_create_tasks)(spec_id, assignee_username, confirm)


if __name__ == "__main__":
    mcp.run()
