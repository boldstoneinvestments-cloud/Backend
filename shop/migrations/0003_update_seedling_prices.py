from django.db import migrations


def update_seedling_prices(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.filter(id__in=['arabica', 'robusta']).update(price=2000)


class Migration(migrations.Migration):
    dependencies = [('shop', '0002_shoporder_address_invoice')]

    operations = [
        migrations.RunPython(update_seedling_prices, migrations.RunPython.noop),
    ]
