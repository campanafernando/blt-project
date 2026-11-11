import re
from datetime import UTC, date, datetime, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from hypermedia.templatetags.tasks_ui import due_caption, initials, short_name
from tasks.models import Task

User = get_user_model()
TODAY = date(2026, 11, 11)


@pytest.fixture
def web(user):
    client = Client()
    client.force_login(user)
    return client


def _tbody_rows(body: str) -> list[str]:
    return re.findall(r"<tr id=\"task-\d+\".*?</tr>", body, flags=re.S)


def _cells(row: str) -> list[str]:
    return re.findall(r"<td\b.*?</td>", row, flags=re.S)


def _cell(row: str, css_class: str) -> str:
    return next(c for c in _cells(row) if f'class="{css_class}"' in c)


@pytest.fixture
def mixed_tasks(user, other_user):
    third = User.objects.create_user(username="lane", first_name="Lane", password="x")
    with freeze_time("2026-11-11 12:00"):
        return {
            "overdue": Task.objects.create(
                title="Late one",
                description="d" * 300,
                due_date=TODAY - timedelta(days=3),
                created_by=user,
                assigned_to=user,
            ),
            "bare": Task.objects.create(title="Bare task", created_by=user),
            "foreign": Task.objects.create(
                title="From elsewhere", created_by=third, assigned_to=user, due_date=TODAY
            ),
            "done": Task.objects.create(
                title="Finished",
                status=Task.Status.DONE,
                completed_at=datetime(2026, 11, 7, 10, tzinfo=UTC),
                created_by=user,
                assigned_to=other_user,
                due_date=TODAY - timedelta(days=9),
            ),
        }


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_colgroup_is_rendered_once_with_six_columns(web, mixed_tasks):
    body = web.get(reverse("hypermedia:board")).content.decode()
    assert body.count("<colgroup>") == 1
    assert len(re.findall(r"<col\b", body)) == 6


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_every_row_has_the_same_number_of_cells(web, mixed_tasks):
    body = web.get(reverse("hypermedia:board")).content.decode()
    rows = _tbody_rows(body)
    assert len(rows) == len(mixed_tasks)
    assert {len(_cells(row)) for row in rows} == {6}
    header = re.search(r"<thead>.*?</thead>", body, flags=re.S).group(0)
    assert len(re.findall(r"<th[ >]", header)) == 6


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_overdue_is_told_in_the_due_cell_not_the_status_cell(web, mixed_tasks):
    row = next(
        r
        for r in _tbody_rows(web.get(reverse("hypermedia:board")).content.decode())
        if "Late one" in r
    )
    assert "Overdue" not in _cell(row, "col-status")
    assert "caption-overdue" in _cell(row, "col-due")
    assert "3 days overdue" in _cell(row, "col-due")
    assert "is-overdue" in row


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_empty_values_have_explicit_labels(web, mixed_tasks):
    rows = _tbody_rows(web.get(reverse("hypermedia:board")).content.decode())
    bare = next(r for r in rows if "Bare task" in r)
    assert "No due date" in _cell(bare, "col-due")
    assert "Unassigned" in _cell(bare, "col-assignee")
    assert "—" not in bare


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_from_caption_only_when_created_by_someone_else(web, mixed_tasks):
    rows = {
        t: r
        for r in _tbody_rows(web.get(reverse("hypermedia:board")).content.decode())
        for t in mixed_tasks
        if mixed_tasks[t].title in r
    }
    assert "from Lane" in _cell(rows["foreign"], "col-assignee")
    assert "You" in _cell(rows["foreign"], "col-assignee")
    for mine in ("overdue", "bare", "done"):
        assert "from " not in _cell(rows[mine], "col-assignee")


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_delete_only_for_creator_but_actions_cell_for_everyone(web, mixed_tasks):
    rows = {
        t: r
        for r in _tbody_rows(web.get(reverse("hypermedia:board")).content.decode())
        for t in mixed_tasks
        if mixed_tasks[t].title in r
    }
    for name, row in rows.items():
        actions = _cell(row, "col-actions")
        assert ("Delete task" in actions) is (name != "foreign")
    assert 'title="Mark as done"' in rows["bare"]
    assert 'title="Reopen task"' in rows["done"]


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_title_and_description_carry_the_full_text_in_title(web, mixed_tasks):
    body = web.get(reverse("hypermedia:board")).content.decode()
    assert 'title="Late one"' in body
    assert f'title="{"d" * 300}"' in body


@freeze_time("2026-11-11 12:00")
@pytest.mark.django_db
def test_complete_response_is_a_full_aligned_row(web, user):
    task = Task.objects.create(title="Quick", created_by=user)
    row = web.post(reverse("hypermedia:complete", args=[task.id]), HTTP_HX_REQUEST="true")
    html = row.content.decode()
    assert len(_cells(html)) == 6
    assert "Completed 11 Nov" in html


def _task(**fields):
    return Task(title="t", **fields)


def test_caption_overdue_counts_days_and_pluralises():
    assert due_caption(_task(due_date=date(2026, 11, 8)), TODAY) == {
        "kind": "overdue",
        "text": "3 days overdue",
    }
    assert due_caption(_task(due_date=date(2026, 11, 10)), TODAY)["text"] == "1 day overdue"


def test_caption_today_tomorrow_and_far_future():
    assert due_caption(_task(due_date=TODAY), TODAY) == {"kind": "today", "text": "Due today"}
    assert due_caption(_task(due_date=date(2026, 11, 12)), TODAY) == {
        "kind": "tomorrow",
        "text": "Due tomorrow",
    }
    assert due_caption(_task(due_date=date(2026, 11, 20)), TODAY)["text"] == ""


def test_caption_done_uses_completion_date_even_when_overdue_by_date():
    task = _task(
        status="done",
        due_date=date(2026, 10, 1),
        completed_at=datetime(2026, 11, 7, 10, tzinfo=UTC),
    )
    assert due_caption(task, TODAY) == {"kind": "done", "text": "Completed 07 Nov"}


def test_caption_without_due_date():
    assert due_caption(_task(), TODAY) == {"kind": "none", "text": "No due date"}


@freeze_time("2026-11-11 12:00")
def test_caption_defaults_to_the_local_date_when_none_is_given():
    assert timezone.localdate() == TODAY
    assert due_caption(_task(due_date=TODAY))["kind"] == "today"


def test_initials_and_short_name():
    full = User(username="fcampana", first_name="Fernando", last_name="Campana")
    only_first = User(username="lane", first_name="Lane")
    bare = User(username="maria")
    assert initials(full) == "FC"
    assert initials(only_first) == "LA"
    assert initials(bare) == "MA"
    assert short_name(full) == "Fernando"
    assert short_name(bare) == "maria"
