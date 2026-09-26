from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
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

    def test_admin_session_and_api_require_staff(self):
        self.assertEqual(self.client.get('/api/admin/session').status_code, 401)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 401)

        self.client.force_login(self.customer)
        self.assertEqual(self.client.get('/api/admin/session').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 403)

        self.client.force_login(self.admin)
        session = self.client.get('/api/admin/session')
        self.assertEqual(session.status_code, 200)
        self.assertTrue(session.json()['authenticated'])
        self.assertEqual(self.client.get('/api/admin/users').status_code, 409)
        identity = self.client.post(
            '/api/admin/identity',
            {'identity_name': 'SSEMATA SABIRA'},
            content_type='application/json',
        )
        self.assertEqual(identity.status_code, 200)
        self.assertEqual(self.client.get('/api/admin/users').status_code, 200)

    def test_selected_identity_stamps_chat_and_page_activity(self):
        self.client.force_login(self.admin)
        identity = self.client.post(
            '/api/admin/identity',
            {'identity_name': 'SSEMATA SABIRA'},
            content_type='application/json',
        )
        self.assertEqual(identity.status_code, 200)
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
        self.client.force_login(self.admin)
        self.client.post('/api/admin/identity', {'identity_name': 'MOSES ALICWAMU'}, content_type='application/json')
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