import importlib.util
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from specs import services
from specs.tests.test_api import make_spec
from tasks.models import Task

User = get_user_model()
SOURCE = "Source: http://localhost:3000/blt/tasks/issues/1"


def url(spec) -> str:
    return f"/api/v1/specs/{spec.id}/tasks/"


@pytest.mark.django_db
def test_service_creates_tasks_with_source_line(user):
    spec = make_spec(user)
    tasks = services.spec_tasks_create(
        spec=spec,
        actor=user,
        tasks=[{"title": "One", "description": "  Details  "}, {"title": "Two"}],
    )
    assert [t.title for t in tasks] == ["One", "Two"]
    assert tasks[0].description == f"Details\n\n{SOURCE}"
    assert tasks[1].description == SOURCE
    assert all(t.created_by == user for t in tasks)


@pytest.mark.django_db
def test_service_does_not_duplicate_the_source_line(user):
    spec = make_spec(user)
    (task,) = services.spec_tasks_create(
        spec=spec, actor=user, tasks=[{"title": "One", "description": f"Text\n{SOURCE}\n"}]
    )
    assert task.description == f"Text\n{SOURCE}"


@pytest.mark.django_db
def test_service_is_all_or_nothing(user):
    spec = make_spec(user)
    with pytest.raises(ValidationError):
        services.spec_tasks_create(
            spec=spec, actor=user, tasks=[{"title": "Good"}, {"title": "x" * 201}]
        )
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_endpoint_creates_tasks(auth, user, other_user):
    spec = make_spec(user)
    response = auth.post(
        url(spec),
        {
            "tasks": [
                {"title": "One", "due_date": "2030-01-02", "assigned_to": other_user.id},
                {"title": "Two", "description": "More"},
            ]
        },
        format="json",
    )
    assert response.status_code == 201
    first, second = response.data["tasks"]
    assert first["title"] == "One"
    assert first["due_date"] == "2030-01-02"
    assert first["assigned_to"]["id"] == other_user.id
    assert first["status"] == "todo"
    assert second["description"] == f"More\n\n{SOURCE}"
    assert Task.objects.count() == 2


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tasks",
    [[], [{"title": f"t{i}"} for i in range(11)], [{"title": "  "}], [{"description": "x"}]],
    ids=["empty", "eleven", "blank-title", "missing-title"],
)
def test_endpoint_rejects_invalid_input(auth, user, tasks):
    spec = make_spec(user)
    response = auth.post(url(spec), {"tasks": tasks}, format="json")
    assert response.status_code == 400
    assert "tasks" in response.data
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_endpoint_rejects_inactive_assignee_and_creates_nothing(auth, user, other_user):
    spec = make_spec(user)
    other_user.is_active = False
    other_user.save()
    response = auth.post(
        url(spec),
        {"tasks": [{"title": "Ok"}, {"title": "Bad", "assigned_to": other_user.id}]},
        format="json",
    )
    assert response.status_code == 400
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_endpoint_hides_other_users_spec(auth, other_user):
    spec = make_spec(other_user)
    response = auth.post(url(spec), {"tasks": [{"title": "One"}]}, format="json")
    assert response.status_code == 404
    assert "detail" in response.data
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_endpoint_requires_authentication(api, user):
    spec = make_spec(user)
    assert api.post(url(spec), {"tasks": [{"title": "One"}]}, format="json").status_code == 401


@pytest.fixture
def mcp_server():
    pytest.importorskip("mcp")
    path = Path(__file__).resolve().parents[3] / "mcp_server" / "server.py"
    spec = importlib.util.spec_from_file_location("blt_mcp_server", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cli_spec(mcp_server):
    return make_spec(
        mcp_server._cli_user(), implementation_steps=["First step", "s" * 250, "Third step"]
    )


@pytest.mark.django_db
def test_mcp_draft_writes_nothing(mcp_server, cli_spec, user):
    result = mcp_server._create_tasks(cli_spec.id, user.username, False)
    assert result["confirmed"] is False
    assert [t["title"] for t in result["tasks"]] == ["First step", "s" * 200, "Third step"]
    assert result["tasks"][0]["description"] == ""
    assert result["tasks"][1]["description"] == "s" * 250
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_mcp_confirm_creates_tasks_for_the_assignee(mcp_server, cli_spec, user):
    result = mcp_server._create_tasks(cli_spec.id, user.username, True)
    assert result["confirmed"] is True
    assert len(result["tasks"]) == 3
    assert Task.objects.filter(assigned_to=user).count() == 3


@pytest.mark.django_db
def test_mcp_rejects_unknown_or_inactive_assignee(mcp_server, cli_spec, other_user):
    other_user.is_active = False
    other_user.save()
    for name in ("ghost", other_user.username):
        with pytest.raises(ValueError, match="No active user"):
            mcp_server._create_tasks(cli_spec.id, name, True)
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_mcp_unknown_spec(mcp_server, user):
    with pytest.raises(ValueError, match="not found"):
        mcp_server._create_tasks(999, user.username, False)
