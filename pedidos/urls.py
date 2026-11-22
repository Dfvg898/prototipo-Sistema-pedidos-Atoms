from django.urls import path
from . import views

urlpatterns = [
    path('', views.ver_pedidos, name='ver_pedidos'),
    path('estado/<int:pedido_id>/', views.cambiar_estado, name='cambiar_estado'),
    path('historial/', views.historial_pedidos, name='historial_pedidos'),
    path('pago/<int:pedido_id>/', views.seleccionar_pago, name='seleccionar_pago'),
    path('pago/confirmar/<int:pago_id>/', views.confirmar_pago_trans, name='confirmar_pago_trans'),
    path('delivery/', views.lista_delivery, name='lista_delivery'),
    path('delivery/asignar/<int:pedido_id>/', views.asignar_repartidor, name='asignar_repartidor'),
    path('notificaciones/', views.notificaciones_pedidos, name='notificaciones_pedidos'),
    path('crear/', views.crear_pedido, name='crear_pedido'),
    # Carrito
    path('carrito/ver/', views.ver_carrito, name='ver_carrito'),
    path('carrito/agregar/<int:producto_id>/', views.agregar_carrito, name='agregar_carrito'),
    path('carrito/mas/<int:item_id>/', views.incrementar_item, name='incrementar_item'),
    path('carrito/menos/<int:item_id>/', views.disminuir_item, name='disminuir_item'),
    path('carrito/eliminar/<int:item_id>/', views.eliminar_item, name='eliminar_item'),
]