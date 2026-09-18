from django.contrib import admin
from django.urls import include, path

urlpatterns = [
	path('admin/', admin.site.urls),
	path('api/', include('api.urls')),
	path('api/admin/', include('api.admin_urls')),
	path('api/shop/', include('shop.urls')),
]