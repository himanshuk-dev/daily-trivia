import re
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from trivia_app.models import Notification, Team, TeamMembership, TriviaSession
from trivia_app.services.ai_generator import GROQ_BASE_URL, GeneratedQuestion, TriviaGenerator


class TriviaGeneratorTests(SimpleTestCase):
    @staticmethod
    def response(content):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        )

    def test_requires_groq_api_key(self):
        with patch.dict(os.environ, {'GROQ_API_KEY': ''}):
            with self.assertRaisesMessage(RuntimeError, 'GROQ_API_KEY is required'):
                TriviaGenerator().generate('Canada')

    @patch('openai.OpenAI')
    def test_uses_groq_and_retries_invalid_domain_output_once(self, openai_client):
        invalid = self.response(
            '{"prompt":"Capital?","choices":["Ottawa","Ottawa","Toronto","Montreal"],'
            '"correct_choice":"Ottawa","explanation":"It is Ottawa."}'
        )
        valid = self.response(
            '{"prompt":"What is Canada’s capital?",'
            '"choices":["Ottawa","Toronto","Vancouver","Montreal"],'
            '"correct_choice":"Ottawa","explanation":"Ottawa is Canada’s capital."}'
        )
        client = openai_client.return_value
        client.chat.completions.create.side_effect = [invalid, valid]

        with patch.dict(os.environ, {
            'GROQ_API_KEY': 'test-key',
            'GROQ_MODEL': 'openai/gpt-oss-20b',
        }):
            question = TriviaGenerator().generate('Canada')

        openai_client.assert_called_once_with(api_key='test-key', base_url=GROQ_BASE_URL)
        self.assertEqual(client.chat.completions.create.call_count, 2)
        self.assertEqual(question.correct_choice, 'Ottawa')


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

    def test_platform_admin_can_edit_and_delete_team(self):
        self.authenticate(self.admin)
        response = self.client.post('/api/teams/', {
            'name': 'Temporary Team',
            'approval_required': True,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team_id = response.data['id']

        self.authenticate(self.player)
        self.assertEqual(self.client.patch(
            f'/api/teams/{team_id}/', {'name': 'Unauthorized'}, format='json',
        ).status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate(self.admin)
        response = self.client.patch(f'/api/teams/{team_id}/', {
            'name': 'Renamed Team',
            'approval_required': False,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Renamed Team')
        self.assertFalse(response.data['approval_required'])

        self.assertEqual(self.client.delete(f'/api/teams/{team_id}/').status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Team.objects.filter(pk=team_id).exists())

    @override_settings(TRIVIA_ANSWER_WINDOW_HOURS=0.25)
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

        sprint_start = timezone.localdate()
        response = self.client.post('/api/master-cycles/', {
            'team': team_id,
            'master_username': team_admin.username,
            'topic': 'Canada Sprint',
            'start_date': sprint_start.isoformat(),
            'end_date': (sprint_start + timedelta(days=13)).isoformat(),
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
        with patch('trivia_app.api.trivia.TriviaGenerator.generate', return_value=generated) as generate:
            response = self.client.post(
                f'/api/master-cycles/{cycle_id}/generate-trivia/',
                {'topic': 'Science'},
                format='json',
            )
        generate.assert_called_once_with('Science')
        self.assertEqual(response.data['topic'], 'Science')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], TriviaSession.Status.LIVE)
        self.assertEqual(len(response.data['questions']), 1)
        self.assertIsNotNone(response.data['publish_at'])
        self.assertIsNotNone(response.data['close_at'])

        session = TriviaSession.objects.get(pk=response.data['id'])
        self.assertTrue(Notification.objects.filter(
            user=self.admin,
            team_id=team_id,
            message=f'New trivia is live: {session.title}',
        ).exists())
        self.assertAlmostEqual(
            (session.close_at - session.publish_at).total_seconds(),
            timedelta(minutes=15).total_seconds(),
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
        response = self.client.get(f'/api/trivia-sessions/{session.id}/')
        self.assertEqual(response.data['questions'][0]['correct_choice'], 'Ottawa')
        self.assertIsNone(response.data['questions'][0]['selected_choice'])
        self.assertFalse(response.data['questions'][0]['is_correct'])

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

        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertEqual(response.data['submission_count'], 1)
        self.assertEqual(response.data['submissions'][0]['username'], self.player.username)
        self.assertEqual(response.data['submissions'][0]['answers_submitted'], 1)
        self.assertNotIn('selected_choice', response.data['submissions'][0])

        self.authenticate(self.player)
        response = self.client.get(f"/api/leaderboard/?team={team['id']}")
        self.assertEqual(response.data[0]['username'], self.player.username)
        self.assertEqual(response.data[0]['trophy_count'], 1)

        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertEqual(response.data['questions'][0]['correct_choice'], 'Mars')
        self.assertEqual(response.data['questions'][0]['selected_choice'], 'Mars')
        self.assertTrue(response.data['questions'][0]['is_correct'])
        self.assertEqual(response.data['questions'][0]['explanation'], 'Iron oxides make Mars appear red.')

        self.assertEqual(self.client.get('/api/admin/overview/').status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.admin)
        response = self.client.get('/api/admin/overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        overview_team = next(item for item in response.data['teams'] if item['id'] == team['id'])
        self.assertEqual(len(overview_team['members']), 3)
        self.assertEqual(overview_team['trivia_sessions'][0]['title'], 'Space Basics')
        self.assertEqual(overview_team['trivia_sessions'][0]['submissions'][0]['username'], self.player.username)
        self.assertEqual(overview_team['leaderboard'][0]['username'], self.player.username)
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['username'], self.player.username)
        self.assertEqual(response.data[0]['trophy_count'], 1)
