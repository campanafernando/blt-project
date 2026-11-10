from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from tasks import selectors
from tasks.filters import TaskFilter
from tasks.models import Task
from tasks.serializers import TaskCreateSerializer
from tasks.services import complete_task, reopen_task

PAGE_SIZE = 20


def _counts(user) -> dict:
    rows = selectors.tasks_for(user).values("status").annotate(total=Count("id"))
    counts = {row["status"]: row["total"] for row in rows}
    return {
        "total": sum(counts.values()),
        "todo": counts.get(Task.Status.TODO, 0),
        "in_progress": counts.get(Task.Status.IN_PROGRESS, 0),
        "done": counts.get(Task.Status.DONE, 0),
    }


def _context(request) -> dict:
    filtered = TaskFilter(request.GET, queryset=selectors.tasks_for(request.user))
    page = Paginator(filtered.qs, PAGE_SIZE).get_page(request.GET.get("page"))
    return {
        "tasks": page.object_list,
        "page_obj": page,
        "counts": _counts(request.user),
    }


@login_required
def board(request):
    return render(request, "hypermedia/board.html", _context(request))


@login_required
def rows(request):
    return render(request, "hypermedia/_rows.html", _context(request))


@login_required
@require_POST
def create(request):
    serializer = TaskCreateSerializer(data=request.POST, context={"request": request})
    if not serializer.is_valid():
        return render(request, "hypermedia/_form.html", {"errors": serializer.errors}, status=422)
    serializer.save()
    response = render(request, "hypermedia/_created.html", _context(request))
    response["HX-Trigger"] = "task-created"
    return response


@login_required
@require_POST
def complete(request, task_id: int):
    task = selectors.get_task(request.user, task_id)
    if task is None:
        raise Http404
    complete_task(task)
    task.refresh_from_db()
    return render(request, "hypermedia/_row.html", {"task": task})


@login_required
@require_POST
def reopen(request, task_id: int):
    task = selectors.get_task(request.user, task_id)
    if task is None:
        raise Http404
    reopen_task(task)
    task.refresh_from_db()
    return render(request, "hypermedia/_row.html", {"task": task})


@login_required
@require_http_methods(["DELETE"])
def delete(request, task_id: int):
    task = selectors.get_task(request.user, task_id)
    if task is None:
        raise Http404
    if task.created_by_id != request.user.id:
        return HttpResponse("Apenas quem criou a tarefa pode excluí-la.", status=403)
    task.delete()
    return HttpResponse(status=200)
