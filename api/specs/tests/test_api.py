import pytest
from django.test import override_settings

from specs.models import Spec

ISSUE = {
    "url": "http://localhost:3000/blt/tasks/issues/1",
    "repo": "blt/tasks",
    "number": 1,
    "title": "Add attachments",
    "body": "Users need to attach files.",
    "state": "open",
}

PAYLOAD = {
    "summary": "Allow files on tasks.",
    "acceptance_criteria": ["A task accepts a PDF."],
    "implementation_steps": ["Add an Attachment model."],
    "risks": ["Storage cost."],
    "out_of_scope": ["Virus scanning."],
    "size": "M",
}


def make_spec(user, **overrides) -> Spec:
    data = {
        "issue_url": ISSUE["url"],
        "repo": ISSUE["repo"],
        "issue_number": 1,
        "issue_title": "Add attachments",
        "summary": "Allow files on tasks.",
        "acceptance_criteria": ["a"],
        "implementation_steps": ["b"],
        "risks": ["c"],
        "out_of_scope": ["d"],
        "size": Spec.Size.MEDIUM,
        "body_markdown": "## Summary\n\nAllow files.",
        "model": "test-model",
        "prompt_version": "spec-v1",
        "latency_ms": 1200,
        "input_chars": 200,
        "created_by": user,
    }
    data.update(overrides)
    return Spec.objects.create(**data)


@pytest.mark.django_db
def test_config_reports_feature_flags(auth):
    response = auth.get("/api/v1/specs/config/")
    assert response.status_code == 200
    assert set(response.data) == {"ai_enabled", "publish_enabled"}


@override_settings(AI_ENABLED=True)
@pytest.mark.django_db
def test_create_rejects_invalid_url(auth):
    response = auth.post(
        "/api/v1/specs/", {"issue_url": "https://example.com/not-an-issue"}, format="json"
    )
    assert response.status_code == 400
    assert "issue_url" in response.data


@override_settings(AI_ENABLED=False)
@pytest.mark.django_db
def test_create_is_503_when_ai_is_disabled(auth):
    response = auth.post("/api/v1/specs/", {"issue_url": ISSUE["url"]}, format="json")
    assert response.status_code == 503


@override_settings(AI_ENABLED=True)
@pytest.mark.django_db
def test_create_persists_spec(auth, user, monkeypatch):
    from specs import gitea, services

    monkeypatch.setattr(gitea, "fetch_issue", lambda *args: ISSUE)
    monkeypatch.setattr(
        services.generator, "generate_payload", lambda issue: (PAYLOAD, 800, False, 120)
    )
    response = auth.post("/api/v1/specs/", {"issue_url": ISSUE["url"]}, format="json")
    assert response.status_code == 201
    spec = Spec.objects.get(pk=response.data["id"])
    assert spec.created_by == user
    assert spec.size == "M"
    assert "## Acceptance criteria" in spec.body_markdown
    assert response.data["published"] is False


@override_settings(AI_ENABLED=True)
@pytest.mark.django_db
def test_create_maps_tracker_error(auth, monkeypatch):
    from specs import gitea

    def missing(*args):
        raise gitea.IssueNotFound()

    monkeypatch.setattr(gitea, "fetch_issue", missing)
    response = auth.post("/api/v1/specs/", {"issue_url": ISSUE["url"]}, format="json")
    assert response.status_code == 404


@pytest.mark.django_db
def test_list_is_scoped_to_the_user(auth, user, other_user):
    mine = make_spec(user)
    make_spec(other_user)
    response = auth.get("/api/v1/specs/")
    assert [item["id"] for item in response.data["results"]] == [mine.id]


@pytest.mark.django_db
def test_detail_hides_other_users_spec(auth, other_user):
    foreign = make_spec(other_user)
    assert auth.get(f"/api/v1/specs/{foreign.id}/").status_code == 404


@pytest.mark.django_db
def test_publish_sets_issue_link(auth, user, monkeypatch):
    from specs import gitea

    spec = make_spec(user)
    monkeypatch.setattr(
        gitea,
        "create_issue",
        lambda repo, title, body: {
            "url": "http://localhost:3000/blt/tasks/issues/9",
            "number": 9,
        },
    )
    response = auth.post(f"/api/v1/specs/{spec.id}/publish/")
    assert response.status_code == 200
    assert response.data["published"] is True
    assert response.data["published_issue_number"] == 9
    spec.refresh_from_db()
    assert spec.published_issue_url.endswith("/issues/9")


@pytest.mark.django_db
def test_publish_twice_is_conflict(auth, user):
    spec = make_spec(user, published_issue_url="http://localhost:3000/blt/tasks/issues/9")
    response = auth.post(f"/api/v1/specs/{spec.id}/publish/")
    assert response.status_code == 409


@override_settings(GITEA_TOKEN="", GITEA_USER="", GITEA_PASSWORD="")
@pytest.mark.django_db
def test_publish_without_token_is_503(auth, user):
    spec = make_spec(user)
    assert auth.post(f"/api/v1/specs/{spec.id}/publish/").status_code == 503


@pytest.mark.django_db
def test_publish_other_users_spec_is_404(auth, other_user):
    foreign = make_spec(other_user)
    assert auth.post(f"/api/v1/specs/{foreign.id}/publish/").status_code == 404


@pytest.mark.django_db
def test_publish_releases_claim_when_gitea_fails(auth, user, monkeypatch):
    from specs import gitea

    def refuse(*args):
        raise gitea.TrackerUnavailable()

    spec = make_spec(user)
    monkeypatch.setattr(gitea, "create_issue", refuse)
    assert auth.post(f"/api/v1/specs/{spec.id}/publish/").status_code == 502
    spec.refresh_from_db()
    assert spec.published_issue_url == ""


@pytest.mark.django_db
def test_publish_is_refused_while_another_call_holds_the_claim(auth, user, monkeypatch):
    from specs import gitea, services

    calls = []
    monkeypatch.setattr(gitea, "create_issue", lambda *args: calls.append(args))
    spec = make_spec(user, published_issue_url=services.PUBLISH_CLAIM)
    assert auth.post(f"/api/v1/specs/{spec.id}/publish/").status_code == 409
    assert calls == []


@pytest.mark.django_db
def test_listing_specs_is_not_throttled(auth):
    assert all(auth.get("/api/v1/specs/").status_code == 200 for _ in range(12))


@override_settings(AI_ENABLED=True)
@pytest.mark.django_db
def test_generation_is_throttled_after_ten_posts(auth, monkeypatch):
    from specs import gitea, services

    monkeypatch.setattr(gitea, "fetch_issue", lambda *args: ISSUE)
    monkeypatch.setattr(
        services.generator, "generate_payload", lambda issue: (PAYLOAD, 800, False, 120)
    )
    statuses = [
        auth.post("/api/v1/specs/", {"issue_url": ISSUE["url"]}, format="json").status_code
        for _ in range(11)
    ]
    assert statuses == [201] * 10 + [429]


@pytest.mark.django_db
def test_publish_has_its_own_throttle_scope(auth, user, monkeypatch):
    from rest_framework.throttling import ScopedRateThrottle

    from specs import gitea

    monkeypatch.setitem(ScopedRateThrottle.THROTTLE_RATES, "spec_publish", "2/hour")
    monkeypatch.setattr(
        gitea, "create_issue", lambda *args: {"url": "http://h/o/r/issues/1", "number": 1}
    )
    statuses = [
        auth.post(f"/api/v1/specs/{make_spec(user).id}/publish/").status_code for _ in range(3)
    ]
    assert statuses == [200, 200, 429]
    assert auth.get("/api/v1/specs/").status_code == 200


@override_settings(AI_ENABLED=True)
@pytest.mark.django_db
def test_create_rejects_repo_outside_allowlist(auth):
    response = auth.post(
        "/api/v1/specs/",
        {"issue_url": "http://localhost:3000/other/secret/issues/1"},
        format="json",
    )
    assert response.status_code == 400
    assert str(response.data["issue_url"]) == "That repository is not enabled for specs."


@override_settings(AI_ENABLED=False)
@pytest.mark.django_db
def test_error_texts_have_no_setup_hints(auth):
    detail = auth.post("/api/v1/specs/", {"issue_url": ISSUE["url"]}, format="json").data["detail"]
    assert detail == "AI generation is not available right now."


@override_settings(GITEA_TOKEN="", GITEA_USER="", GITEA_PASSWORD="")
@pytest.mark.django_db
def test_publish_error_text_is_product_language(auth, user):
    spec = make_spec(user)
    detail = auth.post(f"/api/v1/specs/{spec.id}/publish/").data["detail"]
    assert detail == "Publishing issues is not available right now."
