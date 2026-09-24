from django.urls import path
from . import admin_views

urlpatterns = [
    path('login', admin_views.login_admin),
    path('logout', admin_views.logout_admin),
    path('users', admin_views.admin_users),
    path('users/<int:user_id>', admin_views.admin_user_detail),
    path('customers', admin_views.admin_customers),
    path('customers/<str:email>/delete', admin_views.admin_customer_delete),
    path('orders', admin_views.admin_orders),
    path('orders/<str:order_id>', admin_views.admin_delete_order),
    path('lease-applications', admin_views.admin_lease_applications),
    path('lease-applications/<int:application_id>', admin_views.admin_delete_lease_application),
    path('chat', admin_views.admin_chat_messages),
    path('chat/reply', admin_views.admin_chat_reply),
    path('chat/messages/<int:message_id>', admin_views.admin_chat_message_actions),
    path('chat/<str:email>/delete', admin_views.admin_delete_chat),
    path('presence', admin_views.admin_presence),
]