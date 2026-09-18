from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0002_bootstrap_admin')]

    operations = [migrations.CreateModel(
        name='LeaseApplication',
        fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('full_name', models.CharField(max_length=200)),
            ('email', models.EmailField(max_length=254)),
            ('phone', models.CharField(max_length=50)),
            ('country', models.CharField(max_length=100)),
            ('address', models.CharField(blank=True, max_length=250)),
            ('plan', models.CharField(max_length=100)),
            ('notes', models.TextField(blank=True)),
            ('status', models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('approved', 'Approved'), ('declined', 'Declined')], default='new', max_length=20)),
            ('created_at', models.DateTimeField(auto_now_add=True)),
        ],
    )]