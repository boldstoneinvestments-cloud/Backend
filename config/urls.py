from django.urls import include, path

urlpatterns = [
	path('api/', include('api.urls')),
	path('api/shop/', include('shop.urls')),
]