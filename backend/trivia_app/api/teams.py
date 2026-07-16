from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Notification, Team, TeamMembership, TrophyAward, TriviaSession, UserAnswer
from ..serializers import NotificationSerializer, TeamMembershipSerializer, TeamSerializer, UserSerializer
from .auth import user_payload
from .common import get_object_or_404, is_team_admin


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def team_list_create(request):
    if request.method == 'GET':
        teams = Team.objects.prefetch_related('memberships')
        if not request.user.is_staff:
            teams = teams.filter(memberships__user=request.user).distinct()
        return Response(TeamSerializer(teams.order_by('name'), many=True, context={'request': request}).data)

    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can create teams.'}, status=status.HTTP_403_FORBIDDEN)

    payload = request.data.copy()
    initial_admin_id = payload.pop('initial_admin_id', None)
    initial_admin = request.user
    if initial_admin_id:
        initial_admin = User.objects.filter(pk=initial_admin_id, is_active=True).first()
        if not initial_admin:
            return Response({'initial_admin_id': ['Select an active user as the initial team admin.']}, status=status.HTTP_400_BAD_REQUEST)
    payload['slug'] = payload.get('slug') or slugify(payload.get('name', ''))
    serializer = TeamSerializer(data=payload, context={'request': request})
    serializer.is_valid(raise_exception=True)
    with transaction.atomic():
        team = serializer.save(created_by=request.user)
        TeamMembership.objects.create(
            team=team,
            user=initial_admin,
            role=TeamMembership.Role.TEAM_ADMIN,
            status=TeamMembership.Status.APPROVED,
            approved_at=timezone.now(),
        )
    return Response(TeamSerializer(team, context={'request': request}).data, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def team_manage(request, pk: int):
    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can edit or remove teams.'}, status=status.HTTP_403_FORBIDDEN)
    team = get_object_or_404(Team, pk=pk)

    if request.method == 'DELETE':
        team.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    payload = {}
    if 'name' in request.data:
        name = str(request.data.get('name', '')).strip()
        if not name:
            return Response({'name': ['Team name cannot be blank.']}, status=status.HTTP_400_BAD_REQUEST)
        payload['name'] = name
        payload['slug'] = slugify(name)
    if 'approval_required' in request.data:
        payload['approval_required'] = request.data['approval_required']
    if not payload:
        return Response({'detail': 'Provide a team name or approval setting to update.'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = TeamSerializer(team, data=payload, partial=True, context={'request': request})
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def team_join(request):
    invite_code = request.data.get('invite_code', '').strip()
    team = get_object_or_404(Team, invite_code=invite_code)
    membership, created = TeamMembership.objects.get_or_create(
        team=team,
        user=request.user,
        defaults={
            'status': TeamMembership.Status.PENDING if team.approval_required else TeamMembership.Status.APPROVED,
            'approved_at': None if team.approval_required else timezone.now(),
        },
    )
    if not created and membership.status == TeamMembership.Status.REJECTED:
        membership.status = TeamMembership.Status.PENDING if team.approval_required else TeamMembership.Status.APPROVED
        membership.approved_at = None if team.approval_required else timezone.now()
        membership.save(update_fields=['status', 'approved_at'])
    return Response(TeamMembershipSerializer(membership).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def team_members(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    if not is_team_admin(request.user, team):
        return Response({'detail': 'Only a team admin can manage team membership.'}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'POST':
        user = User.objects.filter(pk=request.data.get('user_id'), is_active=True).first()
        if not user:
            return Response({'user_id': ['Select an active user.']}, status=status.HTTP_400_BAD_REQUEST)
        role = request.data.get('role', TeamMembership.Role.MEMBER)
        if role not in TeamMembership.Role.values:
            return Response({'role': ['Select member or team admin.']}, status=status.HTTP_400_BAD_REQUEST)
        if TeamMembership.objects.filter(team=team, user=user).exists():
            return Response({'user_id': ['This user already belongs to the team.']}, status=status.HTTP_409_CONFLICT)
        membership = TeamMembership.objects.create(
            team=team,
            user=user,
            role=role,
            status=TeamMembership.Status.APPROVED,
            approved_at=timezone.now(),
        )
        return Response(TeamMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)
    memberships = team.memberships.select_related('user').order_by('status', 'user__username')
    return Response(TeamMembershipSerializer(memberships, many=True).data)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def team_membership_manage(request, team_pk: int, membership_pk: int):
    team = get_object_or_404(Team, pk=team_pk)
    if not is_team_admin(request.user, team):
        return Response({'detail': 'Only a team admin can manage members.'}, status=status.HTTP_403_FORBIDDEN)
    membership = get_object_or_404(TeamMembership, pk=membership_pk, team=team)
    if request.method == 'DELETE':
        if membership.user == request.user:
            return Response({'detail': 'You cannot remove your own team-admin membership.'}, status=status.HTTP_400_BAD_REQUEST)
        membership.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    serializer = TeamMembershipSerializer(membership, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    update = serializer.validated_data
    if 'status' in update:
        membership.status = update['status']
        membership.approved_at = timezone.now() if membership.status == TeamMembership.Status.APPROVED else None
    if 'role' in update:
        membership.role = update['role']
    membership.save(update_fields=['status', 'approved_at', 'role'])
    return Response(TeamMembershipSerializer(membership).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def platform_admin_update(request, pk: int):
    if not request.user.is_superuser:
        return Response({'detail': 'Only a platform administrator can manage administrators.'}, status=status.HTTP_403_FORBIDDEN)
    user = get_object_or_404(User, pk=pk, is_active=True)
    is_admin = bool(request.data.get('is_admin'))
    if user == request.user and not is_admin:
        return Response({'detail': 'You cannot remove your own administrator access.'}, status=status.HTTP_400_BAD_REQUEST)
    user.is_staff = is_admin
    user.is_superuser = is_admin
    user.save(update_fields=['is_staff', 'is_superuser'])
    return Response(user_payload(user))


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def notification_list_update(request):
    notifications = Notification.objects.filter(user=request.user).select_related('team')
    if request.method == 'POST':
        notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
    return Response(NotificationSerializer(notifications[:50], many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_analytics(request, pk: int):
    team = get_object_or_404(Team, pk=pk)
    if not is_team_admin(request.user, team):
        return Response({'detail': 'Only a team admin can view analytics.'}, status=status.HTTP_403_FORBIDDEN)
    return Response({
        'team_id': team.id,
        'approved_members': team.memberships.filter(status=TeamMembership.Status.APPROVED).count(),
        'pending_members': team.memberships.filter(status=TeamMembership.Status.PENDING).count(),
        'trivia_sessions': TriviaSession.objects.filter(master_cycle__team=team).count(),
        'answers': UserAnswer.objects.filter(trivia_session__master_cycle__team=team).count(),
        'trophies': TrophyAward.objects.filter(trivia_session__master_cycle__team=team).count(),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def platform_overview(request):
    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can view the platform overview.'}, status=status.HTTP_403_FORBIDDEN)

    team_data = []
    teams = Team.objects.prefetch_related('memberships__user').order_by('name')
    for team in teams:
        session_data = []
        sessions = TriviaSession.objects.filter(master_cycle__team=team).select_related(
            'master_cycle__master',
        ).order_by('-publish_at', '-id')
        for session in sessions:
            submissions = session.answers.values('user_id', 'user__username').annotate(
                answers_submitted=Count('id'),
                submitted_at=Max('submitted_at'),
            ).order_by('user__username')
            session_data.append({
                'id': session.id,
                'title': session.title,
                'topic': session.topic,
                'status': session.status,
                'master': session.master_cycle.master.username,
                'publish_at': session.publish_at,
                'close_at': session.close_at,
                'submissions': [
                    {
                        'user_id': item['user_id'],
                        'username': item['user__username'],
                        'answers_submitted': item['answers_submitted'],
                        'submitted_at': item['submitted_at'],
                    }
                    for item in submissions
                ],
            })

        leaderboard = User.objects.filter(
            trophy_awards__trivia_session__master_cycle__team=team,
        ).annotate(
            trophy_count=Count(
                'trophy_awards',
                filter=Q(trophy_awards__trivia_session__master_cycle__team=team),
            ),
        ).order_by('-trophy_count', 'username')
        members = team.memberships.select_related('user').order_by('status', 'user__username')
        team_data.append({
            'id': team.id,
            'name': team.name,
            'approval_required': team.approval_required,
            'members': TeamMembershipSerializer(members, many=True).data,
            'trivia_sessions': session_data,
            'leaderboard': [
                {'user_id': user.id, 'username': user.username, 'trophy_count': user.trophy_count}
                for user in leaderboard
            ],
        })

    return Response({
        'team_count': len(team_data),
        'user_count': User.objects.filter(is_active=True).count(),
        'trivia_count': TriviaSession.objects.count(),
        'answer_count': UserAnswer.objects.count(),
        'teams': team_data,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_create(request):
    return Response(UserSerializer(User.objects.filter(is_active=True).order_by('username'), many=True).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, pk: int):
    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can remove users.'}, status=status.HTTP_403_FORBIDDEN)
    user = get_object_or_404(User, pk=pk)
    try:
        user.delete()
    except ProtectedError:
        return Response({'detail': 'This user has protected master-cycle or trophy history and cannot be removed.'}, status=status.HTTP_409_CONFLICT)
    return Response(status=status.HTTP_204_NO_CONTENT)
