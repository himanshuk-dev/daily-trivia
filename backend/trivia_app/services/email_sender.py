import smtplib
from typing import Optional

import httpx
from django.conf import settings
from django.core.mail import send_mail
from django.utils.html import escape


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
    subject_cycle_name = ' '.join(cycle_name.splitlines())
    safe_master_name = escape(master_name)
    safe_team_name = escape(team_name)
    safe_cycle_name = escape(cycle_name)
    safe_start_date = escape(str(start_date))
    safe_end_date = escape(str(end_date))
    safe_app_url = escape(settings.PUBLIC_APP_URL)
    send_transactional_email(
        recipient=recipient,
        subject=f'You are the trivia master for {subject_cycle_name}',
        message=(
            f'Hello {master_name},\n\n'
            'You have been assigned as the trivia master for a new sprint cycle.\n\n'
            f'Team: {team_name}\n'
            f'Sprint cycle: {cycle_name}\n'
            f'Schedule: {start_date} through {end_date}\n\n'
            'Next step\n'
            'Sign in to Daily Trivia to create and manage questions for your team:\n'
            f'{settings.PUBLIC_APP_URL}\n\n'
            'Daily Trivia'
        ),
        html_message=(
            f'<p>Hello {safe_master_name},</p>'
            '<p>You have been assigned as the trivia master for a new sprint cycle.</p>'
            '<h2 style="font-size:18px;margin:24px 0 12px">Cycle details</h2>'
            '<ul>'
            f'<li><strong>Team:</strong> {safe_team_name}</li>'
            f'<li><strong>Sprint cycle:</strong> {safe_cycle_name}</li>'
            f'<li><strong>Schedule:</strong> {safe_start_date} through {safe_end_date}</li>'
            '</ul>'
            '<h2 style="font-size:18px;margin:24px 0 12px">Next step</h2>'
            '<p>Sign in to Daily Trivia to create and manage questions for your team.</p>'
            f'<p><a href="{safe_app_url}" style="display:inline-block;padding:12px 18px;'
            'background:#5b21b6;color:#ffffff;text-decoration:none;border-radius:6px;'
            'font-weight:700">Open Daily Trivia</a></p>'
            '<p>Daily Trivia</p>'
        ),
    )


def send_transactional_email(*, recipient: str, subject: str, message: str, html_message: Optional[str] = None) -> None:

    if settings.EMAIL_DELIVERY_PROVIDER == 'smtp':
        _send_with_smtp(recipient=recipient, subject=subject, message=message, html_message=html_message)
        return
    if settings.EMAIL_DELIVERY_PROVIDER == 'brevo':
        _send_with_brevo(recipient=recipient, subject=subject, message=message, html_message=html_message)
        return
    raise EmailDeliveryError(
        f'Unsupported EMAIL_DELIVERY_PROVIDER: {settings.EMAIL_DELIVERY_PROVIDER}'
    )


def _send_with_smtp(*, recipient: str, subject: str, message: str, html_message: Optional[str] = None) -> None:
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_message,
        )
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError('SMTP email delivery failed.') from exc


def _send_with_brevo(*, recipient: str, subject: str, message: str, html_message: Optional[str] = None) -> None:
    if not settings.BREVO_API_KEY:
        raise EmailDeliveryError('BREVO_API_KEY is required for Brevo email delivery.')

    try:
        payload = {
            'sender': {
                'email': settings.BREVO_SENDER_EMAIL,
                'name': settings.BREVO_SENDER_NAME,
            },
            'to': [{'email': recipient}],
            'subject': subject,
            'textContent': message,
        }
        if html_message:
            payload['htmlContent'] = html_message
        response = httpx.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'accept': 'application/json',
                'api-key': settings.BREVO_API_KEY,
                'content-type': 'application/json',
            },
            json=payload,
            timeout=settings.EMAIL_TIMEOUT,
        )
        response.raise_for_status()
    except (httpx.HTTPError, OSError) as exc:
        raise EmailDeliveryError('Brevo email delivery failed.') from exc
