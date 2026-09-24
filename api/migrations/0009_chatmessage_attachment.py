from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0008_chatmessage_admin_identity')]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='attachment',
            field=models.FileField(blank=True, null=True, upload_to='chat_attachments/'),
        ),
    ]