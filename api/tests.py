from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import time

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from api.models import AdminActivity, AdminPresence, ChatMessage


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

    def totp_code(self, device, timestamp):
        totp = TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift)
        totp.time = timestamp
        return str(totp.token()).zfill(device.digits)

    def verify_admin_code(self, code, timestamp):
        with patch('django_otp.plugins.otp_totp.models.time.time', return_value=timestamp):
            return self.client.post(
                '/api/admin/2fa/verify',
                {'token': code},
                content_type='application/json',
            )

    def start_admin_identity_setup(self, identity_name):
        login_response = self.client.post(
            '/api/admin/login',
            {'username': self.admin.username, 'password': 'old-admin-password'},
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        return self.client.post(
            '/api/admin/identity',
            {'identity_name': identity_name},
            content_type='application/json',
        )

    def authenticate_admin_with_totp(self, identity_name='SSEMATA SABIRA'):
        setup = self.start_admin_identity_setup(identity_name)
        self.assertTrue(setup.json()['setup_required'])
        device = TOTPDevice.objects.get(user=self.admin, name=f'admin:{identity_name}')
        timestamp = int(time.time()) + 60
        response = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)
        self.assertEqual(response.status_code, 200)
        return response

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': 'test-secret'})
    @patch('api.views.verify_recaptcha', return_value=False)
    def test_signup_rejects_unverified_recaptcha(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-up',
            {
                'name': 'New Customer',
                'email': 'new@example.com',
                'password': 'valid-password',
                'recaptcha_token': 'invalid-token',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email='new@example.com').exists())
        verify_captcha.assert_called_once()

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': 'test-secret'})
    @patch('api.views.verify_recaptcha', return_value=True)
    def test_signup_creates_account_only_after_recaptcha_verifies(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-up',
            {
                'name': 'New Customer',
                'email': 'new@example.com',
                'password': 'valid-password',
                'recaptcha_token': 'verified-token',
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(User.objects.filter(email='new@example.com').exists())
        verify_captcha.assert_called_once()

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': ''})
    @patch('api.views.verify_recaptcha')
    def test_signup_fails_closed_when_recaptcha_secret_is_missing(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-up',
            {'name': 'New Customer', 'email': 'new@example.com', 'password': 'valid-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        verify_captcha.assert_not_called()

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': 'test-secret'})
    @patch('api.views.verify_recaptcha', return_value=False)
    def test_signin_rejects_unverified_recaptcha(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-in',
            {'email': self.customer.email, 'password': 'old-customer-password', 'recaptcha_token': 'invalid-token'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 400)
        verify_captcha.assert_called_once()

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': 'test-secret'})
    @patch('api.views.verify_recaptcha', return_value=True)
    def test_signin_succeeds_after_recaptcha_verifies(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-in',
            {'email': self.customer.email, 'password': 'old-customer-password', 'recaptcha_token': 'verified-token'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['email'], self.customer.email)
        verify_captcha.assert_called_once()

    @patch.dict('os.environ', {'RECAPTCHA_SECRET_KEY': ''})
    @patch('api.views.verify_recaptcha')
    def test_signin_fails_closed_when_recaptcha_secret_is_missing(self, verify_captcha):
        response = self.client.post(
            '/api/account/sign-in',
            {'email': self.customer.email, 'password': 'old-customer-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 503)
        verify_captcha.assert_not_called()

    def test_admin_session_and_api_require_staff(self):
        self.assertEqual(self.client.get('/api/admin/session').status_code, 401)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 401)

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/api/admin/session').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 403)

        login_response = self.client.post(
            '/api/admin/login',
            {'username': self.admin.username, 'password': 'old-admin-password'},
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.json()['identity_selection_required'])
        self.assertEqual(len(login_response.json()['identities']), 3)
        session = self.client.get('/api/admin/session')
        self.assertEqual(session.status_code, 200)
        self.assertTrue(session.json()['authenticated'])
        self.assertIsNone(session.json()['identity'])
        self.assertEqual(self.client.get('/api/admin/users').status_code, 401)
        setup = self.start_admin_identity_setup('SSEMATA SABIRA')
        self.assertTrue(setup.json()['setup_required'])
        device = TOTPDevice.objects.get(user=self.admin, name='admin:SSEMATA SABIRA')
        timestamp = int(time.time()) + 60
        verified = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 200)

    def test_admin_totp_enrollment_and_recovery_codes(self):
        setup = self.start_admin_identity_setup('SSEMATA SABIRA')
        self.assertTrue(setup.json()['setup_required'])
        self.assertTrue(setup.json()['provisioning_uri'].startswith('otpauth://totp/'))
        device = TOTPDevice.objects.get(user=self.admin, name='admin:SSEMATA SABIRA')
        timestamp = int(time.time()) + 60

        verified = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)

        self.assertEqual(verified.status_code, 200)
        self.assertTrue(TOTPDevice.objects.get(pk=device.pk).confirmed)
        self.assertEqual(len(verified.json()['recovery_codes']), 10)
        self.assertEqual(self.client.get('/api/admin/session').json()['identity']['name'], 'SSEMATA SABIRA')

    def test_each_admin_identity_requires_independent_totp_setup(self):
        for index, identity_name in enumerate(('SSEMATA SABIRA', 'MOSES ALICWAMU', 'HABIB TUMWESIGE')):
            if index == 0:
                setup = self.start_admin_identity_setup(identity_name)
            else:
                setup = self.client.post(
                    '/api/admin/identity',
                    {'identity_name': identity_name},
                    content_type='application/json',
                )
            self.assertEqual(setup.status_code, 200)
            self.assertTrue(setup.json()['setup_required'], identity_name)
            device = TOTPDevice.objects.get(user=self.admin, name=f'admin:{identity_name}')
            timestamp = int(time.time()) + 60 + index * 30
            verified = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)
            self.assertEqual(verified.status_code, 200, identity_name)
            self.assertEqual(verified.json()['identity_name'], identity_name)

        self.assertEqual(TOTPDevice.objects.filter(user=self.admin, confirmed=True).count(), 3)

    def test_admin_recovery_code_is_hashed_and_single_use(self):
        enrollment = self.authenticate_admin_with_totp()
        recovery_code = enrollment.json()['recovery_codes'][0]
        recovery = self.admin.admin_recovery_codes
        self.assertTrue(all(value.startswith('hmac-sha256$') for value in recovery.identity_code_hashes['SSEMATA SABIRA']))
        self.client.logout()

        selected = self.start_admin_identity_setup('SSEMATA SABIRA')
        self.assertFalse(selected.json()['setup_required'])
        verified = self.client.post(
            '/api/admin/2fa/verify',
            {'recovery_code': recovery_code},
            content_type='application/json',
        )
        self.assertEqual(verified.status_code, 200)

        self.client.logout()
        self.start_admin_identity_setup('SSEMATA SABIRA')
        reused = self.client.post(
            '/api/admin/2fa/verify',
            {'recovery_code': recovery_code},
            content_type='application/json',
        )
        self.assertEqual(reused.status_code, 400)

    def test_selected_identity_stamps_chat_and_page_activity(self):
        self.authenticate_admin_with_totp('SSEMATA SABIRA')
        reply = self.client.post(
            '/api/admin/chat/reply',
            {
                'name': 'Customer Example',
                'email': self.customer.email,
                'message': 'A reply from the selected profile.',
                'admin_name': 'HABIB TUMWESIGE',
            },
            content_type='application/json',
        )
        self.assertEqual(reply.status_code, 201)
        saved_reply = ChatMessage.objects.get(is_admin=True)
        self.assertEqual(saved_reply.admin_name, 'SSEMATA SABIRA')

        self.client.post('/api/admin/presence', {'page': '/admin/orders'}, content_type='application/json')
        self.client.post('/api/admin/presence', {'page': '/admin/chat'}, content_type='application/json')
        presence = AdminPresence.objects.get(user=self.admin)
        self.assertEqual(presence.current_page, '/admin/chat')
        self.assertEqual(presence.last_page, '/admin/orders')
        self.assertTrue(AdminActivity.objects.filter(action='Replied to chat', identity_name='SSEMATA SABIRA').exists())
        page_events = AdminActivity.objects.filter(action='Viewed admin page', actor=self.admin)
        self.assertEqual(page_events.count(), 2)
        activity_response = self.client.get('/api/admin/activity')
        self.assertEqual(activity_response.status_code, 200)
        admin_presence = activity_response.json()['admins'][0]
        self.assertEqual(admin_presence['last_visited_page'], '/admin/chat')

    def test_blog_actions_are_recorded_for_selected_identity(self):
        self.authenticate_admin_with_totp('MOSES ALICWAMU')
        response = self.client.post(
            '/api/admin/activity',
            {'action': 'blog.post.created', 'target_id': 27, 'details': {'title': 'Coffee update'}, 'page': '/admin/blog'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        event = AdminActivity.objects.get(action='Created blog post')
        self.assertEqual(event.identity_name, 'MOSES ALICWAMU')
        self.assertEqual(event.actor, self.admin)
        self.assertEqual(event.details['title'], 'Coffee update')

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