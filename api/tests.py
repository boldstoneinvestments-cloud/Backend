from io import StringIO
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
import time

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.core import signing
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase
from django_otp.oath import TOTP
from django_otp.plugins.otp_totp.models import TOTPDevice
from api.admin_cache import get_admin_cache, set_admin_cache
from api.models import AdminActivity, AdminPresence, AdminRecoveryCodes, ChatMessage, Order
from api.views import customer_token
from email_service import queue_password_reset_email, send_password_reset_email
from shop.models import Product as ShopProduct


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

    @patch.dict('os.environ', {
        'RESEND_API_KEY': 'test-api-key',
        'RESEND_FROM_EMAIL': 'reset@example.com',
    })
    @patch('email_service._PASSWORD_RESET_EMAIL_EXECUTOR.submit')
    def test_password_reset_email_is_queued_without_waiting(self, submit):
        reset_url = 'https://www.boldstoneinvestments.com/account/password-reset/confirm/uid/token'

        queued = queue_password_reset_email(self.customer, reset_url)

        self.assertTrue(queued)
        submit.assert_called_once_with(send_password_reset_email, self.customer, reset_url)

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
        self.assertEqual(device.step, 30)
        timestamp = int(time.time()) + 60

        verified = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)

        self.assertEqual(verified.status_code, 200)
        self.assertTrue(TOTPDevice.objects.get(pk=device.pk).confirmed)
        self.assertEqual(len(verified.json()['recovery_codes']), 10)
        self.assertEqual(self.client.get('/api/admin/session').json()['identity']['name'], 'SSEMATA SABIRA')

    def test_admin_login_requires_brand_new_identity_selection_after_password(self):
        self.authenticate_admin_with_totp('MOSES ALICWAMU')
        self.client.logout()

        response = self.client.post(
            '/api/admin/login',
            {'username': self.admin.username, 'password': 'old-admin-password'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['identity_selection_required'])
        self.assertNotIn('pending_identity', response.json())
        self.assertNotIn('two_factor_required', response.json())
        self.assertEqual(len(response.json()['identities']), 3)

        selected = self.client.post(
            '/api/admin/identity',
            {'identity_name': 'MOSES ALICWAMU'},
            content_type='application/json',
        )

        self.assertEqual(selected.status_code, 200)
        self.assertTrue(selected.json()['two_factor_required'])
        self.assertFalse(selected.json()['setup_required'])

        device = TOTPDevice.objects.get(user=self.admin, name='admin:MOSES ALICWAMU')
        timestamp = int(time.time()) + 120
        verified = self.verify_admin_code(self.totp_code(device, timestamp), timestamp)
        self.assertEqual(verified.status_code, 200)
        self.assertEqual(self.client.get('/api/admin/session').json()['identity']['name'], 'MOSES ALICWAMU')

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

    def test_existing_admin_totp_device_uses_thirty_second_interval(self):
        TOTPDevice.objects.create(
            user=self.admin,
            name='admin:SSEMATA SABIRA',
            confirmed=True,
            step=15,
            digits=6,
        )

        selected = self.start_admin_identity_setup('SSEMATA SABIRA')

        self.assertFalse(selected.json()['setup_required'])
        device = TOTPDevice.objects.get(user=self.admin, name='admin:SSEMATA SABIRA')
        self.assertEqual(device.step, 30)

    def test_reset_admin_two_factor_only_removes_selected_identity(self):
        TOTPDevice.objects.get_or_create(
            user=self.admin,
            name='admin:SSEMATA SABIRA',
            defaults={'confirmed': True, 'step': 15, 'digits': 6},
        )
        TOTPDevice.objects.get_or_create(
            user=self.admin,
            name='admin:MOSES ALICWAMU',
            defaults={'confirmed': True, 'step': 15, 'digits': 6},
        )
        recovery = AdminRecoveryCodes.objects.create(
            user=self.admin,
            identity_code_hashes={
                'SSEMATA SABIRA': ['ssemata-hash'],
                'MOSES ALICWAMU': ['moses-hash'],
            },
        )

        call_command('reset_admin_two_factor', 'SSEMATA SABIRA', stdout=StringIO())

        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin, name='admin:SSEMATA SABIRA').exists())
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, name='admin:MOSES ALICWAMU').exists())
        recovery.refresh_from_db()
        self.assertEqual(recovery.identity_code_hashes, {'MOSES ALICWAMU': ['moses-hash']})

    def test_deploy_migration_resets_only_ssemata_two_factor(self):
        TOTPDevice.objects.create(
            user=self.admin,
            name='admin:SSEMATA SABIRA',
            confirmed=True,
            step=15,
            digits=6,
        )
        TOTPDevice.objects.create(
            user=self.admin,
            name='admin:MOSES ALICWAMU',
            confirmed=True,
            step=30,
            digits=6,
        )
        recovery = AdminRecoveryCodes.objects.create(
            user=self.admin,
            identity_code_hashes={
                'SSEMATA SABIRA': ['ssemata-hash'],
                'MOSES ALICWAMU': ['moses-hash'],
            },
        )
        migration = import_module('api.migrations.0013_reset_ssemata_two_factor')
        migration_apps = MigrationExecutor(connection).loader.project_state(
            [('api', '0013_reset_ssemata_two_factor')],
        ).apps

        migration.reset_ssemata_two_factor(
            migration_apps,
            SimpleNamespace(connection=connection),
        )

        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin, name='admin:SSEMATA SABIRA').exists())
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, name='admin:MOSES ALICWAMU').exists())
        recovery.refresh_from_db()
        self.assertEqual(recovery.identity_code_hashes, {'MOSES ALICWAMU': ['moses-hash']})

    def test_followup_deploy_migration_resets_only_moses_and_habib_two_factor(self):
        for identity_name in ('SSEMATA SABIRA', 'MOSES ALICWAMU', 'HABIB TUMWESIGE'):
            TOTPDevice.objects.create(
                user=self.admin,
                name=f'admin:{identity_name}',
                confirmed=True,
                step=30,
                digits=6,
            )
        recovery = AdminRecoveryCodes.objects.create(
            user=self.admin,
            identity_code_hashes={
                'SSEMATA SABIRA': ['ssemata-hash'],
                'MOSES ALICWAMU': ['moses-hash'],
                'HABIB TUMWESIGE': ['habib-hash'],
            },
        )
        migration = import_module('api.migrations.0014_reset_moses_habib_two_factor')
        migration_apps = MigrationExecutor(connection).loader.project_state(
            [('api', '0014_reset_moses_habib_two_factor')],
        ).apps

        migration.reset_moses_habib_two_factor(
            migration_apps,
            SimpleNamespace(connection=connection),
        )

        self.assertTrue(User.objects.filter(pk=self.admin.pk).exists())
        self.assertTrue(TOTPDevice.objects.filter(user=self.admin, name='admin:SSEMATA SABIRA').exists())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin, name='admin:MOSES ALICWAMU').exists())
        self.assertFalse(TOTPDevice.objects.filter(user=self.admin, name='admin:HABIB TUMWESIGE').exists())
        recovery.refresh_from_db()
        self.assertEqual(recovery.identity_code_hashes, {'SSEMATA SABIRA': ['ssemata-hash']})

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

    @patch('api.views.queue_password_reset_email', return_value=True)
    def test_google_customer_can_reset_password_with_email_link(self, queue_reset_email):
        self.customer.set_unusable_password()
        self.customer.save(update_fields=['password'])
        response = self.client.post(
            '/api/account/password-reset',
            {'email': self.customer.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        reset_url = queue_reset_email.call_args.args[1]
        _, _, _, _, uid, token = reset_url.rsplit('/', 5)
        confirmation = self.client.post(
            '/api/account/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'new-customer-password'},
            content_type='application/json',
        )

        self.assertEqual(confirmation.status_code, 200)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('new-customer-password'))

    @patch('api.views.queue_password_reset_email', return_value=True)
    def test_admin_reset_is_role_scoped_and_token_is_single_use(self, queue_reset_email):
        self.admin.set_unusable_password()
        self.admin.save(update_fields=['password'])
        response = self.client.post(
            '/api/admin/password-reset',
            {'email': self.admin.email},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        reset_url = queue_reset_email.call_args.args[1]
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

    @patch('api.admin_views.queue_password_reset_email', return_value=True)
    def test_verified_admin_queues_customer_reset_email(self, queue_reset_email):
        self.authenticate_admin_with_totp()

        response = self.client.post(
            f'/api/admin/customers/{self.customer.pk}/password-reset-link',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['email_queued'])
        reset_url = queue_reset_email.call_args.args[1]
        self.assertTrue(reset_url.startswith('https://www.boldstoneinvestments.com/account/password-reset/confirm/'))
        _, _, _, _, uid, token = reset_url.rsplit('/', 5)
        confirmation = self.client.post(
            '/api/account/password-reset/confirm',
            {'uid': uid, 'token': token, 'password': 'new-customer-password'},
            content_type='application/json',
        )

        self.assertEqual(confirmation.status_code, 200)
        self.customer.refresh_from_db()
        self.assertTrue(self.customer.check_password('new-customer-password'))

    @patch('api.admin_views.queue_password_reset_email', return_value=False)
    def test_customer_gets_copyable_reset_link_when_email_delivery_fails(self, send_reset_email):
        self.authenticate_admin_with_totp()

        response = self.client.post(
            f'/api/admin/customers/{self.customer.pk}/password-reset-link',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['email_queued'])
        self.assertIn('reset_url', response.json())
        send_reset_email.assert_called_once()

    @patch('api.admin_views.queue_password_reset_email')
    def test_invalid_customer_email_skips_email_and_returns_copyable_link(self, queue_reset_email):
        self.authenticate_admin_with_totp()
        self.customer.email = 'not-an-email'
        self.customer.save(update_fields=['email'])

        response = self.client.post(
            f'/api/admin/customers/{self.customer.pk}/password-reset-link',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['email_queued'])
        self.assertIn('reset_url', response.json())
        queue_reset_email.assert_not_called()

    def test_customer_reset_link_requires_verified_admin(self):
        response = self.client.post(
            f'/api/admin/customers/{self.customer.pk}/password-reset-link',
        )

        self.assertEqual(response.status_code, 401)

    def test_customer_reset_link_rejects_contacts_without_accounts(self):
        self.authenticate_admin_with_totp()
        response = self.client.post('/api/admin/customers/999999/password-reset-link')

        self.assertEqual(response.status_code, 404)

    def test_admin_can_sign_out_customer_sessions_and_bearer_tokens(self):
        customer_client = Client()
        customer_client.force_login(self.customer)
        old_token = customer_token(self.customer)
        token_response = self.client.get('/api/account/me', HTTP_AUTHORIZATION=f'Bearer {old_token}')
        session_response = customer_client.get('/api/account/me')
        self.assertTrue(token_response.json()['authenticated'])
        self.assertTrue(session_response.json()['authenticated'])
        self.authenticate_admin_with_totp()

        response = self.client.post(f'/api/admin/customers/{self.customer.pk}/logout')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.client.get('/api/account/me', HTTP_AUTHORIZATION=f'Bearer {old_token}').json()['authenticated'])
        self.assertFalse(customer_client.get('/api/account/me').json()['authenticated'])
        self.assertTrue(self.customer.check_password('old-customer-password'))
        new_token = customer_token(self.customer)
        self.assertTrue(self.client.get('/api/account/me', HTTP_AUTHORIZATION=f'Bearer {new_token}').json()['authenticated'])

    def test_verified_admin_can_create_and_edit_shop_products_and_details(self):
        self.authenticate_admin_with_totp()
        product_data = {
            'id': 'admin-product',
            'category': 'roasted',
            'name': 'Admin Added Roast',
            'price': 25000,
            'unit': 'per bag',
            'image': 'https://example.com/roast.jpg',
            'description': 'Freshly roasted coffee.',
            'badge': 'New',
            'varieties': [],
            'details': {'Roast level': 'Medium', 'Origin': 'Uganda'},
            'active': True,
        }

        created = self.client.post('/api/admin/shop/products', product_data, content_type='application/json')

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()['product']['details']['Origin'], 'Uganda')
        edit_data = self.client.get('/api/admin/shop/products/admin-product')
        self.assertEqual(edit_data.status_code, 200)
        self.assertEqual(edit_data.json()['product']['varieties'], [])
        self.assertEqual(edit_data.json()['product']['details']['Origin'], 'Uganda')
        public_products = self.client.get('/api/shop/products').json()
        public_product = next(product for product in public_products['roasted'] if product['id'] == 'admin-product')
        self.assertEqual(public_product['details']['Roast level'], 'Medium')

        product_data.update({
            'name': 'Updated Admin Roast',
            'active': False,
            'details': {'Roast level': 'Dark', 'Process': 'Washed'},
        })
        updated = self.client.put(
            '/api/admin/shop/products/admin-product',
            product_data,
            content_type='application/json',
        )

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['product']['name'], 'Updated Admin Roast')
        self.assertFalse(ShopProduct.objects.get(pk='admin-product').active)
        public_products = self.client.get('/api/shop/products').json()
        self.assertNotIn('admin-product', [product['id'] for product in public_products['roasted']])

    @patch.dict('os.environ', {
        'CLOUDINARY_CLOUD_NAME': 'boldstone-test',
        'CLOUDINARY_API_KEY': 'public-test-key',
        'CLOUDINARY_API_SECRET': 'private-test-secret',
    })
    @patch('api.admin_views.api_sign_request', return_value='short-lived-signature')
    def test_verified_admin_can_request_cloudinary_upload_signature(self, sign_request):
        self.authenticate_admin_with_totp()

        response = self.client.post('/api/admin/shop/products/upload-signature')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['cloud_name'], 'boldstone-test')
        self.assertEqual(response.json()['api_key'], 'public-test-key')
        self.assertEqual(response.json()['folder'], 'boldstone/products')
        self.assertEqual(response.json()['signature'], 'short-lived-signature')
        self.assertNotIn('api_secret', response.json())
        sign_request.assert_called_once_with(
            {'folder': 'boldstone/products', 'timestamp': response.json()['timestamp']},
            'private-test-secret',
        )

    @patch.dict('os.environ', {
        'CLOUDINARY_CLOUD_NAME': '',
        'CLOUDINARY_API_KEY': '',
        'CLOUDINARY_API_SECRET': '',
    })
    def test_cloudinary_signature_reports_missing_railway_variables(self):
        self.authenticate_admin_with_totp()
        response = self.client.post('/api/admin/shop/products/upload-signature')

        self.assertEqual(response.status_code, 503)

    def test_admin_customer_list_defers_record_details_until_selected(self):
        self.authenticate_admin_with_totp()
        Order.objects.create(
            name='Customer Example',
            phone='555-0100',
            email=self.customer.email,
            product='Coffee seedlings',
            quantity=2,
            location='Kyenjojo',
            notes='Order details should load on demand.',
        )

        summary_response = self.client.get('/api/admin/customers')
        summary = next(customer for customer in summary_response.json()['customers'] if customer['email'] == self.customer.email)
        details_response = self.client.get(f'/api/admin/customers?email={self.customer.email}')
        details = next(customer for customer in details_response.json()['customers'] if customer['email'] == self.customer.email)

        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary['records'], [])
        self.assertIn('Order page', summary['sources'])
        self.assertEqual(details_response.status_code, 200)
        self.assertEqual(len(details['records']), 2)
        self.assertEqual(details['records'][1]['details']['notes'], 'Order details should load on demand.')

    def test_admin_chat_cache_is_reused_and_invalidated_after_message_write(self):
        self.authenticate_admin_with_totp()
        cache.clear()
        set_admin_cache('admin_chat', {'messages': []})

        cached_response = self.client.get('/api/admin/chat')

        self.assertEqual(cached_response.json(), {'messages': []})
        self.assertIsNotNone(get_admin_cache('admin_chat'))
        ChatMessage.objects.create(
            user=self.customer,
            name=self.customer.get_full_name(),
            email=self.customer.email,
            message='New message invalidates cached chat.',
        )

        self.assertIsNone(get_admin_cache('admin_chat'))
        refreshed_response = self.client.get('/api/admin/chat')
        self.assertEqual(refreshed_response.json()['messages'][0]['message'], 'New message invalidates cached chat.')
        self.assertEqual(get_admin_cache('customer_chat', scope=str(self.customer.pk)), None)

    @patch('api.views.queue_password_reset_email')
    def test_unknown_email_gets_generic_response_without_queueing_mail(self, queue_reset_email):
        response = self.client.post(
            '/api/account/password-reset',
            {'email': 'unknown@example.com'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('If an account matches', response.json()['message'])
        queue_reset_email.assert_not_called()

    @patch.dict('os.environ', {
        'GOOGLE_CLIENT_ID': 'client-id',
        'GOOGLE_REDIRECT_URI': 'https://backend.example.com/api/account/google/callback',
    })
    def test_admin_google_start_signs_admin_flow(self):
        response = self.client.get('/api/admin/google/start')
        state = parse_qs(urlparse(response['Location']).query)['state'][0]

        self.assertEqual(response.status_code, 302)
        self.assertEqual(signing.loads(state, salt='google-oauth-state')['flow'], 'admin')