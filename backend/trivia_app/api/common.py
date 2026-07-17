from django.http import Http404, JsonResponse

from ..models import MasterCycle, Team, TeamMembership


def health_check(_request):
    return JsonResponse({'status': 'ok'})


def get_object_or_404(model, **kwargs):
    try:
        queryset = model if hasattr(model, 'get') else model.objects
        return queryset.get(**kwargs)
    except Exception as exc:
        raise Http404 from exc


def is_team_admin(user, team: Team) -> bool:
    return user.is_staff or TeamMembership.objects.filter(
        team=team,
        user=user,
        role=TeamMembership.Role.TEAM_ADMIN,
        status=TeamMembership.Status.APPROVED,
    ).exists()


def is_approved_member(user, team: Team) -> bool:
    return user.is_staff or TeamMembership.objects.filter(
        team=team,
        user=user,
        status=TeamMembership.Status.APPROVED,
    ).exists()


def can_manage_cycle(user, cycle: MasterCycle) -> bool:
    return user.is_staff or user == cycle.master
