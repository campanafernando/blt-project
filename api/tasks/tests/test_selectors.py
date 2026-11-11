from datetime import timedelta

import pytest
from django.utils import timezone

from tasks import selectors
from tasks.models import Task


@pytest.mark.django_db
def test_task_list_is_scoped_to_creator_or_assignee(user, other_user):
    mine = Task.objects.create(title="Mine", created_by=user)
    assigned = Task.objects.create(title="Assigned", created_by=other_user, assigned_to=user)
    Task.objects.create(title="Someone else", created_by=other_user)
    assert set(selectors.task_list(fetched_by=user)) == {mine, assigned}


@pytest.mark.django_db
def test_task_list_applies_filters(user):
    today = timezone.localdate()
    Task.objects.create(title="Open contract", created_by=user)
    Task.objects.create(
        title="Done contract",
        status=Task.Status.DONE,
        completed_at=timezone.now(),
        created_by=user,
    )
    Task.objects.create(title="Late", due_date=today - timedelta(days=1), created_by=user)

    done = selectors.task_list(fetched_by=user, filters={"status": "done"})
    assert [task.title for task in done] == ["Done contract"]
    late = selectors.task_list(fetched_by=user, filters={"overdue": "true"})
    assert [task.title for task in late] == ["Late"]
    found = selectors.task_list(fetched_by=user, filters={"search": "contract"})
    assert found.count() == 2


@pytest.mark.django_db
def test_task_get_returns_none_when_not_visible(user, other_user):
    visible = Task.objects.create(title="Mine", created_by=user)
    hidden = Task.objects.create(title="Hidden", created_by=other_user)
    assert selectors.task_get(fetched_by=user, task_id=visible.pk) == visible
    assert selectors.task_get(fetched_by=user, task_id=hidden.pk) is None
    assert selectors.task_get(fetched_by=user, task_id=0) is None


@pytest.mark.django_db
def test_task_summary_counts_only_visible_tasks(user, other_user):
    today = timezone.localdate()
    Task.objects.create(title="Todo", created_by=user)
    Task.objects.create(title="Doing", status=Task.Status.IN_PROGRESS, created_by=user)
    Task.objects.create(
        title="Done",
        status=Task.Status.DONE,
        completed_at=timezone.now(),
        due_date=today - timedelta(days=5),
        created_by=user,
    )
    Task.objects.create(title="Late", due_date=today - timedelta(days=1), created_by=user)
    Task.objects.create(title="Hidden", created_by=other_user)
    assert selectors.task_summary(fetched_by=user) == {
        "total": 4,
        "todo": 2,
        "in_progress": 1,
        "done": 1,
        "overdue": 1,
    }


@pytest.mark.django_db
def test_assignee_list_is_active_users_ordered_by_username(user, other_user, django_user_model):
    django_user_model.objects.create_user(username="aaron", password="demo12345")
    django_user_model.objects.create_user(username="zoe", password="demo12345", is_active=False)
    usernames = [person.username for person in selectors.assignee_list()]
    assert usernames == ["aaron", "demo", "maria"]
