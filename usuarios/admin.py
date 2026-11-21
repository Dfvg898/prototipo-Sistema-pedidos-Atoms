from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Usuario, Repartidor, BitacoraEvento


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ("correo", "nombre", "rol", "activo", "intentos_fallidos", "bloqueado_hasta")
    list_filter = ("rol", "activo")
    search_fields = ("correo", "nombre")
    ordering = ("correo",)

    fieldsets = (
        ("Credenciales", {"fields": ("correo", "password")}),
        ("Información Personal y Rol", {"fields": ("nombre", "rol", "repartidor")}),
        ("Seguridad y Estado", {"fields": ("activo", "intentos_fallidos", "bloqueado_hasta", "is_staff", "is_superuser")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("correo", "nombre", "rol", "repartidor", "password1", "password2", "activo", "is_staff"),
            },
        ),
    )


@admin.register(Repartidor)
class RepartidorAdmin(admin.ModelAdmin):
    list_display = ("id_repartidor", "nombre_repartidor", "telefono", "activo")
    list_filter = ("activo",)
    search_fields = ("nombre_repartidor", "telefono")


@admin.register(BitacoraEvento)
class BitacoraEventoAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "tipo", "usuario", "ip_origen", "descripcion")
    list_filter = ("tipo", "fecha_hora")
    search_fields = ("descripcion", "usuario__correo")
    readonly_fields = ("fecha_hora", "tipo", "usuario", "id_pedido", "ip_origen", "descripcion")
