import httpx
import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from specs import gitea


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


def test_parse_accepts_common_issue_urls():
    expected = ("blt", "tasks", 12)
    for url in (
        "http://localhost:3000/blt/tasks/issues/12",
        "http://127.0.0.1:3000/blt/tasks/issues/12",
        "https://gitea.example.com/blt/tasks/issues/12/",
        "http://localhost:3000/blt/tasks/issues/12#issuecomment-1",
    ):
        assert gitea.parse_issue_url(url) == expected


@pytest.mark.parametrize(
    "url",
    (
        "",
        "http://localhost:3000/blt/tasks",
        "http://localhost:3000/blt/tasks/pulls/1",
        "not a url",
    ),
)
def test_parse_rejects_other_urls(url):
    with pytest.raises(ValidationError):
        gitea.parse_issue_url(url)


def test_fetch_issue_maps_fields(monkeypatch):
    monkeypatch.setattr(
        gitea,
        "_request",
        lambda *args, **kwargs: {
            "html_url": "http://localhost:3000/blt/tasks/issues/1",
            "title": "Add attachments",
            "body": "files please",
            "state": "open",
        },
    )
    issue = gitea.fetch_issue("blt", "tasks", 1)
    assert issue == {
        "url": "http://localhost:3000/blt/tasks/issues/1",
        "title": "Add attachments",
        "body": "files please",
        "repo": "blt/tasks",
        "number": 1,
        "state": "open",
    }


def test_fetch_issue_rejects_pull_requests(monkeypatch):
    monkeypatch.setattr(
        gitea,
        "_request",
        lambda *args, **kwargs: {
            "html_url": "x",
            "title": "t",
            "body": "",
            "pull_request": {},
        },
    )
    with pytest.raises(ValidationError):
        gitea.fetch_issue("blt", "tasks", 1)


def test_request_maps_404(monkeypatch):
    monkeypatch.setattr(gitea.httpx, "request", lambda *a, **k: FakeResponse(404))
    with pytest.raises(gitea.IssueNotFound):
        gitea.fetch_issue("blt", "tasks", 1)


def test_request_maps_rate_limit(monkeypatch):
    monkeypatch.setattr(gitea.httpx, "request", lambda *a, **k: FakeResponse(403))
    with pytest.raises(gitea.TrackerUnavailable):
        gitea.fetch_issue("blt", "tasks", 1)


def test_request_maps_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(gitea.httpx, "request", boom)
    with pytest.raises(gitea.TrackerUnavailable):
        gitea.fetch_issue("blt", "tasks", 1)


@override_settings(GITEA_TOKEN="", GITEA_USER="", GITEA_PASSWORD="")
def test_create_issue_requires_credentials():
    with pytest.raises(gitea.PublishUnavailable):
        gitea.create_issue("blt/tasks", "title", "body")


@override_settings(GITEA_TOKEN="token")
def test_create_issue_returns_url_and_number(monkeypatch):
    monkeypatch.setattr(
        gitea,
        "_request",
        lambda *args, **kwargs: {
            "html_url": "http://localhost:3000/blt/tasks/issues/9",
            "number": 9,
        },
    )
    assert gitea.create_issue("blt/tasks", "Spec: x", "body") == {
        "url": "http://localhost:3000/blt/tasks/issues/9",
        "number": 9,
    }


@override_settings(GITEA_TOKEN="", GITEA_USER="blt", GITEA_PASSWORD="secret")
def test_basic_auth_also_enables_publishing():
    assert gitea.can_publish() is True


@override_settings(GITEA_TOKEN="token")
def test_ensure_repo_skips_when_it_exists(monkeypatch):
    calls = []
    monkeypatch.setattr(gitea, "_request", lambda *args, **kwargs: calls.append(args) or {})
    gitea.ensure_repo("blt/tasks")
    assert calls[0][:2] == ("GET", "/repos/blt/tasks")


@override_settings(GITEA_TOKEN="token")
def test_ensure_repo_creates_when_missing(monkeypatch):
    calls = []

    def fake_request(method, path, **kwargs):
        calls.append((method, path))
        if path == "/repos/blt/tasks":
            raise gitea.IssueNotFound()
        return {"name": "tasks"}

    monkeypatch.setattr(gitea, "_request", fake_request)
    gitea.ensure_repo("blt/tasks")
    assert calls[-1][0] == "POST"
    assert calls[-1][1] == "/user/repos"


@override_settings(GITEA_TOKEN="token", GITEA_REPO="blt/tasks")
def test_bootstrap_creates_only_missing_issues(monkeypatch):
    from django.core.management import call_command

    from specs.management.commands.gitea_bootstrap import ISSUES

    created = []
    monkeypatch.setattr(gitea, "ensure_repo", lambda repo: None)
    monkeypatch.setattr(
        gitea,
        "list_issues",
        lambda repo, limit=50, state="all": [{"title": ISSUES[0][0]}],
    )
    monkeypatch.setattr(
        gitea,
        "create_issue",
        lambda repo, title, body: (
            created.append(title)
            or {"url": "http://localhost:3000/blt/tasks/issues/1", "number": 1}
        ),
    )
    call_command("gitea_bootstrap")
    assert len(created) == len(ISSUES) - 1
    assert ISSUES[0][0] not in created


@override_settings(GITEA_TOKEN="", GITEA_USER="", GITEA_PASSWORD="")
def test_bootstrap_requires_credentials():
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("gitea_bootstrap")
