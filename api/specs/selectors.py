from .models import Spec


def specs_for(user):
    return Spec.objects.filter(created_by=user)


def get_spec(user, spec_id: int) -> Spec | None:
    return specs_for(user).filter(pk=spec_id).first()
