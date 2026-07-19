from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import MasterCycle, Notification, Team, TeamMembership, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer
from ..serializers import (
    MasterCycleSerializer,
    PublicTriviaQuestionSerializer,
    TriviaQuestionSerializer,
    TriviaSessionSerializer,
    UserAnswerSerializer,
)
from ..services.ai_generator import TriviaGenerator
from ..services.cycle_finalizer import finalize_expired_cycles
from .common import can_manage_cycle, get_object_or_404, is_approved_member, is_team_admin


def notify_trivia_published(team: Team, session: TriviaSession, publisher: User) -> None:
    member_ids = set(TeamMembership.objects.filter(
        team=team,
        status=TeamMembership.Status.APPROVED,
    ).exclude(user=publisher).values_list('user_id', flat=True))
    admin_ids = set(User.objects.filter(is_staff=True, is_active=True).values_list('id', flat=True))
    recipient_ids = member_ids | admin_ids
    Notification.objects.bulk_create([
        Notification(user_id=user_id, team=team, message=f'New trivia is live: {session.title}')
        for user_id in recipient_ids
    ])


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def master_cycle_list_create(request):
    if request.method == 'GET':
        finalize_expired_cycles()
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
    if cycle.status != MasterCycle.Status.ACTIVE or not cycle.start_date <= timezone.localdate() <= cycle.end_date:
        return Response({'detail': 'Trivia can only be generated during an active cycle.'}, status=status.HTTP_409_CONFLICT)
    scheduled_date = request.data.get('scheduled_date') or timezone.localdate().isoformat()
    scheduled_topic = next(
        (item.get('topic') for item in cycle.daily_topics if item.get('date') == scheduled_date),
        None,
    )
    selected_topic = str(request.data.get('topic', '')).strip()
    trivia_topic = selected_topic or scheduled_topic or cycle.topic
    title = request.data.get('title') or f'{trivia_topic} Daily Challenge'
    try:
        question = TriviaGenerator().generate(trivia_topic)
    except Exception as exc:
        return Response({'detail': f'Trivia generation failed: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)

    publish_at = timezone.now()
    with transaction.atomic():
        session = TriviaSession.objects.create(
            master_cycle=cycle,
            title=title,
            topic=trivia_topic,
            status=TriviaSession.Status.LIVE,
            publish_at=publish_at,
            close_at=publish_at + timedelta(hours=settings.TRIVIA_ANSWER_WINDOW_HOURS),
        )
        TriviaQuestion.objects.create(
            trivia_session=session,
            prompt=question.prompt,
            choices=question.choices,
            correct_choice=question.correct_choice,
            explanation=question.explanation,
            sort_order=1,
        )
        if cycle.team:
            notify_trivia_published(cycle.team, session, request.user)
    return Response(TriviaSessionSerializer(session).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_cycle_create_trivia(request, pk: int):
    cycle = get_object_or_404(MasterCycle, pk=pk)
    if not can_manage_cycle(request.user, cycle):
        return Response({'detail': "Only this cycle's master can create trivia."}, status=status.HTTP_403_FORBIDDEN)
    if cycle.status != MasterCycle.Status.ACTIVE or not cycle.start_date <= timezone.localdate() <= cycle.end_date:
        return Response({'detail': 'Trivia can only be created during an active cycle.'}, status=status.HTTP_409_CONFLICT)
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

    answer_window_closed = bool(session.close_at and timezone.now() >= session.close_at)
    can_manage = can_manage_cycle(request.user, session.master_cycle)
    answers_by_question = {
        answer.trivia_question_id: answer
        for answer in UserAnswer.objects.filter(trivia_session=session, user=request.user)
    }
    if can_manage or answer_window_closed or session.status == TriviaSession.Status.CLOSED:
        data = TriviaSessionSerializer(session).data
        data['has_submitted'] = bool(answers_by_question)
        if can_manage:
            submissions = session.answers.values('user_id', 'user__username').annotate(
                answers_submitted=Count('id'),
                submitted_at=Max('submitted_at'),
            ).order_by('submitted_at')
            data['submissions'] = [
                {
                    'user_id': submission['user_id'],
                    'username': submission['user__username'],
                    'answers_submitted': submission['answers_submitted'],
                    'submitted_at': submission['submitted_at'],
                }
                for submission in submissions
            ]
            data['submission_count'] = len(data['submissions'])
        if answer_window_closed or session.status == TriviaSession.Status.CLOSED:
            for question in data['questions']:
                answer = answers_by_question.get(question['id'])
                question['selected_choice'] = answer.selected_choice if answer else None
                question['is_correct'] = bool(answer and answer.selected_choice == question['correct_choice'])
        elif answers_by_question:
            for question in data['questions']:
                answer = answers_by_question.get(question['id'])
                question['selected_choice'] = answer.selected_choice if answer else None
        return Response(data)

    data = TriviaSessionSerializer(session).data
    data['questions'] = PublicTriviaQuestionSerializer(session.questions.all(), many=True).data
    data['has_submitted'] = bool(answers_by_question)
    if answers_by_question:
        for question in data['questions']:
            answer = answers_by_question.get(question['id'])
            question['selected_choice'] = answer.selected_choice if answer else None
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_publish(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if not can_manage_cycle(request.user, session.master_cycle):
        return Response({'detail': "Only this cycle's master can publish trivia."}, status=status.HTTP_403_FORBIDDEN)
    cycle = session.master_cycle
    if cycle.status != MasterCycle.Status.ACTIVE or not cycle.start_date <= timezone.localdate() <= cycle.end_date:
        return Response({'detail': 'Trivia can only be published during an active cycle.'}, status=status.HTTP_409_CONFLICT)
    session.status = TriviaSession.Status.LIVE
    session.publish_at = timezone.now()
    session.save(update_fields=['status', 'publish_at'])
    if session.master_cycle.team:
        notify_trivia_published(session.master_cycle.team, session, request.user)
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_answers(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if session.status != TriviaSession.Status.LIVE:
        return Response({'detail': 'Answers are only accepted for live trivia.'}, status=status.HTTP_409_CONFLICT)
    if session.close_at and timezone.now() >= session.close_at:
        return Response({'detail': 'The answer window has closed.'}, status=status.HTTP_409_CONFLICT)
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
        trivia_question_id=question.id,
        user_id=request.user.id,
        defaults={'selected_choice': serializer.validated_data['selected_choice']},
    )
    return Response(UserAnswerSerializer(answer).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_evaluate(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions', 'answers__user'), pk=pk)
    if not can_manage_cycle(request.user, session.master_cycle):
        return Response({'detail': "Only this cycle's master can evaluate trivia."}, status=status.HTTP_403_FORBIDDEN)
    if session.close_at and timezone.now() < session.close_at:
        return Response({'detail': 'This trivia can be evaluated after its answer window closes.'}, status=status.HTTP_409_CONFLICT)
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
    if session.close_at:
        session.save(update_fields=['status'])
    else:
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
    return Response([
        {'user_id': user.id, 'username': user.username, 'trophy_count': user.trophy_count}
        for user in leaderboard
    ])
