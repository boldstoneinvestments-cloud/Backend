from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0007_chatmessage_is_ai_adminpresence')]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='admin_name',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='chatmessage',
            name='admin_avatar',
            field=models.URLField(blank=True),
        ),
    ]