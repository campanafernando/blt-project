import httpx
import pytest
from django.test import override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

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
    with pytest.raises(gitea.TrackerUnavailable) as caught:
        gitea.fetch_issue("blt", "tasks", 1)
    assert str(caught.value.detail) == "The issue tracker refused the request. Try again later."


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

    from specs.management.commands.gitea_bootstrap import (
        ISSUES,
        SPEC_PRACTICE_ISSUE,
        synced_issues,
    )

    created = []
    monkeypatch.setattr(gitea, "ensure_repo", lambda repo: None)
    monkeypatch.setattr(gitea, "ensure_collaborator", lambda repo, username: None)
    monkeypatch.setattr(
        gitea,
        "list_issues",
        lambda repo, limit=50, state="all": [{"title": ISSUES[0][0]}],
    )
    monkeypatch.setattr(
        gitea,
        "create_issue",
        lambda repo, title, body, assignees=None: (
            created.append((title, assignees))
            or {"url": "http://localhost:3000/blt/tasks/issues/1", "number": 1}
        ),
    )
    call_command("gitea_bootstrap")
    titles = [title for title, _ in created]
    assert ISSUES[0][0] not in titles
    assert len(titles) == len(ISSUES) - 1 + len(synced_issues()) + 1
    assert titles[-1] == SPEC_PRACTICE_ISSUE[0]
    assert dict(created)["Audit the API rate limits"] == ["lane"]
    assert dict(created)[SPEC_PRACTICE_ISSUE[0]] == []


@override_settings(GITEA_TOKEN="", GITEA_USER="", GITEA_PASSWORD="")
def test_bootstrap_requires_credentials():
    from django.core.management import call_command
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        call_command("gitea_bootstrap")


def test_parse_error_is_generic():
    with pytest.raises(ValidationError) as caught:
        gitea.parse_issue_url("nope")
    assert "localhost" not in str(caught.value.detail)


def test_allowlist_blocks_fetch_list_and_create(monkeypatch):
    calls = []
    monkeypatch.setattr(gitea, "_request", lambda *a, **k: calls.append(a) or {})
    with pytest.raises(ValidationError):
        gitea.fetch_issue("other", "repo", 1)
    with pytest.raises(PermissionDenied):
        gitea.list_issues("other/repo")
    with override_settings(GITEA_TOKEN="token"), pytest.raises(PermissionDenied):
        gitea.create_issue("other/repo", "t", "b")
    assert calls == []


@override_settings(GITEA_ALLOWED_REPOS=["blt/tasks", "Acme/Docs"])
def test_allowlist_accepts_listed_repos_case_insensitively(monkeypatch):
    monkeypatch.setattr(gitea, "_request", lambda *a, **k: [])
    assert gitea.list_issues("acme/docs") == []
    assert gitea.list_issues("blt/tasks") == []


def test_request_does_not_follow_redirects(monkeypatch):
    seen = {}

    def fake(*args, **kwargs):
        seen.update(kwargs)
        return FakeResponse(200, {})

    monkeypatch.setattr(gitea.httpx, "request", fake)
    gitea._request("GET", "/x")
    assert "follow_redirects" not in seen


@override_settings(GITEA_TOKEN="t", GITEA_ALLOWED_REPOS=["blt/tasks"])
def test_ensure_repo_refuses_repositories_outside_the_allowlist(monkeypatch):
    monkeypatch.setattr(gitea, "_request", lambda *a, **k: pytest.fail("must not call Gitea"))
    with pytest.raises(gitea.PermissionDenied):
        gitea.ensure_repo("someone/else")


@override_settings(GITEA_TOKEN="t", GITEA_ALLOWED_REPOS=["blt/tasks"])
def test_create_issue_sends_assignees(monkeypatch):
    sent = {}

    def fake(method, path, **kwargs):
        sent.update(kwargs["json"])
        return {"html_url": "http://localhost:3000/blt/tasks/issues/9", "number": 9}

    monkeypatch.setattr(gitea, "_request", fake)
    gitea.create_issue("blt/tasks", "Title", "Body", assignees=["lane"])
    assert sent["assignees"] == ["lane"]
    sent.clear()
    gitea.create_issue("blt/tasks", "Title", "Body")
    assert "assignees" not in sent


@override_settings(GITEA_TOKEN="t", GITEA_ALLOWED_REPOS=["blt/tasks"])
def test_ensure_collaborator_grants_write_and_respects_the_allowlist(monkeypatch):
    calls = []
    monkeypatch.setattr(gitea, "_request", lambda method, path, **k: calls.append((method, path)))
    gitea.ensure_collaborator("blt/tasks", "ballast")
    assert calls == [("PUT", "/repos/blt/tasks/collaborators/ballast")]
    with pytest.raises(PermissionDenied):
        gitea.ensure_collaborator("someone/else", "ballast")


def test_synced_issues_mirror_the_tasks_of_gitea_users():
    from specs.management.commands.gitea_bootstrap import synced_issues
    from tasks.seed_data import GITEA_USERS, TASKS

    issues = synced_issues()
    expected = [task for task in TASKS if task[5] in GITEA_USERS]
    assert [issue[0] for issue in issues] == [task[0] for task in expected]
    assert all(issue[2] == [task[5]] for issue, task in zip(issues, expected, strict=True))
