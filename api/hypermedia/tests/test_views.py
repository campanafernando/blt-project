from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task


@pytest.fixture
def web(user):
    client = Client()
    client.force_login(user)
    return client


@pytest.mark.django_db
def test_anonymous_is_redirected(client):
    response = client.get(reverse("hypermedia:board"))
    assert response.status_code == 302
    assert "/app/login/" in response["Location"]


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse("login"))
    assert response.status_code == 200
    body = response.content.decode()
    assert "Sign in" in body
    assert 'lang="en"' in body
    assert "fernando" not in body.lower()  # no credentials are hinted on the page


@pytest.mark.django_db
def test_board_lists_task(web, task):
    response = web.get(reverse("hypermedia:board"))
    assert response.status_code == 200
    assert task.title in response.content.decode()


@pytest.mark.django_db
def test_board_markup_has_no_pt_br_leftovers_or_duplicate_ids(web, user, other_user):
    body = web.get(reverse("hypermedia:board")).content.decode()
    assert body.count('id="task-form"') == 1
    assert 'lang="en"' in body
    assert "pt-BR" not in body
    assert "Resumo" not in body
    assert "fernando" not in body.lower()  # no credentials are hinted on the page
    assert f'<option value="{other_user.id}"' in body
    assert f'<option value="{user.id}"' in body
    assert "Unassigned" in body


@pytest.mark.django_db
def test_rows_filter_by_status(web, user):
    Task.objects.create(title="Pendente", status=Task.Status.TODO, created_by=user)
    Task.objects.create(
        title="Done", status=Task.Status.DONE, created_by=user, completed_at=timezone.now()
    )
    response = web.get(reverse("hypermedia:rows"), {"status": "done"})
    body = response.content.decode()
    assert "Done" in body
    assert "Pendente" not in body


@pytest.mark.django_db
def test_create_via_htmx_returns_oob_update(web, user):
    response = web.post(
        reverse("hypermedia:create"),
        {"title": "New via HTMX", "description": "created on the server"},
        HTTP_HX_REQUEST="true",
    )
    assert response.status_code == 200
    body = response.content.decode()
    assert "hx-swap-oob" in body
    assert response["HX-Trigger"] == "task-created"
    assert Task.objects.filter(title="New via HTMX", created_by=user).exists()


@pytest.mark.django_db
def test_create_invalid_returns_422(web):
    response = web.post(reverse("hypermedia:create"), {"title": "  "}, HTTP_HX_REQUEST="true")
    assert response.status_code == 422
    assert 'id="task-form"' in response.content.decode()


@pytest.mark.django_db
def test_complete_returns_updated_row(web, task):
    response = web.post(reverse("hypermedia:complete", args=[task.id]), HTTP_HX_REQUEST="true")
    task.refresh_from_db()
    assert response.status_code == 200
    assert task.status == Task.Status.DONE
    assert "Done" in response.content.decode()


@pytest.mark.django_db
def test_reopen_returns_updated_row(web, user):
    task = Task.objects.create(
        title="Feita", status=Task.Status.DONE, created_by=user, completed_at=timezone.now()
    )
    response = web.post(reverse("hypermedia:reopen", args=[task.id]), HTTP_HX_REQUEST="true")
    task.refresh_from_db()
    assert response.status_code == 200
    assert task.status == Task.Status.TODO


@pytest.mark.django_db
def test_creator_can_delete(web, task):
    response = web.delete(reverse("hypermedia:delete", args=[task.id]), HTTP_HX_REQUEST="true")
    assert response.status_code == 200
    assert not Task.objects.filter(pk=task.id).exists()


@pytest.mark.django_db
def test_foreign_task_is_not_found_on_delete(web, other_user):
    foreign = Task.objects.create(title="De outro", created_by=other_user)
    response = web.delete(reverse("hypermedia:delete", args=[foreign.id]))
    # 404 instead of 403: the board never reveals tasks from other users.
    assert response.status_code == 404
    assert Task.objects.filter(pk=foreign.id).exists()


@pytest.mark.django_db
def test_foreign_task_returns_404_on_complete(web, other_user):
    foreign = Task.objects.create(title="De outro", created_by=other_user)
    response = web.post(reverse("hypermedia:complete", args=[foreign.id]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_overdue_task_is_marked(web, user):
    task = Task.objects.create(
        title="Overdue",
        due_date=timezone.localdate() - timedelta(days=2),
        created_by=user,
    )
    response = web.get(reverse("hypermedia:board"))
    assert "Overdue" in response.content.decode()
    assert task.is_overdue is True


@pytest.mark.django_db
def test_pages_use_space_grotesk_and_not_poppins(client, web):
    for body in (
        client.get(reverse("login")).content.decode(),
        web.get(reverse("hypermedia:board")).content.decode(),
    ):
        assert "Space+Grotesk" in body
        assert "Poppins" not in body


@pytest.mark.django_db
def test_pages_declare_the_blt_favicon(web, client):
    for body in (
        web.get(reverse("hypermedia:board")).content.decode(),
        client.get(reverse("login")).content.decode(),
    ):
        assert 'rel="icon"' in body
        assert "hypermedia/favicon.svg" in body
        assert "hypermedia/apple-touch-icon.png" in body


def test_favicon_ico_redirects_to_the_static_file(client):
    from pathlib import Path

    response = client.get("/favicon.ico")
    assert response.status_code == 301
    assert response["Location"] == "/static/hypermedia/favicon.ico"
    static = Path(__file__).resolve().parents[1] / "static" / "hypermedia"
    assert all(
        (static / name).is_file() for name in ("favicon.svg", "favicon.ico", "apple-touch-icon.png")
    )
