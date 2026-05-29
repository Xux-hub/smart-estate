"""Smart Estate URL Configuration."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.apps.home.urls')),
    path('house/', include('web.apps.house.urls')),
    path('analysis/', include('web.apps.analysis.urls')),
    path('prediction/', include('web.apps.prediction.urls')),
]
