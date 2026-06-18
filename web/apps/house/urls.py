from django.urls import path

from . import views

app_name = 'house'

urlpatterns = [
    path('', views.house_list, name='list'),
    path('<int:house_id>/', views.house_detail, name='detail'),
    path('search/', views.search, name='search'),
    path('district/<path:district_id>/', views.district_detail, name='district_detail'),
    path('api/districts/', views.api_district_list, name='api_districts'),
    path('api/map-data/', views.api_house_map_data, name='api_map_data'),
]
