from django.conf import settings
from django.db import migrations


IDENTITY_NAMES = ('MOSES ALICWAMU', 'HABIB TUMWESIGE')


def reset_moses_habib_two_factor(apps, schema_editor):
    database = schema_editor.connection.alias
    user_app, user_model_name = settings.AUTH_USER_MODEL.split('.')
    User = apps.get_model(user_app, user_model_name)
    TOTPDevice = apps.get_model('otp_totp', 'TOTPDevice')
    AdminRecoveryCodes = apps.get_model('api', 'AdminRecoveryCodes')
    active_staff_ids = User.objects.using(database).filter(
        is_active=True,
        is_staff=True,
    ).values_list('pk', flat=True)

    TOTPDevice.objects.using(database).filter(
        user_id__in=active_staff_ids,
        name__in=[f'admin:{identity_name}' for identity_name in IDENTITY_NAMES],
    ).delete()

    recovery_records = AdminRecoveryCodes.objects.using(database).filter(
        user_id__in=active_staff_ids,
    )
    for recovery in recovery_records:
        hashes = recovery.identity_code_hashes or {}
        changed = False
        for identity_name in IDENTITY_NAMES:
            if identity_name in hashes:
                hashes.pop(identity_name)
                changed = True
        if changed:
            recovery.identity_code_hashes = hashes
            recovery.save(using=database, update_fields=['identity_code_hashes'])


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_reset_ssemata_two_factor'),
        ('otp_totp', '0003_add_timestamps'),
    ]

    operations = [
        migrations.RunPython(reset_moses_habib_two_factor, migrations.RunPython.noop),
    ]