from django.urls import path
from . import admin_views

urlpatterns = [
    path('login', admin_views.login_admin),
    path('logout', admin_views.logout_admin),
    path('orders', admin_views.admin_orders),
]