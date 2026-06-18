from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    path('', views.analysis_index, name='index'),
    path('compare/', views.compare, name='compare'),
    # API endpoints
    path('api/price-distribution/', views.api_price_distribution, name='api_price_distribution'),
    path('api/layout-stats/', views.api_layout_stats, name='api_layout_stats'),
    path('api/price-area/', views.api_price_area_scatter, name='api_price_area'),
    path('api/decoration-stats/', views.api_decoration_stats, name='api_decoration_stats'),
]
