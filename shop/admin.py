from django.contrib import admin
from .models import Product, ShopOrder


@admin.register(ShopOrder)
class ShopOrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'product_name', 'quantity', 'email', 'phone', 'location', 'created_at')
    list_filter = ('created_at', 'product')
    search_fields = ('name', 'email', 'phone', 'product_name', 'location')
    readonly_fields = ('created_at',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'unit', 'active')
    list_filter = ('category', 'active')
    search_fields = ('id', 'name', 'description')