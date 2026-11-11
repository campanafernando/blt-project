import pytest


@pytest.mark.django_db
def test_user_list_exposes_only_directory_fields(auth, user, other_user):
    response = auth.get("/api/v1/auth/users/")
    assert response.status_code == 200
    assert isinstance(response.data, list)
    assert [set(item) for item in response.data] == [
        {"id", "username", "first_name", "last_name"}
    ] * 2


@pytest.mark.django_db
def test_me_keeps_the_full_profile(auth):
    assert set(auth.get("/api/v1/auth/me/").data) == {
        "id",
        "username",
        "first_name",
        "last_name",
        "email",
        "is_active",
    }
