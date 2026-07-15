import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q
from django.http import Http404
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import EmailLoginCode, MasterCycle, Notification, Team, TeamMembership, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer
from .serializers import (
    MasterCycleSerializer,
    NotificationSerializer,
    PublicTriviaQuestionSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
    TrophyAwardSerializer,
    TriviaQuestionSerializer,
    TriviaSessionSerializer,
    UserAnswerSerializer,
    UserSerializer,
)
from .services.ai_generator import TriviaGenerator


def get_object_or_404(model, **kwargs):
    try:
        queryset = model if hasattr(model, 'get') else model.objects
        return queryset.get(**kwargs)
    except Exception as exc:
        raise Http404 from exc


def user_payload(user: User) -> dict:
    return UserSerializer(user).data


def is_team_admin(user: User, team: Team) -> bool:
    return user.is_staff or TeamMembership.objects.filter(
        team=team,
        user=user,
        role=TeamMembership.Role.TEAM_ADMIN,
        status=TeamMembership.Status.APPROVED,
    ).exists()


def is_approved_member(user: User, team: Team) -> bool:
    return user.is_staff or TeamMembership.objects.filter(
        team=team,
        user=user,
        status=TeamMembership.Status.APPROVED,
    ).exists()


def can_manage_cycle(user: User, cycle: MasterCycle) -> bool:
    return user.is_staff or user == cycle.master


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_request_code(request):
    email = request.data.get('email', '').strip().lower()
    username = request.data.get('username', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()
    if not email:
        return Response({'email': ['Email is required.']}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        if not username:
            return Response(
                {'username': ['Username is required for registration.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if User.objects.filter(username__iexact=username).exists():
            return Response({'username': ['This username is already in use.']}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_active=False,
        )
    elif username and user.username.lower() != username.lower():
        return Response({'email': ['An account already exists for this email.']}, status=status.HTTP_400_BAD_REQUEST)
    elif username and not user.is_active:
        # Registration may be retried before the code is verified. Preserve the
        # latest name values entered on the registration form.
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])

    code = f'{secrets.randbelow(1_000_000):06d}'
    EmailLoginCode.objects.filter(user=user, used_at__isnull=True).delete()
    EmailLoginCode.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=settings.LOGIN_CODE_EXPIRY_MINUTES),
    )
    send_mail(
        subject='Your Daily Trivia login code',
        message=f'Your Daily Trivia login code is {code}. It expires in {settings.LOGIN_CODE_EXPIRY_MINUTES} minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
    return Response({'detail': 'A login code has been sent.', 'email': email})


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_verify_code(request):
    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()
    user = User.objects.filter(email__iexact=email).first()
    login_code = EmailLoginCode.objects.filter(user=user, used_at__isnull=True).first() if user else None

    if not login_code or login_code.expires_at <= timezone.now() or not check_password(code, login_code.code_hash):
        return Response({'code': ['The login code is invalid or expired.']}, status=status.HTTP_400_BAD_REQUEST)

    login_code.used_at = timezone.now()
    login_code.save(update_fields=['used_at'])
    update_fields = []
    if not user.is_active:
        user.is_active = True
        update_fields.append('is_active')
    if user.email.lower() in settings.PLATFORM_ADMIN_EMAILS and not user.is_staff:
        user.is_staff = True
        user.is_superuser = True
        update_fields.extend(['is_staff', 'is_superuser'])
    if update_fields:
        user.save(update_fields=update_fields)

    Token.objects.filter(user=user).delete()
    token = Token.objects.create(user=user)
    return Response({'token': token.key, 'user': user_payload(user)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    return Response(user_payload(request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


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
            return Response(
                {'initial_admin_id': ['Select an active user as the initial team admin.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
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
            return Response(
                {'user_id': ['This user already belongs to the team.']},
                status=status.HTTP_409_CONFLICT,
            )
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
def user_list_create(request):
    users = User.objects.filter(is_active=True).order_by('username')
    return Response(UserSerializer(users, many=True).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, pk: int):
    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can remove users.'}, status=status.HTTP_403_FORBIDDEN)

    user = get_object_or_404(User, pk=pk)
    try:
        user.delete()
    except ProtectedError:
        return Response(
            {'detail': 'This user has protected master-cycle or trophy history and cannot be removed.'},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def master_cycle_list_create(request):
    if request.method == 'GET':
        cycles = MasterCycle.objects.select_related('master').prefetch_related('trivia_sessions__questions').order_by('-start_date')
        if not request.user.is_staff:
            team_ids = TeamMembership.objects.filter(
                user=request.user,
                status=TeamMembership.Status.APPROVED,
            ).values_list('team_id', flat=True)
            cycles = cycles.filter(team_id__in=team_ids)
        return Response(MasterCycleSerializer(cycles, many=True).data)

    serializer = MasterCycleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    team = serializer.validated_data['team']
    master = User.objects.filter(username=serializer.validated_data['master_username'], is_active=True).first()
    if not is_team_admin(request.user, team):
        return Response({'detail': 'Only a team admin can create cycles for this team.'}, status=status.HTTP_403_FORBIDDEN)
    if not master or not is_approved_member(master, team):
        return Response({'master_username': ['The master must be an approved team member.']}, status=status.HTTP_400_BAD_REQUEST)
    cycle = serializer.save()
    return Response(MasterCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_cycle_generate_trivia(request, pk: int):
    cycle = get_object_or_404(MasterCycle, pk=pk)
    if not can_manage_cycle(request.user, cycle):
        return Response({'detail': "Only this cycle's master can generate trivia."}, status=status.HTTP_403_FORBIDDEN)
    question_count = int(request.data.get('question_count', 5))
    title = request.data.get('title') or f'{cycle.topic} Trivia'

    generator = TriviaGenerator()
    try:
        generated_questions = generator.generate(cycle.topic, question_count=question_count)
    except Exception as exc:
        return Response({'detail': f'Trivia generation failed: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

    session = TriviaSession.objects.create(master_cycle=cycle, title=title, topic=cycle.topic)
    for order, question in enumerate(generated_questions, start=1):
        TriviaQuestion.objects.create(
            trivia_session=session,
            prompt=question.prompt,
            choices=question.choices,
            correct_choice=question.correct_choice,
            explanation=question.explanation,
            sort_order=order,
        )

    return Response(TriviaSessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_cycle_create_trivia(request, pk: int):
    cycle = get_object_or_404(MasterCycle, pk=pk)
    if not can_manage_cycle(request.user, cycle):
        return Response({'detail': "Only this cycle's master can create trivia."}, status=status.HTTP_403_FORBIDDEN)

    questions_data = request.data.get('questions', [])
    question_serializer = TriviaQuestionSerializer(data=questions_data, many=True)
    question_serializer.is_valid(raise_exception=True)
    if not questions_data:
        return Response({'questions': ['At least one question is required.']}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        session = TriviaSession.objects.create(
            master_cycle=cycle,
            title=request.data.get('title', '').strip() or f'{cycle.topic} Trivia',
            topic=cycle.topic,
        )
        for order, question in enumerate(question_serializer.validated_data, start=1):
            TriviaQuestion.objects.create(trivia_session=session, sort_order=order, **question)
    return Response(TriviaSessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def trivia_session_update(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if not can_manage_cycle(request.user, session.master_cycle):
        return Response({'detail': "Only this cycle's master can edit trivia."}, status=status.HTTP_403_FORBIDDEN)
    if session.status != TriviaSession.Status.DRAFT:
        return Response({'detail': 'Only draft trivia can be edited.'}, status=status.HTTP_409_CONFLICT)

    questions_data = request.data.get('questions', [])
    question_serializer = TriviaQuestionSerializer(data=questions_data, many=True)
    question_serializer.is_valid(raise_exception=True)
    if not questions_data:
        return Response({'questions': ['At least one question is required.']}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        session.title = request.data.get('title', session.title).strip() or session.title
        session.save(update_fields=['title'])
        session.questions.all().delete()
        for order, question in enumerate(question_serializer.validated_data, start=1):
            TriviaQuestion.objects.create(trivia_session=session, sort_order=order, **question)
    return Response(TriviaSessionSerializer(session).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def trivia_session_retrieve(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions'), pk=pk)
    if session.master_cycle.team and not is_approved_member(request.user, session.master_cycle.team):
        return Response({'detail': 'You are not an approved member of this team.'}, status=status.HTTP_403_FORBIDDEN)
    if can_manage_cycle(request.user, session.master_cycle):
        return Response(TriviaSessionSerializer(session).data)
    data = TriviaSessionSerializer(session).data
    data['questions'] = PublicTriviaQuestionSerializer(session.questions.all(), many=True).data
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_publish(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if not can_manage_cycle(request.user, session.master_cycle):
        return Response({'detail': "Only this cycle's master can publish trivia."}, status=status.HTTP_403_FORBIDDEN)
    session.status = TriviaSession.Status.LIVE
    session.publish_at = timezone.now()
    session.save(update_fields=['status', 'publish_at'])
    if session.master_cycle.team:
        member_ids = TeamMembership.objects.filter(
            team=session.master_cycle.team,
            status=TeamMembership.Status.APPROVED,
        ).exclude(user=request.user).values_list('user_id', flat=True)
        Notification.objects.bulk_create([
            Notification(
                user_id=user_id,
                team=session.master_cycle.team,
                message=f'New trivia is live: {session.title}',
            )
            for user_id in member_ids
        ])
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_answers(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if session.status != TriviaSession.Status.LIVE:
        return Response({'detail': 'Answers are only accepted for live trivia.'}, status=status.HTTP_409_CONFLICT)
    if session.master_cycle.team and not is_approved_member(request.user, session.master_cycle.team):
        return Response({'detail': 'You are not an approved member of this team.'}, status=status.HTTP_403_FORBIDDEN)
    serializer = UserAnswerSerializer(data={
        'trivia_session': session.id,
        'trivia_question': request.data.get('trivia_question'),
        'user': request.user.id,
        'selected_choice': request.data.get('selected_choice'),
    })
    serializer.is_valid(raise_exception=True)
    question = serializer.validated_data['trivia_question']
    if question.trivia_session_id != session.id:
        return Response({'trivia_question': ['This question does not belong to the trivia session.']}, status=status.HTTP_400_BAD_REQUEST)
    if serializer.validated_data['selected_choice'] not in question.choices:
        return Response({'selected_choice': ['Select one of the available choices.']}, status=status.HTTP_400_BAD_REQUEST)
    answer, _created = UserAnswer.objects.update_or_create(
        trivia_session=session,
        trivia_question_id=serializer.validated_data['trivia_question'].id,
        user_id=serializer.validated_data['user'].id,
        defaults={'selected_choice': serializer.validated_data['selected_choice']},
    )
    return Response(UserAnswerSerializer(answer).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_evaluate(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions', 'answers__user'), pk=pk)
    if not can_manage_cycle(request.user, session.master_cycle):
        return Response({'detail': "Only this cycle's master can evaluate trivia."}, status=status.HTTP_403_FORBIDDEN)
    correct_user_ids: list[int] = []

    with transaction.atomic():
        for answer in session.answers.select_related('user'):
            answer.is_correct = answer.selected_choice == answer.trivia_question.correct_choice
            answer.evaluated_at = timezone.now()
            answer.save(update_fields=['is_correct', 'evaluated_at'])
            if answer.is_correct:
                correct_user_ids.append(answer.user_id)
                TrophyAward.objects.get_or_create(
                    trivia_session=session,
                    user=answer.user,
                    defaults={'reason': 'Correct trivia answer'},
                )

    trophy_count = TrophyAward.objects.filter(trivia_session=session).count()
    session.status = TriviaSession.Status.CLOSED
    session.close_at = timezone.now()
    session.save(update_fields=['status', 'close_at'])
    return Response({'session_id': session.id, 'correct_users': correct_user_ids, 'trophies_awarded': trophy_count})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def leaderboard_view(request):
    team_id = request.query_params.get('team')
    if team_id:
        team = get_object_or_404(Team, pk=team_id)
        if not is_approved_member(request.user, team):
            return Response({'detail': 'You are not an approved member of this team.'}, status=status.HTTP_403_FORBIDDEN)
    leaderboard = (
        User.objects.annotate(
            trophy_count=Count(
                'trophy_awards',
                filter=Q(trophy_awards__trivia_session__master_cycle__team_id=team_id) if team_id else Q(),
            )
        )
        .filter(trophy_count__gt=0)
        .order_by('-trophy_count', 'username')
    )
    data = [
        {
            'user_id': user.id,
            'username': user.username,
            'trophy_count': user.trophy_count,
        }
        for user in leaderboard
    ]
    return Response(data)
