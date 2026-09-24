from django.urls import path
from . import views

urlpatterns = [
    path('health', views.health),
    path('account/sign-up', views.account_signup),
    path('account/sign-in', views.account_login),
    path('account/me', views.account_me),
    path('account/sign-out', views.account_logout),
    path('account/csrf', views.account_csrf),
    path('account/google/start', views.google_start),
    path('account/google/callback', views.google_callback),
    path('estate', views.estate),
    path('estate/invest', views.invest),
    path('orders', views.orders),
    path('contact', views.contact),
    path('chat', views.chat),
    path('chat/messages/<int:message_id>', views.chat_message_actions),
    path('chat/attachments/<int:message_id>', views.chat_attachment),
    path('chat/stream', views.chat_stream),
    path('lease-applications', views.lease_applications),
]