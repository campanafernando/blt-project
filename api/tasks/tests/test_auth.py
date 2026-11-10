import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_token_obtain(api, user):
    response = api.post(
        "/api/v1/auth/token/",
        {"username": "demo", "password": "demo12345"},
        format="json",
    )
    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_token_rejects_wrong_password(api, user):
    response = api.post(
        "/api/v1/auth/token/",
        {"username": "demo", "password": "wrong"},
        format="json",
    )
    assert response.status_code == 401


@pytest.mark.django_db
def test_me_returns_current_user(auth, user):
    response = auth.get("/api/v1/auth/me/")
    assert response.status_code == 200
    assert response.data["username"] == user.username
    assert response.data["email"] == "demo@blt.local"


@pytest.mark.django_db
def test_users_list_excludes_inactive(auth, user, other_user):
    other_user.is_active = False
    other_user.save()
    response = auth.get("/api/v1/auth/users/")
    usernames = [item["username"] for item in response.data]
    assert usernames == ["demo"]


@pytest.mark.django_db
def test_refresh_returns_new_access(api, user):
    tokens = api.post(
        "/api/v1/auth/token/",
        {"username": "demo", "password": "demo12345"},
        format="json",
    ).data
    response = api.post("/api/v1/auth/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert response.status_code == 200
    assert "access" in response.data
