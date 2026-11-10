import re

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

ISSUE_URL = re.compile(
    r"^https?://(?:www\.)?github\.com/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)"
    r"/issues/(?P<number>\d+)(?:[/?#].*)?$"
)


class IssueNotFound(APIException):
    status_code = 404
    default_detail = "Issue não encontrada ou repositório privado."


class GitHubUnavailable(APIException):
    status_code = 502
    default_detail = "O GitHub não respondeu corretamente. Tente novamente."


class PublishUnavailable(APIException):
    status_code = 503
    default_detail = "Publicação desabilitada: defina GITHUB_TOKEN no ambiente."


def parse_issue_url(url: str) -> tuple[str, str, int]:
    match = ISSUE_URL.match((url or "").strip())
    if not match:
        raise ValidationError(
            {"issue_url": "Use uma URL de issue: https://github.com/owner/repo/issues/123"}
        )
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def _headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "BLT/0.1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
    return headers


def _request(method: str, path: str, **kwargs) -> dict:
    try:
        response = httpx.request(
            method,
            f"{settings.GITHUB_API_URL}{path}",
            headers=_headers(),
            timeout=15,
            follow_redirects=True,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise GitHubUnavailable() from exc

    if response.status_code == 404:
        raise IssueNotFound()
    if response.status_code in (401, 403, 429):
        raise GitHubUnavailable("GitHub recusou a requisição (autenticação ou limite de uso).")
    if response.status_code >= 400:
        raise GitHubUnavailable(f"GitHub respondeu {response.status_code}.")
    return response.json()


def fetch_issue(owner: str, repo: str, number: int) -> dict:
    data = _request("GET", f"/repos/{owner}/{repo}/issues/{number}")
    if "pull_request" in data:
        raise ValidationError({"issue_url": "A URL aponta para um pull request, não uma issue."})
    return {
        "url": data["html_url"],
        "title": data["title"],
        "body": data.get("body") or "",
        "repo": f"{owner}/{repo}",
        "number": number,
        "state": data["state"],
    }


def list_issues(repo: str, limit: int = 20) -> list[dict]:
    data = _request("GET", f"/repos/{repo}/issues?state=open&per_page={limit}")
    return [
        {
            "url": item["html_url"],
            "title": item["title"],
            "number": item["number"],
            "labels": [label["name"] for label in item.get("labels", [])],
        }
        for item in data
        if "pull_request" not in item
    ]


def create_issue(repo: str, title: str, body: str) -> dict:
    if not settings.GITHUB_TOKEN:
        raise PublishUnavailable()
    data = _request("POST", f"/repos/{repo}/issues", json={"title": title, "body": body})
    return {"url": data["html_url"], "number": data["number"]}
