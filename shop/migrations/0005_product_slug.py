from django.db import migrations, models
from django.utils.text import slugify


def populate_product_slugs(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    database = schema_editor.connection.alias
    used_slugs = set()

    for product in Product.objects.using(database).order_by('pk').iterator():
        base_slug = slugify(product.name)[:100].rstrip('-') or 'product'
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            suffix_text = f'-{suffix}'
            slug = f'{base_slug[:100 - len(suffix_text)].rstrip("-")}{suffix_text}'
            suffix += 1
        used_slugs.add(slug)
        Product.objects.using(database).filter(pk=product.pk).update(slug=slug)


class Migration(migrations.Migration):
    dependencies = [
        ('shop', '0004_product_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, db_index=False, default='', max_length=100),
        ),
        migrations.RunPython(populate_product_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(blank=True, max_length=100, unique=True),
        ),
    ]