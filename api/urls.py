from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('estate', views.estate),
    path('estate/invest', views.invest),
    path('orders', views.orders),
    path('contact', views.contact),
    path('chat', views.chat),
    path('lease-applications', views.lease_applications),
]