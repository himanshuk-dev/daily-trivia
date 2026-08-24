import smtplib

import httpx
from django.conf import settings
from django.core.mail import send_mail


class EmailDeliveryError(RuntimeError):
    """Raised when a transactional email cannot be delivered."""


def send_login_code_email(*, recipient: str, code: str) -> None:
    subject = 'Your Daily Trivia login code'
    message = (
        f'Your Daily Trivia login code is {code}. '
        f'It expires in {settings.LOGIN_CODE_EXPIRY_MINUTES} minutes.'
    )
    send_transactional_email(recipient=recipient, subject=subject, message=message)


def send_master_cycle_assigned_email(*, recipient: str, master_name: str, team_name: str, cycle_name: str, start_date, end_date) -> None:
    send_transactional_email(
        recipient=recipient,
        subject=f'You are the trivia master for {cycle_name}',
        message=(
            f'Hello {master_name},\n\n'
            f'You have been assigned as the trivia master for the {cycle_name} sprint cycle '
            f'on {team_name}. The cycle runs from {start_date} to {end_date}.\n\n'
            'Sign in to Daily Trivia to create and manage questions for your team.'
        ),
    )


def send_transactional_email(*, recipient: str, subject: str, message: str) -> None:

    if settings.EMAIL_DELIVERY_PROVIDER == 'smtp':
        _send_with_smtp(recipient=recipient, subject=subject, message=message)
        return
    if settings.EMAIL_DELIVERY_PROVIDER == 'brevo':
        _send_with_brevo(recipient=recipient, subject=subject, message=message)
        return
    raise EmailDeliveryError(
        f'Unsupported EMAIL_DELIVERY_PROVIDER: {settings.EMAIL_DELIVERY_PROVIDER}'
    )


def _send_with_smtp(*, recipient: str, subject: str, message: str) -> None:
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
        )
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError('SMTP email delivery failed.') from exc


def _send_with_brevo(*, recipient: str, subject: str, message: str) -> None:
    if not settings.BREVO_API_KEY:
        raise EmailDeliveryError('BREVO_API_KEY is required for Brevo email delivery.')

    try:
        response = httpx.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'accept': 'application/json',
                'api-key': settings.BREVO_API_KEY,
                'content-type': 'application/json',
            },
            json={
                'sender': {
                    'email': settings.BREVO_SENDER_EMAIL,
                    'name': settings.BREVO_SENDER_NAME,
                },
                'to': [{'email': recipient}],
                'subject': subject,
                'textContent': message,
            },
            timeout=settings.EMAIL_TIMEOUT,
        )
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        raise EmailDeliveryError('Brevo email delivery failed.') from exc
