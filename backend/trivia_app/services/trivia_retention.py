from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from ..models import TriviaQuestion, TriviaSession


def delete_expired_trivia_questions() -> int:
    """Delete question and answer details after retention, preserving cycle trophies."""
    cutoff = timezone.now() - timedelta(days=settings.TRIVIA_QUESTION_RETENTION_DAYS)
    expired_session_ids = TriviaSession.objects.filter(
        status=TriviaSession.Status.CLOSED,
        close_at__lt=cutoff,
    ).values_list('id', flat=True)
    deleted_count, _ = TriviaQuestion.objects.filter(
        trivia_session_id__in=expired_session_ids,
    ).delete()
    return deleted_count
