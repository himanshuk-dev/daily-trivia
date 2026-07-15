from django.contrib.auth.models import User
from rest_framework import serializers

from .models import MasterCycle, Notification, Team, TeamMembership, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'date_joined']
        read_only_fields = ['id', 'is_staff', 'date_joined']


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

    class Meta:
        model = MasterCycle
        fields = ['id', 'team', 'master_username', 'master_name', 'topic', 'start_date', 'end_date', 'status', 'trivia_sessions']

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
