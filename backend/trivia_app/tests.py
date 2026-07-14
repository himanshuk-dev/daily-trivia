import re

from django.core import mail
from django.contrib.auth.models import User
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PLATFORM_ADMIN_EMAILS={'himanshu.kumar@ssc-spc.gc.ca'},
)
class EmailCodeAuthenticationTests(APITestCase):
    def test_registration_verification_and_logout(self):
        email = 'himanshu.kumar@ssc-spc.gc.ca'
        response = self.client.post(
            '/api/auth/request-code/',
            {'username': 'himanshu', 'email': email},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        code = re.search(r'\b\d{6}\b', mail.outbox[0].body).group(0)
        response = self.client.post(
            '/api/auth/verify-code/',
            {'email': email, 'code': code},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['user']['is_staff'])

        token = response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, status.HTTP_200_OK)
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
