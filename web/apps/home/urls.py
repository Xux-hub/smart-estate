from django.urls import path
from . import views

app_name = 'home'

urlpatterns = [
    path('', views.index, name='index'),
    path('city/<str:city_name>/', views.city_detail, name='city_detail'),
]
