from django.db import migrations, models
import django.db.models.deletion


PRODUCTS = [
    ('arabica', 'seedlings', 'Arabica Seedlings', 1500, 'per seedling', 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789646469/Arabica-Coffee-Seeds-For-Planting_o2ijiw.jpg', 'High-altitude Arabica varieties known for their smooth, mild flavour with hints of fruit and chocolate. Ideal for elevations above 1,200m.', 'Best Seller', ['SL14', 'SL28', 'SL34', 'Ruiru 11', 'Batian', 'CIFC 635', 'K7', 'Blue Mountain', 'Nyasaland']),
    ('robusta', 'seedlings', 'Robusta Seedlings', 1200, 'per seedling', 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789646468/Robusta_svyvej.jpg', 'Hardy Robusta varieties with strong, bold flavour and higher caffeine content. Thrives in lower altitudes and are highly disease-resistant.', 'High Yield', ['BP42', 'BP358', 'BP409', 'Newton', 'Napak 1', 'Napak 2', 'Napak 3', 'Napak 4', 'Clone 186']),
    ('light-roast', 'roasted', 'Light Roast Coffee', 28000, 'per kg', 'https://images.unsplash.com/photo-1514432324607-a09d9b4aefdd?auto=format&fit=crop&w=600&q=80', 'Lightly roasted to preserve the natural fruity and floral notes of Ugandan coffee. Bright acidity with a light body, perfect for filter and pour-over brewing.', '', []),
    ('medium-roast', 'roasted', 'Medium Roast Coffee', 30000, 'per kg', 'https://images.unsplash.com/photo-1447933601403-0c6688de566e?auto=format&fit=crop&w=600&q=80', 'A balanced medium roast delivering a smooth, well-rounded cup with hints of caramel and chocolate. Ideal for drip coffee and espresso.', '', []),
    ('dark-roast', 'roasted', 'Dark Roast Coffee', 32000, 'per kg', 'https://images.unsplash.com/photo-1509042239860-f550ce710b93?auto=format&fit=crop&w=600&q=80', 'Boldly roasted for a rich, intense flavour with low acidity and a full body. Deep notes of dark chocolate and smoky undertones. Perfect for espresso and French press.', '', []),
    ('mvule', 'trees', 'Mvule (Milicia excelsa)', 1500, 'per seedling', 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789651003/Mvule_lhgpld.png', "One of Uganda's most prized hardwoods, known for its durability and high timber value. A long-term investment in land and biodiversity.", '', []),
    ('musizi', 'trees', 'Musizi (Maesopsis eminii)', 1500, 'per seedling', 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789650949/Musizi_atn3xr.png', 'A fast-growing indigenous hardwood native to Uganda. Excellent for timber, shade, and agroforestry integration with coffee farms.', '', []),
    ('mutuba', 'trees', 'Mutuba (Ficus natalensis)', 1500, 'per seedling', 'https://res.cloudinary.com/cwj8d38f/image/upload/v1789650887/Mutuba_qz02q5.jpg', 'A culturally significant tree in Uganda, widely used for bark cloth production, shade, and soil conservation. Grows well across a range of climates.', '', []),
]


def seed_products(apps, schema_editor):
    Product = apps.get_model('shop', 'Product')
    Product.objects.bulk_create([
        Product(id=id_, category=category, name=name, price=price, unit=unit, image=image,
                description=description, badge=badge, varieties=varieties)
        for id_, category, name, price, unit, image, description, badge, varieties in PRODUCTS
    ])


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.CharField(max_length=80, primary_key=True, serialize=False)),
                ('category', models.CharField(choices=[('seedlings', 'Coffee Seedlings'), ('roasted', 'Roasted Coffee'), ('trees', 'Indigenous Trees')], max_length=20)),
                ('name', models.CharField(max_length=200)),
                ('price', models.PositiveIntegerField()),
                ('unit', models.CharField(max_length=50)),
                ('image', models.URLField()),
                ('description', models.TextField()),
                ('badge', models.CharField(blank=True, max_length=80)),
                ('varieties', models.JSONField(blank=True, default=list)),
                ('active', models.BooleanField(default=True)),
            ],
            options={'ordering': ('category', 'name')},
        ),
        migrations.CreateModel(
            name='ShopOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('phone', models.CharField(max_length=50)),
                ('email', models.EmailField(max_length=254)),
                ('product_name', models.CharField(max_length=200)),
                ('quantity', models.PositiveIntegerField()),
                ('location', models.CharField(max_length=200)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='orders', to='shop.product')),
            ],
        ),
        migrations.RunPython(seed_products, migrations.RunPython.noop),
    ]