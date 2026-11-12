from django.conf import settings
from django.db import transaction

from core.exceptions import SpecAlreadyPublishedError
from tasks.models import Task
from tasks.services import task_create

from . import generator, gitea
from .models import Spec
from .rendering import render_markdown


def spec_generate(*, user, issue_url: str) -> Spec:
    generator.require_ai()

    owner, repo, number = gitea.parse_issue_url(issue_url)
    issue = gitea.fetch_issue(owner, repo, number)
    payload, latency_ms, truncated, input_chars = generator.generate_payload(issue)

    spec = Spec.objects.create(
        issue_url=issue["url"],
        repo=issue["repo"],
        issue_number=issue["number"],
        issue_title=issue["title"],
        summary=payload["summary"],
        acceptance_criteria=payload["acceptance_criteria"],
        implementation_steps=payload["implementation_steps"],
        risks=payload["risks"],
        out_of_scope=payload["out_of_scope"],
        size=payload["size"],
        model=settings.OPENCODE_MODEL,
        prompt_version=settings.SPEC_PROMPT_VERSION,
        latency_ms=latency_ms,
        input_chars=input_chars,
        truncated=truncated,
        created_by=user,
    )
    spec.body_markdown = render_markdown(spec)
    spec.save(update_fields=("body_markdown",))
    return spec


PUBLISH_CLAIM = "pending"


def spec_publish(*, spec: Spec) -> Spec:
    # Claim first so concurrent calls cannot both create an issue. If the process dies
    # after the claim, the spec stays "pending" and needs a manual reset: we accept
    # that over a duplicate issue.
    claimed = Spec.objects.filter(pk=spec.pk, published_issue_url="").update(
        published_issue_url=PUBLISH_CLAIM
    )
    if not claimed:
        raise SpecAlreadyPublishedError()
    title = f"Spec: {spec.issue_title}"[:240]
    try:
        issue = gitea.create_issue(spec.repo, title, spec.body_markdown)
    except Exception:
        Spec.objects.filter(pk=spec.pk).update(published_issue_url="")
        raise
    spec.published_issue_url = issue["url"]
    spec.published_issue_number = issue["number"]
    spec.save(update_fields=("published_issue_url", "published_issue_number"))
    return spec


def spec_tasks_create(*, spec: Spec, actor, tasks: list[dict]) -> list[Task]:
    source = f"Source: {spec.issue_url}"
    with transaction.atomic():
        created = []
        for item in tasks:
            description = item.get("description", "").strip()
            if source not in description.splitlines():
                description = f"{description}\n\n{source}".strip()
            created.append(task_create(actor=actor, **{**item, "description": description}))
        return created
