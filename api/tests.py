from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase


User = get_user_model()


class PasswordResetTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(
            username='customer@example.com',
            email='customer@example.com',
            password='old-customer-password',
        )
        self.admin = User.objects.create_user(
            username='admin@example.com',
            email='admin@example.com',
            password='old-admin-password',
            is_staff=True,
        )

    @patch('api.views.send_password_reset_email', return_value=True)
    def test_customer_can_reset_password_with_email_link(self, send_reset_email):
        response = self.client.post(
            '/api/account/password-reset',
            {'email': self.customer.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        reset_url = send_reset_email.call_args.args[1]
        _, _, _, _, uid, token = reset_url.rsplit('/', 5)
        confirmation = self.client.post(
            '/api/account/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'new-customer-password'},
            content_type='application/json',
        )

        self.assertEqual(confirmation.status_code, 200)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('new-customer-password'))

    @patch('api.views.send_password_reset_email', return_value=True)
    def test_admin_reset_is_role_scoped_and_token_is_single_use(self, send_reset_email):
        response = self.client.post(
            '/api/admin/password-reset',
            {'email': self.admin.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        reset_url = send_reset_email.call_args.args[1]
        _, _, _, _, uid, token = reset_url.rsplit('/', 5)
        wrong_role = self.client.post(
            '/api/account/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'new-admin-password'},
            content_type='application/json',
        )
        self.assertEqual(wrong_role.status_code, 400)

        confirmation = self.client.post(
            '/api/admin/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'new-admin-password'},
            content_type='application/json',
        )
        self.assertEqual(confirmation.status_code, 200)
        second_use = self.client.post(
            '/api/admin/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'another-admin-password'},
            content_type='application/json',
        )

        self.assertEqual(second_use.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('new-admin-password'))

    @patch('api.views.send_password_reset_email')
    def test_unknown_email_gets_generic_response_without_sending_mail(self, send_reset_email):
        response = self.client.post(
            '/api/account/password-reset',
            {'email': 'unknown@example.com'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('If an account matches', response.json()['message'])
        send_reset_email.assert_not_called()

    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'client-id',
        'GOOGLE_REDIRECT_URI': 'https://backend.example.com/api/account/google/callback',
    })
    def test_admin_google_start_signs_admin_flow(self):
        response = self.client.get('/api/admin/google/start')
        state = parse_qs(urlparse(response['Location']).query)['state'][0]

        self.assertEqual(response.status_code, 302)
        self.assertEqual(signing.loads(state, salt='google-oauth-state')['flow'], 'admin')