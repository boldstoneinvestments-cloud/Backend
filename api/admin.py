from django.contrib import admin
from .models import ContactMessage, Lease, Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'product', 'quantity', 'location', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'phone', 'product', 'location')
    readonly_fields = ('created_at',)


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)


@admin.register(Lease)
class LeaseAdmin(admin.ModelAdmin):
    list_display = ('acres', 'created_at')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)