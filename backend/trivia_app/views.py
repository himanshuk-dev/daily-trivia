from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MasterCycle, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer
from .serializers import (
    MasterCycleSerializer,
    TrophyAwardSerializer,
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


@api_view(['GET', 'POST'])
def user_list_create(request):
    if request.method == 'GET':
        users = User.objects.order_by('username')
        return Response(UserSerializer(users, many=True).data)

    serializer = UserSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = User.objects.create_user(username=serializer.validated_data['username'])
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(['GET', 'POST'])
def master_cycle_list_create(request):
    if request.method == 'GET':
        cycles = MasterCycle.objects.select_related('master').prefetch_related('trivia_sessions__questions').order_by('-start_date')
        return Response(MasterCycleSerializer(cycles, many=True).data)

    serializer = MasterCycleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    cycle = serializer.save()
    return Response(MasterCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def master_cycle_generate_trivia(request, pk: int):
    cycle = get_object_or_404(MasterCycle, pk=pk)
    question_count = int(request.data.get('question_count', 5))
    title = request.data.get('title') or f'{cycle.topic} Trivia'

    generator = TriviaGenerator()
    generated_questions = generator.generate(cycle.topic, question_count=question_count)

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


@api_view(['GET'])
def trivia_session_retrieve(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions'), pk=pk)
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
def trivia_session_publish(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    session.status = TriviaSession.Status.LIVE
    session.publish_at = timezone.now()
    session.save(update_fields=['status', 'publish_at'])
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
def trivia_session_answers(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    serializer = UserAnswerSerializer(data={
        'trivia_session': session.id,
        'trivia_question': request.data.get('trivia_question'),
        'user': request.data.get('user'),
        'selected_choice': request.data.get('selected_choice'),
    })
    serializer.is_valid(raise_exception=True)
    answer, _created = UserAnswer.objects.update_or_create(
        trivia_session=session,
        trivia_question_id=serializer.validated_data['trivia_question'].id,
        user_id=serializer.validated_data['user'].id,
        defaults={'selected_choice': serializer.validated_data['selected_choice']},
    )
    return Response(UserAnswerSerializer(answer).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def trivia_session_evaluate(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions', 'answers__user'), pk=pk)
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
    return Response({'session_id': session.id, 'correct_users': correct_user_ids, 'trophies_awarded': trophy_count})


@api_view(['GET'])
def leaderboard_view(request):
    leaderboard = (
        User.objects.annotate(trophy_count=Count('trophy_awards'))
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
