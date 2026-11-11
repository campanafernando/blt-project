import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from config.celery import app as celery_app
from tasks.models import Task

User = get_user_model()


@pytest.fixture(autouse=True)
def _test_environment(settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    cache.clear()
    yield
    celery_app.conf.task_always_eager = False
    cache.clear()


@pytest.fixture
def api() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="demo", password="demo12345", email="demo@blt.local")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="maria", password="demo12345", email="maria@blt.local")


@pytest.fixture
def auth(api, user) -> APIClient:
    response = api.post(
        "/api/v1/auth/token/",
        {"username": "demo", "password": "demo12345"},
        format="json",
    )
    assert response.status_code == 200, response.content
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return api


@pytest.fixture
def task(user) -> Task:
    return Task.objects.create(title="Test task", created_by=user)
