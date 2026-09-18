import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create the Django admin account from ADMIN_USERNAME, ADMIN_EMAIL, and ADMIN_PASSWORD.'

    def handle(self, *args, **options):
        username = os.getenv('ADMIN_USERNAME', '').strip()
        email = os.getenv('ADMIN_EMAIL', '').strip()
        password = os.getenv('ADMIN_PASSWORD', '')

        if not username or not password:
            self.stdout.write('ADMIN_USERNAME or ADMIN_PASSWORD is not set; skipping admin creation.')
            return

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={'email': email, 'is_staff': True, 'is_superuser': True},
        )
        if created:
            user.set_password(password)
            user.save(update_fields=('password',))
            self.stdout.write(self.style.SUCCESS(f'Created admin user: {username}'))
            return

        changed = False
        user.set_password(password)
        changed = True
        if email and user.email != email:
            user.email = email
            changed = True
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            changed = True
        if changed:
            user.save(update_fields=('email', 'is_staff', 'is_superuser'))
        self.stdout.write(f'Admin user already exists: {username}')