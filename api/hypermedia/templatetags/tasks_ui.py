"""Presentation helpers for the task table. No business rules: the template still decides
who may delete; these only turn dates and names into display values."""

from datetime import date

from django import template
from django.utils import timezone
from django.utils.dateformat import format as date_format

register = template.Library()


@register.simple_tag
def due_caption(task, today: date | None = None) -> dict:
    """Caption under the due date: ``{"kind": ..., "text": ...}``.

    Kinds: ``overdue``, ``today``, ``tomorrow``, ``done``, ``none`` (no due date) and
    ``""`` with empty text when the date is further away and nothing needs saying.
    ``today`` is injectable so tests never read the clock.
    """
    if task.status == "done":
        if task.completed_at:
            done_on = timezone.localtime(task.completed_at)
            return {"kind": "done", "text": f"Completed {date_format(done_on, 'd M')}"}
        return {"kind": "", "text": ""}
    if not task.due_date:
        return {"kind": "none", "text": "No due date"}
    days = (task.due_date - (today or timezone.localdate())).days
    if days < 0:
        late = -days
        return {"kind": "overdue", "text": f"{late} day{'s' if late != 1 else ''} overdue"}
    if days == 0:
        return {"kind": "today", "text": "Due today"}
    if days == 1:
        return {"kind": "tomorrow", "text": "Due tomorrow"}
    return {"kind": "", "text": ""}


@register.filter
def short_name(person) -> str:
    """First name, falling back to the username."""
    return person.first_name or person.username


@register.filter
def full_name(person) -> str:
    return person.get_full_name() or person.username


@register.filter
def initials(person) -> str:
    """Two letters: first+last name initials, or the first two of the username."""
    first, last = person.first_name.strip(), person.last_name.strip()
    if first and last:
        return (first[0] + last[0]).upper()
    return (first or person.username)[:2].upper()
