from functools import wraps
from django.shortcuts import render, redirect
from django.conf import settings
from .models import BitacoraEvento


def obtener_ip_cliente(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def rol_requerido(*roles_permitidos):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            if not user.activo or (roles_permitidos and user.rol not in roles_permitidos):
                BitacoraEvento.objects.create(
                    usuario=user,
                    tipo=BitacoraEvento.TipoEvento.ACCESO_DENEGADO,
                    descripcion=f"Acceso denegado (403) a la ruta '{request.path}' con rol '{user.rol}'.",
                    ip_origen=obtener_ip_cliente(request),
                )
                return render(
                    request,
                    "usuarios/403.html",
                    {"ruta_intentada": request.path},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator
