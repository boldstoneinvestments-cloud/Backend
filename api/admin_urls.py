from django.urls import path
from . import admin_views

urlpatterns = [
    path('login', admin_views.login_admin),
    path('logout', admin_views.logout_admin),
    path('users', admin_views.admin_users),
    path('users/<int:user_id>', admin_views.admin_user_detail),
    path('orders', admin_views.admin_orders),
    path('orders/<str:order_id>', admin_views.admin_delete_order),
    path('lease-applications', admin_views.admin_lease_applications),
    path('lease-applications/<int:application_id>', admin_views.admin_delete_lease_application),
]