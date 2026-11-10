import django_filters
from django.db.models import Q
from django.utils import timezone

from .models import Task


class TaskFilter(django_filters.FilterSet):
    status = django_filters.ChoiceFilter(choices=Task.Status.choices)
    due_date_after = django_filters.DateFilter(field_name="due_date", lookup_expr="gte")
    due_date_before = django_filters.DateFilter(field_name="due_date", lookup_expr="lte")
    assigned_to = django_filters.NumberFilter(field_name="assigned_to_id")
    overdue = django_filters.BooleanFilter(method="filter_overdue")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Task
        fields = ("status", "due_date_after", "due_date_before", "assigned_to", "overdue", "search")

    def filter_overdue(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(due_date__lt=timezone.localdate()).exclude(status=Task.Status.DONE)

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
