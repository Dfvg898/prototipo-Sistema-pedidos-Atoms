from django.urls import path
from . import views

urlpatterns = [
    path('', views.homeView, name='base'),
    path('lista/', views.listaView, name='lista'),
]