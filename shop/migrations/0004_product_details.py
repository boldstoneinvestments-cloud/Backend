from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('shop', '0003_update_seedling_prices'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='details',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]