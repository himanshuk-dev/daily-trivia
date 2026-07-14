import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count
from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import MasterCycle, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer
from .models import EmailLoginCode
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


def user_payload(user: User) -> dict:
    return UserSerializer(user).data


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_request_code(request):
    email = request.data.get('email', '').strip().lower()
    username = request.data.get('username', '').strip()
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
        user = User.objects.create_user(username=username, email=email, is_active=False)
    elif username and user.username.lower() != username.lower():
        return Response({'email': ['An account already exists for this email.']}, status=status.HTTP_400_BAD_REQUEST)

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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_list_create(request):
    users = User.objects.filter(is_active=True).order_by('username')
    return Response(UserSerializer(users, many=True).data)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def user_delete(request, pk: int):
    is_active_master = MasterCycle.objects.filter(
        master=request.user,
        status=MasterCycle.Status.ACTIVE,
    ).exists()
    if not (request.user.is_staff or is_active_master):
        return Response({'detail': 'Only an active master can remove users.'}, status=status.HTTP_403_FORBIDDEN)

    user = get_object_or_404(User, pk=pk)
    try:
        user.delete()
    except ProtectedError:
        return Response(
            {'detail': 'This user owns a master cycle and cannot be removed.'},
            status=status.HTTP_409_CONFLICT,
        )

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def master_cycle_list_create(request):
    if request.method == 'GET':
        cycles = MasterCycle.objects.select_related('master').prefetch_related('trivia_sessions__questions').order_by('-start_date')
        return Response(MasterCycleSerializer(cycles, many=True).data)

    if not request.user.is_staff:
        return Response({'detail': 'Only a platform admin can create master cycles.'}, status=status.HTTP_403_FORBIDDEN)

    serializer = MasterCycleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    cycle = serializer.save()
    return Response(MasterCycleSerializer(cycle).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def master_cycle_generate_trivia(request, pk: int):
    cycle = get_object_or_404(MasterCycle, pk=pk)
    if request.user != cycle.master and not request.user.is_staff:
        return Response({'detail': 'Only this cycle’s master can generate trivia.'}, status=status.HTTP_403_FORBIDDEN)
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
@permission_classes([IsAuthenticated])
def trivia_session_retrieve(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions'), pk=pk)
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_publish(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    if request.user != session.master_cycle.master and not request.user.is_staff:
        return Response({'detail': 'Only this cycle’s master can publish trivia.'}, status=status.HTTP_403_FORBIDDEN)
    session.status = TriviaSession.Status.LIVE
    session.publish_at = timezone.now()
    session.save(update_fields=['status', 'publish_at'])
    return Response(TriviaSessionSerializer(session).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trivia_session_answers(request, pk: int):
    session = get_object_or_404(TriviaSession, pk=pk)
    serializer = UserAnswerSerializer(data={
        'trivia_session': session.id,
        'trivia_question': request.data.get('trivia_question'),
        'user': request.user.id,
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
@permission_classes([IsAuthenticated])
def trivia_session_evaluate(request, pk: int):
    session = get_object_or_404(TriviaSession.objects.prefetch_related('questions', 'answers__user'), pk=pk)
    if request.user != session.master_cycle.master and not request.user.is_staff:
        return Response({'detail': 'Only this cycle’s master can evaluate trivia.'}, status=status.HTTP_403_FORBIDDEN)
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
@permission_classes([IsAuthenticated])
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
