from django.urls import path
from . import views

urlpatterns = [
    path('', views.homeView, name='base'),
    path('lista/', views.listaView, name='lista'),
    #  Categorías
    path('gestion/categorias/', views.categoriasListView, name='categorias'),
    path('gestion/categorias/crear/', views.categoriasCreateView, name='categorias_crear'),
    path('gestion/categorias/editar/<int:pk>/', views.categoriasUpdateView, name='categorias_editar'),
    path('gestion/categorias/eliminar/<int:pk>/', views.categoriasDeleteView, name='categorias_eliminar'),
    # Productos
    path('gestion/productos/', views.productosListView, name='productos'),
    path('gestion/productos/crear/', views.productosCreateView, name='productos_crear'),
    path('gestion/productos/editar/<int:pk>/', views.productosUpdateView, name='productos_editar'),
    path('gestion/productos/eliminar/<int:pk>/', views.productosDeleteView, name='productos_eliminar'),
    # Opción de personalización
    path('gestion/opciones/', views.opcionesPersonalizacionListView, name='opciones_personalizacion'),
    path('gestion/opciones/crear/', views.opcionesPersonalizacionCreateView, name='opciones_personalizacion_crear'),
    path('gestion/opciones/editar/<int:pk>/', views.opcionesPersonalizacionUpdateView, name='opciones_personalizacion_editar'),
    path('gestion/opciones/eliminar/<int:pk>/', views.opcionesPersonalizacionDeleteView, name='opciones_personalizacion_eliminar'),
]