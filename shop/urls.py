from django.urls import path
from . import views

urlpatterns = [
    path('products', views.products),
    path('products/', views.products),
    path('orders', views.orders),
    path('orders/', views.orders),
]