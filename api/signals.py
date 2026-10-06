from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .admin_cache import invalidate_admin_cache
from .models import AdminActivity, AdminPresence, BlogPost, ChatMessage, Lease, LeaseApplication, Order
from shop.models import Product, ShopOrder

User = get_user_model()


@receiver([post_save, post_delete], sender=User)
def invalidate_user_cache(sender, instance, **kwargs):
    invalidate_admin_cache('admin_users')
    if not instance.is_staff:
        invalidate_admin_cache('admin_customers')


@receiver([post_save, post_delete], sender=ShopOrder)
@receiver([post_save, post_delete], sender=Order)
def invalidate_order_cache(sender, instance, **kwargs):
    invalidate_admin_cache('admin_orders')
    invalidate_admin_cache('admin_customers')


@receiver([post_save, post_delete], sender=LeaseApplication)
def invalidate_lease_application_cache(sender, instance, **kwargs):
    invalidate_admin_cache('admin_lease_applications')
    invalidate_admin_cache('admin_customers')


@receiver([post_save, post_delete], sender=ChatMessage)
def invalidate_chat_cache(sender, instance, **kwargs):
    invalidate_admin_cache('admin_chat')
    if instance.user_id:
        invalidate_admin_cache('customer_chat', scope=str(instance.user_id))


@receiver([post_save, post_delete], sender=AdminActivity)
@receiver([post_save, post_delete], sender=AdminPresence)
def invalidate_activity_cache(sender, instance, **kwargs):
    invalidate_admin_cache('admin_activity')


@receiver([post_save, post_delete], sender=BlogPost)
def invalidate_blog_cache(sender, instance, **kwargs):
    invalidate_admin_cache('blog_posts')


@receiver([post_save, post_delete], sender=Product)
def invalidate_product_cache(sender, instance, **kwargs):
    invalidate_admin_cache('shop_products')


@receiver([post_save, post_delete], sender=Lease)
def invalidate_estate_cache(sender, instance, **kwargs):
    invalidate_admin_cache('estate')