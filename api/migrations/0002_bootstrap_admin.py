import os

from django.db import migrations


def create_admin(apps, schema_editor):
    username = os.getenv('ADMIN_USERNAME', '').strip()
    email = os.getenv('ADMIN_EMAIL', '').strip()
    password = os.getenv('ADMIN_PASSWORD', '')
    if not username or not password:
        return

    User = apps.get_model('auth', 'User')
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'is_staff': True,
            'is_superuser': True,
        },
    )
    if created:
        user.set_password(password)
        user.save(update_fields=['password'])
    else:
        fields = []
        user.set_password(password)
        fields.append('password')
        if email and user.email != email:
            user.email = email
            fields.append('email')
        if not user.is_staff:
            user.is_staff = True
            fields.append('is_staff')
        if not user.is_superuser:
            user.is_superuser = True
            fields.append('is_superuser')
        if fields:
            user.save(update_fields=fields)


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [migrations.RunPython(create_admin, migrations.RunPython.noop)]
