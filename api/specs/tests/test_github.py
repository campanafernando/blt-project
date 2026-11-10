import httpx
import pytest
from django.test import override_settings
from rest_framework.exceptions import ValidationError

from specs import github


class FakeResponse:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def json(self):
        return self._data


def test_parse_accepts_common_issue_urls():
    expected = ("campanafernando", "blt-project", 12)
    for url in (
        "https://github.com/campanafernando/blt-project/issues/12",
        "http://github.com/campanafernando/blt-project/issues/12",
        "https://www.github.com/campanafernando/blt-project/issues/12/",
        "https://github.com/campanafernando/blt-project/issues/12#issuecomment-1",
    ):
        assert github.parse_issue_url(url) == expected


@pytest.mark.parametrize(
    "url",
    (
        "",
        "https://github.com/campanafernando/blt-project",
        "https://gitlab.com/a/b/issues/1",
        "https://github.com/a/b/pull/1",
        "not a url",
    ),
)
def test_parse_rejects_other_urls(url):
    with pytest.raises(ValidationError):
        github.parse_issue_url(url)


def test_fetch_issue_maps_fields(monkeypatch):
    monkeypatch.setattr(
        github,
        "_request",
        lambda *args, **kwargs: {
            "html_url": "https://github.com/o/r/issues/1",
            "title": "Add attachments",
            "body": "files please",
            "state": "open",
        },
    )
    issue = github.fetch_issue("o", "r", 1)
    assert issue == {
        "url": "https://github.com/o/r/issues/1",
        "title": "Add attachments",
        "body": "files please",
        "repo": "o/r",
        "number": 1,
        "state": "open",
    }


def test_fetch_issue_rejects_pull_requests(monkeypatch):
    monkeypatch.setattr(
        github,
        "_request",
        lambda *args, **kwargs: {"html_url": "x", "title": "t", "body": "", "pull_request": {}},
    )
    with pytest.raises(ValidationError):
        github.fetch_issue("o", "r", 1)


def test_request_maps_404(monkeypatch):
    monkeypatch.setattr(github.httpx, "request", lambda *a, **k: FakeResponse(404))
    with pytest.raises(github.IssueNotFound):
        github.fetch_issue("o", "r", 1)


def test_request_maps_rate_limit(monkeypatch):
    monkeypatch.setattr(github.httpx, "request", lambda *a, **k: FakeResponse(403))
    with pytest.raises(github.GitHubUnavailable):
        github.fetch_issue("o", "r", 1)


def test_request_maps_network_error(monkeypatch):
    def boom(*args, **kwargs):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(github.httpx, "request", boom)
    with pytest.raises(github.GitHubUnavailable):
        github.fetch_issue("o", "r", 1)


@override_settings(GITHUB_TOKEN="")
def test_create_issue_requires_token():
    with pytest.raises(github.PublishUnavailable):
        github.create_issue("o/r", "title", "body")


@override_settings(GITHUB_TOKEN="token")
def test_create_issue_returns_url_and_number(monkeypatch):
    monkeypatch.setattr(
        github,
        "_request",
        lambda *args, **kwargs: {
            "html_url": "https://github.com/o/r/issues/9",
            "number": 9,
        },
    )
    assert github.create_issue("o/r", "Spec: x", "body") == {
        "url": "https://github.com/o/r/issues/9",
        "number": 9,
    }
