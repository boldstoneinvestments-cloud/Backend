from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0004_chatmessage')]

    operations = [
        migrations.AddField(
            model_name='chatmessage',
            name='is_admin',
            field=models.BooleanField(default=False),
        ),
    ]