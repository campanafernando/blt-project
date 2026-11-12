from datetime import timedelta

import pytest
from django.utils import timezone

from tasks.models import Task


@pytest.mark.django_db
def test_list_requires_authentication(api):
    response = api.get("/api/v1/tasks/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_task(auth, user):
    response = auth.post(
        "/api/v1/tasks/",
        {"title": "New task", "description": "Details"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["title"] == "New task"
    assert response.data["created_by"]["username"] == user.username
    assert response.data["status"] == Task.Status.TODO
    assert response.data["is_overdue"] is False


@pytest.mark.django_db
def test_create_rejects_blank_title(auth):
    response = auth.post("/api/v1/tasks/", {"title": "   "}, format="json")
    assert response.status_code == 400
    assert "title" in response.data


@pytest.mark.django_db
def test_create_rejects_title_over_200_characters(auth):
    response = auth.post("/api/v1/tasks/", {"title": "x" * 201}, format="json")
    assert response.status_code == 400
    assert "title" in response.data
    assert not Task.objects.exists()


@pytest.mark.django_db
def test_update_rejects_title_over_200_characters(auth, task):
    response = auth.patch(f"/api/v1/tasks/{task.id}/", {"title": "x" * 201}, format="json")
    assert response.status_code == 400
    assert "title" in response.data
    task.refresh_from_db()
    assert task.title == "Test task"


@pytest.mark.django_db
def test_list_returns_pagination_metadata(auth, user):
    for index in range(12):
        Task.objects.create(title=f"Task {index}", created_by=user)
    response = auth.get("/api/v1/tasks/")
    assert response.status_code == 200
    assert response.data["count"] == 12
    assert len(response.data["results"]) == 10
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_page_size_is_capped(auth, user):
    for index in range(12):
        Task.objects.create(title=f"Task {index}", created_by=user)
    response = auth.get("/api/v1/tasks/?page_size=500")
    assert len(response.data["results"]) == 12


@pytest.mark.django_db
def test_summary_counts_only_visible_tasks(auth, user, other_user):
    today = timezone.localdate()
    Task.objects.create(title="To do", created_by=user)
    Task.objects.create(
        title="Finished", status=Task.Status.DONE, completed_at=timezone.now(), created_by=user
    )
    Task.objects.create(title="Overdue", due_date=today - timedelta(days=1), created_by=user)
    Task.objects.create(title="Someone else", created_by=other_user)
    response = auth.get("/api/v1/tasks/summary/")
    assert response.status_code == 200
    assert response.data == {
        "total": 3,
        "todo": 2,
        "in_progress": 0,
        "done": 1,
        "overdue": 1,
    }


@pytest.mark.django_db
def test_list_is_scoped_to_creator_or_assignee(auth, user, other_user):
    mine = Task.objects.create(title="Mine", created_by=user)
    assigned = Task.objects.create(title="Assigned", created_by=other_user, assigned_to=user)
    Task.objects.create(title="Someone else", created_by=other_user)
    ids = {item["id"] for item in auth.get("/api/v1/tasks/").data["results"]}
    assert ids == {mine.id, assigned.id}


@pytest.mark.django_db
def test_stranger_gets_404(auth, other_user):
    foreign = Task.objects.create(title="Private", created_by=other_user)
    response = auth.get(f"/api/v1/tasks/{foreign.id}/")
    assert response.status_code == 404


@pytest.mark.django_db
def test_update_title(auth, task):
    response = auth.patch(f"/api/v1/tasks/{task.id}/", {"title": "Updated"}, format="json")
    assert response.status_code == 200
    task.refresh_from_db()
    assert task.title == "Updated"


@pytest.mark.django_db
def test_patch_done_sets_completed_at(auth, task):
    response = auth.patch(f"/api/v1/tasks/{task.id}/", {"status": Task.Status.DONE}, format="json")
    assert response.status_code == 200
    assert response.data["completed_at"] is not None


@pytest.mark.django_db
def test_complete_endpoint(auth, task):
    response = auth.post(f"/api/v1/tasks/{task.id}/complete/")
    assert response.status_code == 200
    assert response.data["status"] == Task.Status.DONE
    second = auth.post(f"/api/v1/tasks/{task.id}/complete/")
    assert second.data["completed_at"] == response.data["completed_at"]


@pytest.mark.django_db
def test_reopen_endpoint(auth, user):
    done = Task.objects.create(
        title="Finished", status=Task.Status.DONE, created_by=user, completed_at=timezone.now()
    )
    response = auth.post(f"/api/v1/tasks/{done.id}/reopen/")
    assert response.status_code == 200
    assert response.data["status"] == Task.Status.TODO
    assert response.data["completed_at"] is None


@pytest.mark.django_db
def test_assign_endpoint(auth, task, other_user):
    response = auth.post(f"/api/v1/tasks/{task.id}/assign/", {"user": other_user.id}, format="json")
    assert response.status_code == 200
    assert response.data["assigned_to"]["username"] == other_user.username


@pytest.mark.django_db
def test_assign_inactive_user_returns_400(auth, task, other_user):
    other_user.is_active = False
    other_user.save()
    response = auth.post(f"/api/v1/tasks/{task.id}/assign/", {"user": other_user.id}, format="json")
    assert response.status_code == 400


@pytest.mark.django_db
def test_filter_by_status(auth, user):
    Task.objects.create(title="To do", status=Task.Status.TODO, created_by=user)
    Task.objects.create(
        title="Finished", status=Task.Status.DONE, completed_at=timezone.now(), created_by=user
    )
    response = auth.get("/api/v1/tasks/?status=done")
    assert [item["title"] for item in response.data["results"]] == ["Finished"]


@pytest.mark.django_db
def test_filter_by_due_date_range(auth, user):
    today = timezone.localdate()
    Task.objects.create(title="Yesterday", due_date=today - timedelta(days=1), created_by=user)
    Task.objects.create(title="Today", due_date=today, created_by=user)
    Task.objects.create(title="Tomorrow", due_date=today + timedelta(days=1), created_by=user)
    response = auth.get(f"/api/v1/tasks/?due_date_after={today}&due_date_before={today}")
    assert [item["title"] for item in response.data["results"]] == ["Today"]


@pytest.mark.django_db
def test_filter_overdue(auth, user):
    today = timezone.localdate()
    Task.objects.create(title="Overdue", due_date=today - timedelta(days=2), created_by=user)
    Task.objects.create(title="On time", due_date=today, created_by=user)
    response = auth.get("/api/v1/tasks/?overdue=true")
    assert [item["title"] for item in response.data["results"]] == ["Overdue"]


@pytest.mark.django_db
def test_search_matches_title_and_description(auth, user):
    Task.objects.create(title="Contract", created_by=user)
    Task.objects.create(title="Other", description="review annual contract", created_by=user)
    response = auth.get("/api/v1/tasks/?search=contract")
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_creator_can_delete(auth, task):
    response = auth.delete(f"/api/v1/tasks/{task.id}/")
    assert response.status_code == 204
    assert not Task.objects.filter(pk=task.id).exists()


@pytest.mark.django_db
def test_assignee_cannot_delete(auth, user, other_user):
    task = Task.objects.create(title="Someone else", created_by=other_user, assigned_to=user)
    response = auth.delete(f"/api/v1/tasks/{task.id}/")
    assert response.status_code == 403
    assert Task.objects.filter(pk=task.id).exists()
