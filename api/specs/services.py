from django.conf import settings
from rest_framework.exceptions import APIException

from . import generator, github
from .models import Spec
from .rendering import render_markdown


class SpecAlreadyPublished(APIException):
    status_code = 409
    default_detail = "Spec já publicada."


def generate_spec(*, user, issue_url: str) -> Spec:
    if not settings.AI_ENABLED:
        raise generator.AIDisabled()

    owner, repo, number = github.parse_issue_url(issue_url)
    issue = github.fetch_issue(owner, repo, number)
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


def publish_spec(*, spec: Spec) -> Spec:
    if spec.published:
        raise SpecAlreadyPublished(f"Spec já publicada em {spec.published_issue_url}.")
    title = f"Spec: {spec.issue_title}"[:240]
    issue = github.create_issue(spec.repo, title, spec.body_markdown)
    spec.published_issue_url = issue["url"]
    spec.published_issue_number = issue["number"]
    spec.save(update_fields=("published_issue_url", "published_issue_number"))
    return spec
