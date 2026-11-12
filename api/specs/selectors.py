from .models import Spec


def spec_list(*, fetched_by):
    return Spec.objects.filter(created_by=fetched_by)


def spec_get(*, fetched_by, spec_id: int) -> Spec | None:
    return spec_list(fetched_by=fetched_by).filter(pk=spec_id).first()
