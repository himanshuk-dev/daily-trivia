from django.contrib.auth.models import User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models import Count
from rest_framework import serializers

from .models import MasterCycle, Notification, Team, TeamMembership, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'is_staff', 'date_joined']


class UsernameUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )

    def validate_username(self, value):
        username = value.strip()
        if not username:
            raise serializers.ValidationError('Username cannot be blank.')
        if User.objects.filter(username__iexact=username).exclude(pk=self.context['user'].pk).exists():
            raise serializers.ValidationError('This username is already in use.')
        return username


class TriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = ['id', 'prompt', 'choices', 'correct_choice', 'explanation', 'sort_order']
        read_only_fields = ['id', 'sort_order']

    def validate(self, attrs):
        choices = attrs.get('choices', [])
        if len(choices) < 2:
            raise serializers.ValidationError({'choices': 'At least two choices are required.'})
        if attrs.get('correct_choice') not in choices:
            raise serializers.ValidationError({'correct_choice': 'The correct choice must be one of the choices.'})
        return attrs


class PublicTriviaQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaQuestion
        fields = ['id', 'prompt', 'choices', 'sort_order']


class TriviaSessionSerializer(serializers.ModelSerializer):
    questions = TriviaQuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TriviaSession
        fields = ['id', 'master_cycle', 'title', 'topic', 'status', 'publish_at', 'close_at', 'questions']


class TriviaSessionSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = TriviaSession
        fields = ['id', 'master_cycle', 'title', 'topic', 'status', 'publish_at', 'close_at']


class MasterCycleSerializer(serializers.ModelSerializer):
    master_username = serializers.CharField(write_only=True)
    master_name = serializers.CharField(source='master.username', read_only=True)
    trivia_sessions = TriviaSessionSummarySerializer(many=True, read_only=True)
    sprint_leaderboard = serializers.SerializerMethodField()
    sprint_winner = serializers.SerializerMethodField()

    class Meta:
        model = MasterCycle
        fields = [
            'id', 'team', 'master_username', 'master_name', 'topic', 'daily_topics',
            'start_date', 'end_date', 'status', 'trivia_sessions', 'sprint_leaderboard', 'sprint_winner',
        ]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})
        daily_topics = attrs.get('daily_topics', [])
        seen_dates = set()
        for item in daily_topics:
            if not isinstance(item, dict) or not item.get('date') or not str(item.get('topic', '')).strip():
                raise serializers.ValidationError({'daily_topics': 'Each scheduled day needs a date and topic.'})
            try:
                scheduled_date = serializers.DateField().to_internal_value(item['date'])
            except serializers.ValidationError as error:
                raise serializers.ValidationError({'daily_topics': 'Use valid dates for daily topics.'}) from error
            if start_date and end_date and not start_date <= scheduled_date <= end_date:
                raise serializers.ValidationError({'daily_topics': 'Daily topic dates must be inside the sprint.'})
            if scheduled_date in seen_dates:
                raise serializers.ValidationError({'daily_topics': 'Each sprint date can appear only once.'})
            seen_dates.add(scheduled_date)
            item['topic'] = item['topic'].strip()
        return attrs

    def get_sprint_leaderboard(self, obj):
        rows = TrophyAward.objects.filter(trivia_session__master_cycle=obj).values(
            'user_id', 'user__username',
        ).annotate(trophy_count=Count('id')).order_by('-trophy_count', 'user__username')
        return [
            {'user_id': row['user_id'], 'username': row['user__username'], 'trophy_count': row['trophy_count']}
            for row in rows
        ]

    def get_sprint_winner(self, obj):
        leaderboard = self.get_sprint_leaderboard(obj)
        return leaderboard[0] if leaderboard else None

    def create(self, validated_data):
        master_username = validated_data.pop('master_username')
        master = User.objects.get(username=master_username)
        return MasterCycle.objects.create(master=master, **validated_data)


class TeamMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)

    class Meta:
        model = TeamMembership
        fields = [
            'id', 'team', 'user', 'username', 'email', 'first_name', 'last_name',
            'role', 'status', 'joined_at', 'approved_at',
        ]
        read_only_fields = [
            'id', 'team', 'user', 'username', 'email', 'first_name', 'last_name',
            'joined_at', 'approved_at',
        ]


class TeamSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    membership_role = serializers.SerializerMethodField()
    membership_status = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'name', 'slug', 'invite_code', 'approval_required', 'created_by', 'created_by_username', 'created_at',
            'membership_role', 'membership_status', 'member_count',
        ]
        read_only_fields = ['id', 'invite_code', 'created_by', 'created_by_username', 'created_at']

    def _membership(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        return obj.memberships.filter(user=request.user).first()

    def get_membership_role(self, obj):
        membership = self._membership(obj)
        return membership.role if membership else None

    def get_membership_status(self, obj):
        membership = self._membership(obj)
        return membership.status if membership else None

    def get_member_count(self, obj):
        return obj.memberships.filter(status=TeamMembership.Status.APPROVED).count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        membership = self._membership(instance)
        can_manage = bool(
            request
            and request.user.is_authenticated
            and (request.user.is_staff or (
                membership
                and membership.status == TeamMembership.Status.APPROVED
                and membership.role == TeamMembership.Role.TEAM_ADMIN
            ))
        )
        if not can_manage:
            data['invite_code'] = None
        return data


class NotificationSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source='team.name', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'team', 'team_name', 'message', 'read_at', 'created_at']


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
