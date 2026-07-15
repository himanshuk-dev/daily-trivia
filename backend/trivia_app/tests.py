import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.models import User
from django.test import override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from trivia_app.models import TeamMembership, TriviaSession
from trivia_app.services.ai_generator import GeneratedQuestion


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PLATFORM_ADMIN_EMAILS={'himanshu.kumar@ssc-spc.gc.ca'},
)
class EmailCodeAuthenticationTests(APITestCase):
    def test_registration_verification_and_logout(self):
        email = 'himanshu.kumar@ssc-spc.gc.ca'
        response = self.client.post(
            '/api/auth/request-code/',
            {
                'username': 'himanshu',
                'email': email,
                'first_name': 'Himanshu',
                'last_name': 'Kumar',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        user = User.objects.get(email=email)
        self.assertEqual(user.first_name, 'Himanshu')
        self.assertEqual(user.last_name, 'Kumar')

        code = re.search(r'\b\d{6}\b', mail.outbox[0].body).group(0)
        response = self.client.post(
            '/api/auth/verify-code/',
            {'email': email, 'code': code},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['user']['is_staff'])
        self.assertEqual(response.data['user']['first_name'], 'Himanshu')
        self.assertEqual(response.data['user']['last_name'], 'Kumar')

        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/auth/me/').data['first_name'], 'Himanshu')
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.client.get('/api/auth/me/').status_code, status.HTTP_401_UNAUTHORIZED)


class TeamTriviaWorkflowTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='platform-admin', email='admin@example.com', is_staff=True, is_superuser=True,
        )
        self.master = User.objects.create_user(username='master', email='master@example.com')
        self.player = User.objects.create_user(username='player', email='player@example.com')

    def authenticate(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

    def test_platform_admin_assigns_initial_team_admin_who_can_assign_self_as_master(self):
        team_admin = User.objects.create_user(username='team-admin', email='team-admin@example.com')
        direct_member = User.objects.create_user(username='direct-member', email='direct-member@example.com')
        self.authenticate(self.admin)
        response = self.client.post('/api/teams/', {
            'name': 'Policy',
            'approval_required': True,
            'initial_admin_id': team_admin.id,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team_id = response.data['id']

        membership = TeamMembership.objects.get(team_id=team_id, user=team_admin)
        self.assertEqual(membership.role, TeamMembership.Role.TEAM_ADMIN)
        self.assertEqual(membership.status, TeamMembership.Status.APPROVED)
        self.assertFalse(TeamMembership.objects.filter(team_id=team_id, user=self.admin).exists())

        self.authenticate(team_admin)
        response = self.client.post(f'/api/teams/{team_id}/members/', {
            'user_id': direct_member.id,
            'role': 'member',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], TeamMembership.Status.APPROVED)
        self.assertEqual(response.data['role'], TeamMembership.Role.MEMBER)

        response = self.client.post(f'/api/teams/{team_id}/members/', {
            'user_id': direct_member.id,
            'role': 'member',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        response = self.client.post('/api/master-cycles/', {
            'team': team_id,
            'master_username': team_admin.username,
            'topic': 'Canada',
            'start_date': '2026-07-28',
            'end_date': '2026-08-10',
            'status': 'active',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['master_name'], team_admin.username)
        cycle_id = response.data['id']

        generated = GeneratedQuestion(
            prompt='What is the capital of Canada?',
            choices=['Ottawa', 'Toronto', 'Vancouver', 'Montreal'],
            correct_choice='Ottawa',
            explanation='Ottawa is the capital of Canada.',
        )
        with patch('trivia_app.api.trivia.TriviaGenerator.generate', return_value=generated):
            response = self.client.post(f'/api/master-cycles/{cycle_id}/generate-trivia/', format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], TriviaSession.Status.LIVE)
        self.assertEqual(len(response.data['questions']), 1)
        self.assertIsNotNone(response.data['publish_at'])
        self.assertIsNotNone(response.data['close_at'])

        session = TriviaSession.objects.get(pk=response.data['id'])
        self.assertAlmostEqual(
            (session.close_at - session.publish_at).total_seconds(),
            timedelta(hours=24).total_seconds(),
            delta=1,
        )
        self.assertEqual(
            self.client.post(f'/api/trivia-sessions/{session.id}/evaluate/').status_code,
            status.HTTP_409_CONFLICT,
        )

        session.close_at = timezone.now() - timedelta(seconds=1)
        session.save(update_fields=['close_at'])
        self.authenticate(direct_member)
        question_id = session.questions.get().id
        self.assertEqual(self.client.post(f'/api/trivia-sessions/{session.id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Ottawa',
        }, format='json').status_code, status.HTTP_409_CONFLICT)

    def test_team_approval_manual_trivia_and_team_leaderboard(self):
        self.authenticate(self.admin)
        response = self.client.post(
            '/api/teams/', {'name': 'Engineering', 'approval_required': True}, format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = response.data

        for user in (self.master, self.player):
            self.authenticate(user)
            response = self.client.post('/api/teams/join/', {'invite_code': team['invite_code']}, format='json')
            self.assertEqual(response.data['status'], 'pending')

        self.authenticate(self.admin)
        memberships = self.client.get(f"/api/teams/{team['id']}/members/").data
        for membership in memberships:
            if membership['user'] in {self.master.id, self.player.id}:
                response = self.client.patch(
                    f"/api/teams/{team['id']}/members/{membership['id']}/",
                    {'status': 'approved'}, format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post('/api/master-cycles/', {
            'team': team['id'],
            'master_username': self.master.username,
            'topic': 'Space',
            'start_date': '2026-07-14',
            'end_date': '2026-07-27',
            'status': 'active',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        cycle_id = response.data['id']

        self.authenticate(self.master)
        response = self.client.post(f'/api/master-cycles/{cycle_id}/trivia-sessions/', {
            'title': 'Space Basics',
            'questions': [{
                'prompt': 'Which planet is known as the Red Planet?',
                'choices': ['Earth', 'Mars', 'Venus', 'Jupiter'],
                'correct_choice': 'Mars',
                'explanation': 'Iron oxides make Mars appear red.',
            }],
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.data['id']
        question_id = response.data['questions'][0]['id']
        self.assertEqual(self.client.post(f'/api/trivia-sessions/{session_id}/publish/').status_code, status.HTTP_200_OK)

        self.authenticate(self.player)
        teams = self.client.get('/api/teams/').data
        self.assertIsNone(teams[0]['invite_code'])
        notifications = self.client.get('/api/notifications/').data
        self.assertEqual(notifications[0]['message'], 'New trivia is live: Space Basics')
        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertNotIn('correct_choice', response.data['questions'][0])
        response = self.client.post(f'/api/trivia-sessions/{session_id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Mars',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.authenticate(self.master)
        response = self.client.post(f'/api/trivia-sessions/{session_id}/evaluate/')
        self.assertEqual(response.data['trophies_awarded'], 1)

        self.authenticate(self.player)
        response = self.client.get(f"/api/leaderboard/?team={team['id']}")
        self.assertEqual(response.data[0]['username'], self.player.username)
        self.assertEqual(response.data[0]['trophy_count'], 1)
