"""Smart Estate URL Configuration."""
from django.contrib import admin
from django.urls import path, include

from web.apps.house import views as house_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.apps.home.urls')),
    path('details/', house_views.house_detail_from_query, name='legacy_house_detail'),
    path('house/', include('web.apps.house.urls')),
    path('analysis/', include('web.apps.analysis.urls')),
    path('prediction/', include('web.apps.prediction.urls')),
    path('shandong/', include('web.apps.shandong.urls')),
]
