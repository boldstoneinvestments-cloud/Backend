from django.db import migrations, models
from api.admin_cache import invalidate_admin_cache


def seed_initial_blog_post(apps, schema_editor):
    BlogPost = apps.get_model('api', 'BlogPost')
    database = schema_editor.connection.alias
    BlogPost.objects.using(database).get_or_create(
        title='Boldstone To Raise US $140,000 Pre-Seed Investment',
        defaults={
            'category': 'News',
            'author': 'Boldstone',
            'date': 'June 17, 2026',
            'image': 'https://address-restaurant2.odoo.com/web/image/2031-8f550bf9/coffee%20machine.webp',
            'excerpt': 'Boldstone Announces US $140K (UGX 500M) Equity and Debt Financing Plan to Build Coffee Processing Infrastructure in Uganda.',
            'body': [
                "Boldstone Property Investments LLC today announced its 2026-2027 plan to finance the establishment of coffee processing infrastructure in Kyenjojo District, Uganda. Boldstone is raising money in order to set up coffee processing infrastructure that will enable it to dry, hull and purchase coffee beans from thousands of smallholder farmers in Uganda. The investment will also enable the establishment of Boldstone's coffee digital infrastructure, extend small recoverable loans to verified smallholder farmers and help the business accomplish the incorporation in the USA as a Delaware C-Corp.",
                'Boldstone expects to raise UGX 500M (Approx. US $140,000) of gross cash proceeds during the 2026-2027 financial year. The company plans to achieve its funding objective by using a balanced combination of debt and equity financing to maintain a solid investment-grade balance sheet. On the equity side, Boldstone plans to raise approximately half of its 2026-2027 funding through a combination of equity-linked and common equity issuances.',
                'The company plans to issue equity from the at-the-market program flexibly over time based on market conditions and capital needs. On the debt side, Boldstone intends to raise upwards of UGX 150M (US$ 40,000) of low interest debt via crowdfunding and UGX 100M (US $27,000) in a low interest impact linked Uganda government facility.',
                "This funding plan reflects Boldstone's commitment to maintaining an investment-grade rating, prudent capital allocation, balance sheet strength, and transparency with investors as the company continues to expand its sustainable coffee trade and farming business. These transactions have been approved by Boldstone's Board of Directors which constitutes the founding members. Boldstone is in the process of identifying a financial advisor for the debt and preferred equity offering which may cause slight changes to fund allocations.",
            ],
            'is_published': True,
        },
    )
    invalidate_admin_cache('blog_posts')


class Migration(migrations.Migration):
    dependencies = [('api', '0015_customerprofile_auth_version')]

    operations = [
        migrations.CreateModel(
            name='BlogPost',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=240)),
                ('category', models.CharField(choices=[('News', 'News'), ('Impact', 'Impact'), ('Industry', 'Industry'), ('Company', 'Company'), ('Agronomy', 'Agronomy')], default='News', max_length=20)),
                ('author', models.CharField(max_length=120)),
                ('date', models.CharField(max_length=80)),
                ('image', models.URLField(max_length=1000)),
                ('excerpt', models.TextField()),
                ('body', models.JSONField(default=list)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-id']},
        ),
        migrations.RunPython(seed_initial_blog_post, migrations.RunPython.noop),
    ]