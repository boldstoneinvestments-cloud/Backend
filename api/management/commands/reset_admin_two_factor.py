from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django_otp.plugins.otp_totp.models import TOTPDevice

from api.models import AdminRecoveryCodes


ADMIN_IDENTITIES = (
    'SSEMATA SABIRA',
    'MOSES ALICWAMU',
    'HABIB TUMWESIGE',
)


class Command(BaseCommand):
    help = 'Reset one admin identity\'s authenticator enrollment and recovery codes.'

    def add_arguments(self, parser):
        parser.add_argument('identity_name', choices=ADMIN_IDENTITIES)

    def handle(self, *args, **options):
        identity_name = options['identity_name']
        active_staff = get_user_model().objects.filter(is_active=True, is_staff=True)

        with transaction.atomic():
            device_count, _ = TOTPDevice.objects.filter(
                user__in=active_staff,
                name=f'admin:{identity_name}',
            ).delete()

            recovery_count = 0
            for recovery in AdminRecoveryCodes.objects.filter(user__in=active_staff):
                hashes = recovery.identity_code_hashes or {}
                if identity_name in hashes:
                    hashes.pop(identity_name)
                    recovery.identity_code_hashes = hashes
                    recovery.save(update_fields=['identity_code_hashes'])
                    recovery_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Reset {identity_name}: removed {device_count} authenticator device(s) '
            f'and cleared {recovery_count} recovery record(s).'
        ))