import re
import os
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework import status
from rest_framework.test import APITestCase

from trivia_app.models import EmailLoginCode, MasterCycle, Notification, Team, TeamMembership, TrophyAward, TriviaQuestion, TriviaSession, UserAnswer
from trivia_app.services.ai_generator import GROQ_BASE_URL, GeneratedQuestion, TriviaGenerator
from trivia_app.services.email_sender import send_login_code_email


class TriviaGeneratorTests(SimpleTestCase):
    def test_health_check(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'ok'})

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
    EMAIL_DELIVERY_PROVIDER='brevo',
    BREVO_API_KEY='test-brevo-key',
    BREVO_SENDER_EMAIL='sender@example.com',
    BREVO_SENDER_NAME='Daily Trivia',
    EMAIL_TIMEOUT=10,
    LOGIN_CODE_EXPIRY_MINUTES=10,
)
class BrevoEmailDeliveryTests(SimpleTestCase):
    @patch('trivia_app.services.email_sender.httpx.post')
    def test_sends_login_code_through_brevo_api(self, post):
        post.return_value.raise_for_status.return_value = None

        send_login_code_email(recipient='player@example.com', code='123456')

        post.assert_called_once_with(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'accept': 'application/json',
                'api-key': 'test-brevo-key',
                'content-type': 'application/json',
            },
            json={
                'sender': {'email': 'sender@example.com', 'name': 'Daily Trivia'},
                'to': [{'email': 'player@example.com'}],
                'subject': 'Your Daily Trivia login code',
                'textContent': 'Your Daily Trivia login code is 123456. It expires in 10 minutes.',
            },
            timeout=10,
        )


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    PLATFORM_ADMIN_EMAILS={'himanshu.kumar@ssc-spc.gc.ca'},
    ALLOWED_EMAIL_DOMAINS={'ssc-spc.gc.ca'},
)
class EmailCodeAuthenticationTests(APITestCase):
    @patch('trivia_app.api.auth.send_login_code_email')
    def test_email_delivery_failure_returns_bad_gateway_and_removes_code(self, send_email):
        from trivia_app.services.email_sender import EmailDeliveryError

        send_email.side_effect = EmailDeliveryError('Delivery failed')

        response = self.client.post(
            '/api/auth/request-code/',
            {'username': 'test-user', 'email': 'test.user@ssc-spc.gc.ca'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(
            response.data['detail'],
            'The login email could not be sent. Please try again later.',
        )
        self.assertFalse(EmailLoginCode.objects.exists())

    @patch('trivia_app.api.auth.send_login_code_email')
    def test_external_email_domain_cannot_register_or_receive_code(self, send_email):
        response = self.client.post(
            '/api/auth/request-code/',
            {'username': 'external-user', 'email': 'person@example.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data['email'],
            ['Use an SSC email address ending in @ssc-spc.gc.ca.'],
        )
        self.assertFalse(User.objects.filter(username='external-user').exists())
        self.assertFalse(EmailLoginCode.objects.exists())
        send_email.assert_not_called()

    def test_external_email_domain_cannot_verify_an_existing_code(self):
        user = User.objects.create_user(username='legacy-external', email='person@example.com')
        EmailLoginCode.objects.create(
            user=user,
            code_hash=make_password('123456'),
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        response = self.client.post(
            '/api/auth/verify-code/',
            {'email': 'person@example.com', 'code': '123456'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Token.objects.filter(user=user).exists())

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
        User.objects.create_user(username='existing-user', email='existing@example.com')
        response = self.client.patch('/api/auth/me/', {'username': 'EXISTING-USER'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response = self.client.patch('/api/auth/me/', {'username': 'himanshu-updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'himanshu-updated')
        self.assertEqual(self.client.get('/api/auth/me/').status_code, status.HTTP_200_OK)
        self.assertEqual(self.client.get('/api/auth/me/').data['username'], 'himanshu-updated')
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

        response = self.client.post('/api/master-cycles/', {
            'team': team_id,
            'master_username': self.admin.username,
            'topic': 'Invalid dates',
            'start_date': '2026-08-10',
            'end_date': '2026-08-09',
            'status': 'active',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('end_date', response.data)

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
        self.assertEqual(response.data['generation_method'], TriviaSession.GenerationMethod.AI)
        self.assertEqual(len(response.data['questions']), 1)
        self.assertIsNotNone(response.data['publish_at'])
        self.assertIsNotNone(response.data['close_at'])

        session = TriviaSession.objects.get(pk=response.data['id'])
        question_id = session.questions.get().id
        self.assertEqual(self.client.post(f'/api/trivia-sessions/{session.id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Ottawa',
        }, format='json').status_code, status.HTTP_201_CREATED)
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
        self.assertEqual(self.client.post(f'/api/trivia-sessions/{session.id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Ottawa',
        }, format='json').status_code, status.HTTP_409_CONFLICT)
        response = self.client.get(f'/api/trivia-sessions/{session.id}/')
        self.assertEqual(response.data['questions'][0]['correct_choice'], 'Ottawa')
        self.assertIsNone(response.data['questions'][0]['selected_choice'])
        self.assertFalse(response.data['questions'][0]['is_correct'])

    def test_platform_admin_can_create_blank_team_without_membership(self):
        self.authenticate(self.admin)
        response = self.client.post(
            '/api/teams/',
            {'name': 'Blank Team', 'approval_required': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        team = Team.objects.get(pk=response.data['id'])
        self.assertFalse(TeamMembership.objects.filter(team=team).exists())
        self.assertFalse(TeamMembership.objects.filter(team=team, user=self.admin).exists())

    def test_team_can_have_only_one_team_admin(self):
        team = Team.objects.create(name='Single Admin Team', slug='single-admin-team', created_by=self.admin)
        TeamMembership.objects.create(
            team=team,
            user=self.admin,
            role=TeamMembership.Role.TEAM_ADMIN,
            status=TeamMembership.Status.APPROVED,
        )
        candidate = User.objects.create_user(username='second-admin', email='second-admin@example.com')
        self.authenticate(self.admin)

        response = self.client.post(
            f'/api/teams/{team.id}/members/',
            {'user_id': candidate.id, 'role': TeamMembership.Role.TEAM_ADMIN},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['role'], ['A team can have only one team admin.'])
        self.assertFalse(TeamMembership.objects.filter(team=team, user=candidate).exists())

    def test_platform_admin_can_switch_team_admin(self):
        team = Team.objects.create(name='Transfer Team', slug='transfer-team', created_by=self.admin)
        current_admin = User.objects.create_user(username='current-admin', email='current-admin@example.com')
        replacement = User.objects.create_user(username='replacement-admin', email='replacement-admin@example.com')
        current_membership = TeamMembership.objects.create(
            team=team, user=current_admin, role=TeamMembership.Role.TEAM_ADMIN,
            status=TeamMembership.Status.APPROVED,
        )
        replacement_membership = TeamMembership.objects.create(
            team=team, user=replacement, role=TeamMembership.Role.MEMBER,
            status=TeamMembership.Status.APPROVED,
        )
        self.authenticate(self.admin)

        response = self.client.patch(
            f'/api/teams/{team.id}/members/{replacement_membership.id}/',
            {'role': TeamMembership.Role.TEAM_ADMIN},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        current_membership.refresh_from_db()
        replacement_membership.refresh_from_db()
        self.assertEqual(current_membership.role, TeamMembership.Role.MEMBER)
        self.assertEqual(replacement_membership.role, TeamMembership.Role.TEAM_ADMIN)

    def test_platform_admin_can_remove_their_own_team_membership(self):
        team = Team.objects.create(name='Self Removal Team', slug='self-removal-team', created_by=self.admin)
        membership = TeamMembership.objects.create(
            team=team,
            user=self.admin,
            role=TeamMembership.Role.TEAM_ADMIN,
            status=TeamMembership.Status.APPROVED,
        )
        self.authenticate(self.admin)

        response = self.client.delete(f'/api/teams/{team.id}/members/{membership.id}/')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(TeamMembership.objects.filter(pk=membership.id).exists())

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

        cycle_start = timezone.localdate()
        response = self.client.post('/api/master-cycles/', {
            'team': team['id'],
            'master_username': self.master.username,
            'topic': 'Space',
            'start_date': cycle_start.isoformat(),
            'end_date': (cycle_start + timedelta(days=13)).isoformat(),
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
        self.assertFalse(response.data['has_submitted'])
        response = self.client.post(f'/api/trivia-sessions/{session_id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Mars',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertTrue(response.data['has_submitted'])
        self.assertEqual(response.data['questions'][0]['selected_choice'], 'Mars')
        self.assertNotIn('correct_choice', response.data['questions'][0])

        self.authenticate(self.master)
        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertFalse(response.data['has_submitted'])
        response = self.client.post(f'/api/trivia-sessions/{session_id}/answers/', {
            'trivia_question': question_id,
            'selected_choice': 'Venus',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'The Trivia Master cannot answer trivia they created manually.')
        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertFalse(response.data['has_submitted'])
        response = self.client.post(f'/api/trivia-sessions/{session_id}/evaluate/')
        self.assertEqual(response.data['trophies_awarded'], 1)

        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertEqual(response.data['submission_count'], 1)
        player_submission = next(
            submission for submission in response.data['submissions']
            if submission['username'] == self.player.username
        )
        self.assertEqual(player_submission['answers_submitted'], 1)
        self.assertNotIn('selected_choice', player_submission)

        self.authenticate(self.player)
        response = self.client.get(f"/api/leaderboard/?team={team['id']}")
        self.assertEqual(response.data[0]['username'], self.player.username)
        self.assertEqual(response.data[0]['trophy_count'], 1)

        response = self.client.get(f'/api/trivia-sessions/{session_id}/')
        self.assertEqual(response.data['questions'][0]['correct_choice'], 'Mars')
        self.assertEqual(response.data['questions'][0]['selected_choice'], 'Mars')
        self.assertTrue(response.data['questions'][0]['is_correct'])
        self.assertEqual(response.data['questions'][0]['explanation'], 'Iron oxides make Mars appear red.')

        cycle = MasterCycle.objects.get(pk=cycle_id)
        cycle.start_date = timezone.localdate() - timedelta(days=14)
        cycle.end_date = timezone.localdate() - timedelta(days=1)
        cycle.save(update_fields=['start_date', 'end_date'])
        response = self.client.get('/api/notifications/')
        winner_message = 'Cycle "Space" winner: player with 1 trophy!'
        self.assertEqual(response.data[0]['message'], winner_message)
        cycle.refresh_from_db()
        self.assertEqual(cycle.status, MasterCycle.Status.CLOSED)
        self.assertEqual(
            Notification.objects.filter(user=self.player, message=winner_message).count(),
            1,
        )
        self.client.get('/api/notifications/')
        self.assertEqual(
            Notification.objects.filter(user=self.player, message=winner_message).count(),
            1,
        )
        self.assertTrue(Notification.objects.filter(user=self.master, message=winner_message).exists())

        self.assertEqual(self.client.get('/api/admin/overview/').status_code, status.HTTP_403_FORBIDDEN)
        self.authenticate(self.admin)
        response = self.client.get('/api/admin/overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        overview_team = next(item for item in response.data['teams'] if item['id'] == team['id'])
        self.assertEqual(len(overview_team['members']), 3)
        self.assertEqual(overview_team['trivia_sessions'][0]['title'], 'Space Basics')
        self.assertIn(
            self.player.username,
            {
                submission['username']
                for submission in overview_team['trivia_sessions'][0]['submissions']
            },
        )
        self.assertEqual(overview_team['leaderboard'][0]['username'], self.player.username)
        response = self.client.get('/api/leaderboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['username'], self.player.username)
        self.assertEqual(response.data[0]['trophy_count'], 1)

    def test_leaderboard_uses_earliest_correct_answer_as_tiebreaker(self):
        faster_player = User.objects.create_user(username='faster-player', email='fast@example.com')
        team = Team.objects.create(name='Ranking Team', slug='ranking-team', created_by=self.admin)
        for user in (self.player, faster_player):
            TeamMembership.objects.create(
                team=team,
                user=user,
                status=TeamMembership.Status.APPROVED,
            )
        cycle = MasterCycle.objects.create(
            team=team,
            master=self.master,
            topic='Ranking',
            start_date=timezone.localdate(),
            end_date=timezone.localdate(),
            status=MasterCycle.Status.CLOSED,
        )
        session = TriviaSession.objects.create(
            master_cycle=cycle,
            title='Ranking question',
            topic='Ranking',
            status=TriviaSession.Status.CLOSED,
            close_at=timezone.now(),
        )
        now = timezone.now()
        TrophyAward.objects.create(trivia_session=session, user=self.player, answered_at=now)
        TrophyAward.objects.create(
            trivia_session=session,
            user=faster_player,
            answered_at=now - timedelta(seconds=10),
        )

        self.authenticate(self.player)
        response = self.client.get(f'/api/leaderboard/?team={team.id}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [entry['username'] for entry in response.data],
            [faster_player.username, self.player.username],
        )

    @override_settings(TRIVIA_QUESTION_RETENTION_DAYS=17)
    def test_question_cleanup_preserves_cycle_ranking_and_limits_user_history(self):
        team = Team.objects.create(name='History Team', slug='history-team', created_by=self.admin)
        TeamMembership.objects.create(
            team=team,
            user=self.player,
            status=TeamMembership.Status.APPROVED,
        )
        cycles = []
        for days_ago in range(4):
            day = timezone.localdate() - timedelta(days=days_ago)
            cycles.append(MasterCycle.objects.create(
                team=team,
                master=self.master,
                topic=f'Cycle {days_ago}',
                start_date=day,
                end_date=day,
                status=MasterCycle.Status.CLOSED,
            ))
        old_session = TriviaSession.objects.create(
            master_cycle=cycles[-1],
            title='Expired question details',
            topic='History',
            status=TriviaSession.Status.CLOSED,
            close_at=timezone.now() - timedelta(days=18),
        )
        question = TriviaQuestion.objects.create(
            trivia_session=old_session,
            prompt='Old question',
            choices=['A', 'B'],
            correct_choice='A',
        )
        answer = UserAnswer.objects.create(
            trivia_session=old_session,
            trivia_question=question,
            user=self.player,
            selected_choice='A',
            is_correct=True,
        )
        trophy = TrophyAward.objects.create(
            trivia_session=old_session,
            user=self.player,
            answered_at=answer.submitted_at,
        )

        self.authenticate(self.player)
        response = self.client.get('/api/master-cycles/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        self.assertFalse(TriviaQuestion.objects.filter(pk=question.pk).exists())
        self.assertFalse(UserAnswer.objects.filter(pk=answer.pk).exists())
        self.assertTrue(TriviaSession.objects.filter(pk=old_session.pk).exists())
        self.assertTrue(MasterCycle.objects.filter(pk=cycles[-1].pk).exists())
        self.assertTrue(TrophyAward.objects.filter(pk=trophy.pk).exists())

        self.authenticate(self.admin)
        response = self.client.get('/api/master-cycles/')
        self.assertEqual(len(response.data), 4)
        old_cycle = next(item for item in response.data if item['id'] == cycles[-1].id)
        self.assertEqual(old_cycle['sprint_leaderboard'][0]['username'], self.player.username)
