from django.urls import path
from . import views

urlpatterns = [
    path("alertas/pedidos/", views.alertas_pedidos_view, name="usuarios_alertas_pedidos"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("personal/", views.usuarios_list_view, name="usuarios_personal"),
    path("personal/crear/", views.usuarios_create_view, name="usuarios_personal_crear"),
    path("personal/editar/<int:pk>/", views.usuarios_update_view, name="usuarios_personal_editar"),
    path("personal/estado/<int:pk>/", views.usuarios_toggle_activo_view, name="usuarios_personal_estado"),
    path("personal/desbloquear/<int:pk>/", views.usuarios_desbloquear_view, name="usuarios_personal_desbloquear"),
    path("personal/eliminar/<int:pk>/", views.usuarios_delete_view, name="usuarios_personal_eliminar"),
    path("repartidores/", views.repartidores_list_view, name="usuarios_repartidores"),
    path("repartidores/crear/", views.repartidores_create_view, name="usuarios_repartidores_crear"),
    path("repartidores/editar/<int:pk>/", views.repartidores_update_view, name="usuarios_repartidores_editar"),
    path("repartidores/estado/<int:pk>/", views.repartidores_toggle_view, name="usuarios_repartidores_estado"),
    path("repartidores/eliminar/<int:pk>/", views.repartidores_delete_view, name="usuarios_repartidores_eliminar"),
    path("bitacora/", views.bitacora_list_view, name="usuarios_bitacora"),
    path("datos-entrega/", views.datos_entrega_view, name="datos_entrega"),
]
