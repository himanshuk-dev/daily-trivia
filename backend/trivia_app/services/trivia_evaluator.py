from django.db import transaction
from django.utils import timezone

from ..models import TrophyAward, TriviaSession


def evaluate_expired_trivia_sessions(session_ids=None) -> int:
    """Close expired live sessions and award trophies exactly once."""
    now = timezone.now()
    filters = {
        'status': TriviaSession.Status.LIVE,
        'close_at__isnull': False,
        'close_at__lte': now,
    }
    if session_ids is not None:
        filters['id__in'] = session_ids

    evaluated = 0
    with transaction.atomic():
        sessions = TriviaSession.objects.select_for_update().filter(**filters).prefetch_related('answers__trivia_question')
        for session in sessions:
            for answer in session.answers.all():
                answer.is_correct = answer.selected_choice == answer.trivia_question.correct_choice
                answer.evaluated_at = now
                answer.save(update_fields=['is_correct', 'evaluated_at'])
                if answer.is_correct:
                    TrophyAward.objects.get_or_create(
                        trivia_session=session,
                        user=answer.user,
                        defaults={
                            'reason': 'Correct trivia answer',
                            'answered_at': answer.submitted_at,
                        },
                    )
            session.status = TriviaSession.Status.CLOSED
            session.save(update_fields=['status'])
            evaluated += 1
    return evaluated
