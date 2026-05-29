from django.urls import path
from . import views

app_name = 'prediction'

urlpatterns = [
    path('', views.prediction_index, name='index'),
    path('api/data/', views.api_prediction_data, name='api_data'),
    path('api/trend/', views.api_district_trend, name='api_trend'),
]
