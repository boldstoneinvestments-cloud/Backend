from django.db import models


class Product(models.Model):
    CATEGORY_CHOICES = (
        ('seedlings', 'Coffee Seedlings'),
        ('roasted', 'Roasted Coffee'),
        ('trees', 'Indigenous Trees'),
    )

    id = models.CharField(max_length=80, primary_key=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=200)
    price = models.PositiveIntegerField()
    unit = models.CharField(max_length=50)
    image = models.URLField()
    description = models.TextField()
    badge = models.CharField(max_length=80, blank=True)
    varieties = models.JSONField(default=list, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ('category', 'name')


class ShopOrder(models.Model):
    invoice_number = models.CharField(max_length=40, db_index=True)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=50)
    email = models.EmailField()
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    location = models.CharField(max_length=200)
    country = models.CharField(max_length=100, default='Uganda')
    province = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    street = models.CharField(max_length=200, blank=True)
    village = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)