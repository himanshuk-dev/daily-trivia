from django.contrib.auth.models import User
from rest_framework import serializers

from .models import MasterCycle, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = ['id', 'prompt', 'choices', 'correct_choice', 'explanation', 'sort_order']


class TriviaSessionSerializer(serializers.ModelSerializer):
    questions = TriviaQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TriviaSession
        fields = ['id', 'master_cycle', 'title', 'topic', 'status', 'publish_at', 'close_at', 'questions']


class MasterCycleSerializer(serializers.ModelSerializer):
    master_username = serializers.CharField(write_only=True)
    master_name = serializers.CharField(source='master.username', read_only=True)
    trivia_sessions = TriviaSessionSerializer(many=True, read_only=True)

    class Meta:
        model = MasterCycle
        fields = ['id', 'master_username', 'master_name', 'topic', 'start_date', 'end_date', 'status', 'trivia_sessions']

    def create(self, validated_data):
        master_username = validated_data.pop('master_username')
        master = User.objects.get(username=master_username)
        return MasterCycle.objects.create(master=master, **validated_data)


class UserAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAnswer
        fields = ['id', 'trivia_session', 'trivia_question', 'user', 'selected_choice', 'is_correct', 'submitted_at', 'evaluated_at']
        read_only_fields = ['id', 'is_correct', 'submitted_at', 'evaluated_at']


class TrophyAwardSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = TrophyAward
        fields = ['id', 'trivia_session', 'user', 'username', 'reason', 'awarded_at']
