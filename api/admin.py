from django.contrib import admin
from .models import ChatMessage, ContactMessage, Lease, LeaseApplication, Order


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'message', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at',)


@admin.register(LeaseApplication)
class LeaseApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'plan', 'status', 'created_at')
    list_filter = ('status', 'plan', 'created_at')
    search_fields = ('full_name', 'email', 'phone', 'country', 'plan')
    readonly_fields = ('created_at',)


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