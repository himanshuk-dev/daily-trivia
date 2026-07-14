import re

from django.core import mail
from django.test import override_settings
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
