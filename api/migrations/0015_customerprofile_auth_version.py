from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_reset_moses_habib_two_factor'),
    ]

    operations = [
        migrations.AddField(
            model_name='customerprofile',
            name='auth_version',
            field=models.PositiveIntegerField(default=0),
        ),
    ]