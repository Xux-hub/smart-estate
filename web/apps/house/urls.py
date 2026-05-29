from django.urls import path
from . import views
from . import crawler_views

app_name = 'house'

urlpatterns = [
    path('', views.house_list, name='list'),
    path('<int:house_id>/', views.house_detail, name='detail'),
    path('search/', views.search, name='search'),
    path('district/<int:district_id>/', views.district_detail, name='district_detail'),
    # API endpoints
    path('api/districts/', views.api_district_list, name='api_districts'),
    path('api/map-data/', views.api_house_map_data, name='api_map_data'),
    # 爬虫管理
    path('crawler/', crawler_views.crawler_index, name='crawler_index'),
    path('crawler/start/', crawler_views.crawler_start, name='crawler_start'),
    path('crawler/status/<str:task_id>/', crawler_views.crawler_status, name='crawler_status'),
    path('crawler/list/', crawler_views.crawler_list, name='crawler_list'),
]
