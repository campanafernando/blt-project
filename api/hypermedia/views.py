from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods, require_POST

from core.pagination import PAGE_SIZE
from tasks import selectors, services


class TaskCreateForm(forms.Form):
    title = forms.CharField()
    description = forms.CharField(required=False)
    due_date = forms.DateField(required=False)
    assigned_to = forms.ModelChoiceField(queryset=selectors.assignee_list(), required=False)


def _context(request) -> dict:
    tasks = selectors.task_list(fetched_by=request.user, filters=request.GET)
    page = Paginator(tasks, PAGE_SIZE).get_page(request.GET.get("page"))
    return {
        "tasks": page.object_list,
        "page_obj": page,
        "counts": selectors.task_summary(fetched_by=request.user),
        "users": selectors.assignee_list(),
    }


def _task_get_or_404(request, task_id: int):
    task = selectors.task_get(fetched_by=request.user, task_id=task_id)
    if task is None:
        raise Http404
    return task


def _form_errors(request, errors: dict) -> HttpResponse:
    context = {"errors": errors, "users": selectors.assignee_list()}
    return render(request, "hypermedia/_form.html", context, status=422)


@login_required
def board(request):
    return render(request, "hypermedia/board.html", _context(request))


@login_required
def rows(request):
    return render(request, "hypermedia/_rows.html", _context(request))


@login_required
@require_POST
def create(request):
    form = TaskCreateForm(request.POST)
    if not form.is_valid():
        return _form_errors(request, {field: list(errors) for field, errors in form.errors.items()})
    try:
        services.task_create(actor=request.user, **form.cleaned_data)
    except ValidationError as exc:
        return _form_errors(request, exc.message_dict)
    response = render(request, "hypermedia/_created.html", _context(request))
    response["HX-Trigger"] = "task-created"
    return response


@login_required
@require_POST
def complete(request, task_id: int):
    task = services.task_complete(task=_task_get_or_404(request, task_id))
    return render(request, "hypermedia/_row.html", {"task": task})


@login_required
@require_POST
def reopen(request, task_id: int):
    task = services.task_reopen(task=_task_get_or_404(request, task_id))
    return render(request, "hypermedia/_row.html", {"task": task})


@login_required
@require_http_methods(["DELETE"])
def delete(request, task_id: int):
    task = _task_get_or_404(request, task_id)
    try:
        services.task_delete(task=task, actor=request.user)
    except PermissionDenied as exc:
        return HttpResponse(str(exc), status=403)
    return HttpResponse(status=200)
