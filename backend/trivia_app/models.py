from django.conf import settings
from django.db import models


class MasterCycle(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        CLOSED = 'closed', 'Closed'

    master = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='master_cycles')
    topic = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.topic} ({self.start_date} - {self.end_date})'


class TriviaSession(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        LIVE = 'live', 'Live'
        CLOSED = 'closed', 'Closed'

    master_cycle = models.ForeignKey(MasterCycle, on_delete=models.CASCADE, related_name='trivia_sessions')
    title = models.CharField(max_length=200)
    topic = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    publish_at = models.DateTimeField(null=True, blank=True)
    close_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.title


class TriviaQuestion(models.Model):
    trivia_session = models.ForeignKey(TriviaSession, on_delete=models.CASCADE, related_name='questions')
    prompt = models.TextField()
    choices = models.JSONField(default=list)
    correct_choice = models.CharField(max_length=255)
    explanation = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    def __str__(self) -> str:
        return self.prompt[:80]


class UserAnswer(models.Model):
    trivia_question = models.ForeignKey(TriviaQuestion, on_delete=models.CASCADE, related_name='answers')
    trivia_session = models.ForeignKey(TriviaSession, on_delete=models.CASCADE, related_name='answers')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trivia_answers')
    selected_choice = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    evaluated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trivia_session', 'trivia_question', 'user'], name='unique_user_answer_per_question'),
        ]


class TrophyAward(models.Model):
    trivia_session = models.ForeignKey(TriviaSession, on_delete=models.CASCADE, related_name='trophy_awards')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trophy_awards')
    reason = models.CharField(max_length=255, default='Correct trivia answer')
    awarded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['trivia_session', 'user'], name='unique_trophy_per_user_session'),
        ]
