from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Count, F, Min
from django.utils import timezone

from ..models import MasterCycle, Notification, TeamMembership, TrophyAward, TriviaSession


def finalize_expired_cycles() -> int:
    now = timezone.now()
    today = timezone.localdate()
    finalized_count = 0

    with transaction.atomic():
        cycles = MasterCycle.objects.select_for_update().filter(
            status=MasterCycle.Status.ACTIVE,
            end_date__lt=today,
        )

        for cycle in cycles:
            if cycle.trivia_sessions.filter(
                status=TriviaSession.Status.LIVE,
                close_at__gt=now,
            ).exists():
                continue

            ended_sessions = cycle.trivia_sessions.filter(
                status=TriviaSession.Status.LIVE,
            ).prefetch_related('answers__user', 'answers__trivia_question')
            for session in ended_sessions:
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
                session.close_at = session.close_at or now
                session.save(update_fields=['status', 'close_at'])

            leaderboard = list(TrophyAward.objects.filter(
                trivia_session__master_cycle=cycle,
            ).values(
                'user_id', 'user__username',
            ).annotate(
                trophy_count=Count('id'),
                first_correct_at=Min('answered_at'),
            ).order_by('-trophy_count', F('first_correct_at').asc(nulls_last=True), 'user__username'))

            cycle.status = MasterCycle.Status.CLOSED
            cycle.save(update_fields=['status'])
            finalized_count += 1

            if not cycle.team:
                continue

            if leaderboard:
                winning_score = leaderboard[0]['trophy_count']
                winner = leaderboard[0]['user__username']
                trophy_label = 'trophy' if winning_score == 1 else 'trophies'
                message = f'Cycle "{cycle.topic}" winner: {winner} with {winning_score} {trophy_label}!'
            else:
                message = f'Cycle "{cycle.topic}" has ended. No trophies were awarded.'

            recipient_ids = set(TeamMembership.objects.filter(
                team=cycle.team,
                status=TeamMembership.Status.APPROVED,
            ).values_list('user_id', flat=True))
            recipient_ids.add(cycle.master_id)
            recipient_ids.update(User.objects.filter(
                is_staff=True,
                is_active=True,
            ).values_list('id', flat=True))
            Notification.objects.bulk_create([
                Notification(
                    user_id=user_id,
                    team=cycle.team,
                    message=message[:255],
                )
                for user_id in recipient_ids
            ])

    return finalized_count
