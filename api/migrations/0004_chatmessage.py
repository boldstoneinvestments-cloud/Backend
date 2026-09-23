from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0003_leaseapplication')]

    operations = [migrations.CreateModel(
        name='ChatMessage',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('name', models.CharField(max_length=200)),
            ('email', models.EmailField(max_length=254)),
            ('message', models.TextField()),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ],
    )]
