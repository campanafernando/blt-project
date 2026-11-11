import pytest
from django.test import Client
from django.urls import reverse

from tasks.models import Task


@pytest.fixture
def web(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_assignee_cannot_delete_via_htmx(web, user, other_user):
    task = Task.objects.create(title="Not mine", created_by=other_user, assigned_to=user)
    response = web.delete(reverse("hypermedia:delete", args=[task.id]), HTTP_HX_REQUEST="true")
    assert response.status_code == 403
    assert response.content.decode() == "Only the task creator can delete it."
    assert Task.objects.filter(pk=task.id).exists()


@pytest.mark.django_db
def test_creator_can_delete_via_htmx(web, task):
    response = web.delete(reverse("hypermedia:delete", args=[task.id]), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert not Task.objects.filter(pk=task.id).exists()
