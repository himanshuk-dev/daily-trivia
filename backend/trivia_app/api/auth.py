import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from ..models import EmailLoginCode
from ..serializers import UsernameUpdateSerializer, UserSerializer
from ..services.email_sender import EmailDeliveryError, send_login_code_email


logger = logging.getLogger(__name__)


def user_payload(user: User) -> dict:
    return UserSerializer(user).data


def email_domain_is_allowed(email: str) -> bool:
    local_part, separator, domain = email.rpartition('@')
    return bool(local_part and separator and domain in settings.ALLOWED_EMAIL_DOMAINS)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_request_code(request):
    email = request.data.get('email', '').strip().lower()
    username = request.data.get('username', '').strip()
    first_name = request.data.get('first_name', '').strip()
    last_name = request.data.get('last_name', '').strip()
    if not email:
        return Response({'email': ['Email is required.']}, status=status.HTTP_400_BAD_REQUEST)
    if not email_domain_is_allowed(email):
        return Response(
            {'email': ['Use an SSC email address ending in @ssc-spc.gc.ca.']},
            status=status.HTTP_403_FORBIDDEN,
        )

    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        if not username:
            return Response({'username': ['Username is required for registration.']}, status=status.HTTP_400_BAD_REQUEST)
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
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=['first_name', 'last_name'])

    code = f'{secrets.randbelow(1_000_000):06d}'
    EmailLoginCode.objects.filter(user=user, used_at__isnull=True).delete()
    login_code = EmailLoginCode.objects.create(
        user=user,
        code_hash=make_password(code),
        expires_at=timezone.now() + timedelta(minutes=settings.LOGIN_CODE_EXPIRY_MINUTES),
    )
    try:
        send_login_code_email(recipient=email, code=code)
    except EmailDeliveryError:
        login_code.delete()
        logger.exception('Unable to send a login code email.')
        return Response(
            {'detail': 'The login email could not be sent. Please try again later.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response({'detail': 'A login code has been sent.', 'email': email})


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_verify_code(request):
    email = request.data.get('email', '').strip().lower()
    code = request.data.get('code', '').strip()
    if not email_domain_is_allowed(email):
        return Response(
            {'email': ['Use an SSC email address ending in @ssc-spc.gc.ca.']},
            status=status.HTTP_403_FORBIDDEN,
        )
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


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def auth_me(request):
    if request.method == 'PATCH':
        serializer = UsernameUpdateSerializer(
            data=request.data,
            context={'user': request.user},
        )
        serializer.is_valid(raise_exception=True)
        request.user.username = serializer.validated_data['username']
        request.user.save(update_fields=['username'])
    return Response(user_payload(request.user))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
