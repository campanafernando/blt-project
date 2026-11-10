import re
from pathlib import Path

import httpx
from django.conf import settings
from rest_framework.exceptions import APIException, ValidationError

ISSUE_URL = re.compile(
    r"^https?://[^/\s]+/(?P<owner>[\w.-]+)/(?P<repo>[\w.-]+)"
    r"/issues/(?P<number>\d+)(?:[/?#].*)?$"
)


class IssueNotFound(APIException):
    status_code = 404
    default_detail = "Issue not found or repository is private."


class TrackerUnavailable(APIException):
    status_code = 502
    default_detail = "The issue tracker did not answer correctly. Try again."


class PublishUnavailable(APIException):
    status_code = 503
    default_detail = "Publishing is disabled: set GITEA_TOKEN or GITEA_USER/GITEA_PASSWORD."


def token() -> str:
    """Env token first; Compose provisions one in a mounted file."""
    if settings.GITEA_TOKEN:
        return settings.GITEA_TOKEN
    if settings.GITEA_TOKEN_FILE:
        path = Path(settings.GITEA_TOKEN_FILE)
        if path.is_file():
            return path.read_text().strip()
    return ""


def can_publish() -> bool:
    return bool(token() or (settings.GITEA_USER and settings.GITEA_PASSWORD))


def parse_issue_url(url: str) -> tuple[str, str, int]:
    match = ISSUE_URL.match((url or "").strip())
    if not match:
        raise ValidationError(
            {"issue_url": "Use an issue URL: http://localhost:3000/owner/repo/issues/1"}
        )
    return match.group("owner"), match.group("repo"), int(match.group("number"))


def _headers() -> dict:
    headers = {"Accept": "application/json", "User-Agent": "BLT/0.1"}
    value = token()
    if value:
        headers["Authorization"] = f"token {value}"
    return headers


def _basic_auth():
    if token():
        return None
    if settings.GITEA_USER and settings.GITEA_PASSWORD:
        return (settings.GITEA_USER, settings.GITEA_PASSWORD)
    return None


def _request(method: str, path: str, **kwargs) -> dict | list:
    try:
        response = httpx.request(
            method,
            f"{settings.GITEA_API_URL}{path}",
            headers=_headers(),
            auth=_basic_auth(),
            timeout=15,
            follow_redirects=True,
            **kwargs,
        )
    except httpx.HTTPError as exc:
        raise TrackerUnavailable() from exc

    if response.status_code == 404:
        raise IssueNotFound()
    if response.status_code in (401, 403, 429):
        raise TrackerUnavailable("Gitea refused the request (auth or rate limit).")
    if response.status_code >= 400:
        raise TrackerUnavailable(f"Gitea answered {response.status_code}.")
    if response.status_code == 204:
        return {}
    return response.json()


def fetch_issue(owner: str, repo: str, number: int) -> dict:
    data = _request("GET", f"/repos/{owner}/{repo}/issues/{number}")
    if data.get("pull_request") is not None:
        raise ValidationError({"issue_url": "That URL points to a pull request, not an issue."})
    return {
        "url": data["html_url"],
        "title": data["title"],
        "body": data.get("body") or "",
        "repo": f"{owner}/{repo}",
        "number": number,
        "state": data["state"],
    }


def list_issues(repo: str, limit: int = 20, state: str = "open") -> list[dict]:
    data = _request("GET", f"/repos/{repo}/issues?state={state}&limit={limit}")
    return [
        {
            "url": item["html_url"],
            "title": item["title"],
            "number": item["number"],
            "labels": [label["name"] for label in item.get("labels", [])],
        }
        for item in data
        if item.get("pull_request") is None
    ]


def create_issue(repo: str, title: str, body: str) -> dict:
    if not can_publish():
        raise PublishUnavailable()
    data = _request("POST", f"/repos/{repo}/issues", json={"title": title, "body": body})
    return {"url": data["html_url"], "number": data["number"]}


def unblock_account() -> bool:
    """Complete a forced password change through the web flow.

    Gitea flags CLI-created accounts and then rejects both basic auth and
    tokens until the password is changed. Reusing the same password clears
    the flag without a second credential.
    """
    user = settings.GITEA_USER
    password = settings.GITEA_PASSWORD
    if not user or not password:
        return False

    # Inside Compose, GITEA_URL is the browser-facing host; the API URL is internal.
    web_base = settings.GITEA_API_URL.removesuffix("/api/v1")
    client = httpx.Client(base_url=web_base, timeout=15, follow_redirects=True)
    login_page = client.get("/user/login")
    csrf = re.search(r'name="_csrf" value="([^"]+)"', login_page.text)
    if not csrf:
        return False
    client.post(
        "/user/login",
        data={"user_name": user, "password": password, "_csrf": csrf.group(1)},
    )
    page = client.get("/user/settings/change_password")
    csrf = re.search(r'name="_csrf" value="([^"]+)"', page.text)
    if not csrf:
        return False
    client.post(
        "/user/settings/change_password",
        data={
            "old_password": password,
            "password": password,
            "retype": password,
            "_csrf": csrf.group(1),
        },
    )
    return True


def ensure_repo(repo: str) -> None:
    """Create the demo repository if the authenticated user does not own it yet."""
    if not can_publish():
        raise PublishUnavailable()
    owner, name = repo.split("/", 1)
    try:
        _request("GET", f"/repos/{owner}/{name}")
        return
    except IssueNotFound:
        pass
    _request(
        "POST",
        "/user/repos",
        json={"name": name, "auto_init": True, "private": False, "default_branch": "main"},
    )
