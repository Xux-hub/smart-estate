from django.urls import path
from . import views

app_name = 'shandong'

urlpatterns = [
    # JSON API（必须放在动态路由前面）
    path('api/city-stats/', views.api_city_stats, name='api_city_stats'),
    path('api/district-stats/', views.api_district_stats, name='api_district_stats'),
    path('api/house-filter/', views.api_house_filter, name='api_house_filter'),
    # 图表
    path('chart/desc-stats/', views.chart_desc_stats, name='chart_desc_stats'),
    path('chart/housing-count/', views.chart_housing_count, name='chart_housing_count'),
    path('chart/avg-price/', views.chart_avg_price, name='chart_avg_price'),
    path('chart/listing-trend/', views.chart_listing_trend, name='chart_listing_trend'),
    path('chart/high-end/', views.chart_high_end, name='chart_high_end'),
    path('chart/wordcloud/', views.chart_wordcloud, name='chart_wordcloud'),
    path('chart/top5-layouts/', views.chart_top5_layouts, name='chart_top5_layouts'),
    path('chart/floor-pie/', views.chart_floor_pie, name='chart_floor_pie'),
    path('chart/floor-avg-price/', views.chart_floor_avg_price, name='chart_floor_avg_price'),
    path('chart/decoration/', views.chart_decoration, name='chart_decoration'),
    path('chart/area-distribution/', views.chart_area_distribution, name='chart_area_distribution'),
    # 页面
    path('', views.province, name='province'),
    path('<str:city_name>/', views.city_detail, name='city'),
    path('<str:city_name>/<str:district_name>/', views.district_detail, name='district'),
]
