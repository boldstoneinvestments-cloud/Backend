from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('shop', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='shoporder', name='invoice_number',
            field=models.CharField(db_index=True, default='PENDING-INVOICE', max_length=40),
            preserve_default=False,
        ),
        migrations.AddField(model_name='shoporder', name='country', field=models.CharField(default='Uganda', max_length=100)),
        migrations.AddField(model_name='shoporder', name='province', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='shoporder', name='district', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='shoporder', name='street', field=models.CharField(blank=True, max_length=200)),
        migrations.AddField(model_name='shoporder', name='village', field=models.CharField(blank=True, max_length=200)),
    ]