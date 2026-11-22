from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .models import Usuario, Repartidor, BitacoraEvento
from .forms import (
    LoginPersonalForm,
    UsuarioCrearForm,
    UsuarioEditarForm,
    RepartidorForm,
    DatosEntregaCheckoutForm,
)
from .decorators import obtener_ip_cliente, rol_requerido

MENSAJE_ERROR_GENERICO = "Credenciales incorrectas o cuenta temporalmente no disponible."
EXPIRACION_SESION_CAJERO_SEG = 30 * 60
EXPIRACION_SESION_REPARTIDOR_SEG = 60 * 60


def redireccion_por_rol(usuario: Usuario) -> str:
    if usuario.rol == Usuario.Rol.DUENO:
        return "/usuarios/personal/"
    return "/"


def login_view(request):
    if request.user.is_authenticated:
        return redirect(redireccion_por_rol(request.user))

    form = LoginPersonalForm(request.POST or None)

    if request.method == "POST":
        ip_cliente = obtener_ip_cliente(request)

        if form.is_valid():
            correo = form.cleaned_data["correo"]
            password = form.cleaned_data["password"]

            usuario = Usuario.objects.filter(correo=correo).first()

            if usuario is None or not usuario.activo:
                BitacoraEvento.objects.create(
                    usuario=usuario,
                    tipo=BitacoraEvento.TipoEvento.LOGIN_FALLIDO,
                    descripcion=f"Intento de login sobre cuenta inexistente o inactiva ({correo}).",
                    ip_origen=ip_cliente,
                )
                messages.error(request, MENSAJE_ERROR_GENERICO)
                return render(request, "acceso.html", {"form": form})

            if usuario.esta_bloqueado():
                BitacoraEvento.objects.create(
                    usuario=usuario,
                    tipo=BitacoraEvento.TipoEvento.LOGIN_FALLIDO,
                    descripcion="Intento de login rechazado: cuenta en periodo de bloqueo temporal.",
                    ip_origen=ip_cliente,
                )
                messages.error(request, MENSAJE_ERROR_GENERICO)
                return render(request, "acceso.html", {"form": form})

            if not usuario.check_password(password):
                bloqueado_ahora = usuario.registrar_intento_fallido()

                if bloqueado_ahora:
                    BitacoraEvento.objects.create(
                        usuario=usuario,
                        tipo=BitacoraEvento.TipoEvento.CUENTA_BLOQUEADA,
                        descripcion="Cuenta bloqueada por 15 minutos tras alcanzar 5 intentos fallidos.",
                        ip_origen=ip_cliente,
                    )
                else:
                    BitacoraEvento.objects.create(
                        usuario=usuario,
                        tipo=BitacoraEvento.TipoEvento.LOGIN_FALLIDO,
                        descripcion=f"Contraseña inválida (intento {usuario.intentos_fallidos}/5).",
                        ip_origen=ip_cliente,
                    )

                messages.error(request, MENSAJE_ERROR_GENERICO)
                return render(request, "acceso.html", {"form": form})

            usuario.resetear_intentos()
            login(request, usuario)

            if usuario.rol == Usuario.Rol.REPARTIDOR:
                request.session.set_expiry(EXPIRACION_SESION_REPARTIDOR_SEG)
            else:
                request.session.set_expiry(EXPIRACION_SESION_CAJERO_SEG)

            BitacoraEvento.objects.create(
                usuario=usuario,
                tipo=BitacoraEvento.TipoEvento.LOGIN_EXITOSO,
                descripcion=f"Inicio de sesión exitoso con rol {usuario.rol}.",
                ip_origen=ip_cliente,
            )

            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                url=next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)

            return redirect(redireccion_por_rol(usuario))
        else:
            messages.error(request, MENSAJE_ERROR_GENERICO)

    return render(request, "acceso.html", {"form": form})


@require_POST
def logout_view(request):
    if request.user.is_authenticated:
        BitacoraEvento.objects.create(
            usuario=request.user,
            tipo=BitacoraEvento.TipoEvento.LOGOUT,
            descripcion="Cierre de sesión manual del usuario.",
            ip_origen=obtener_ip_cliente(request),
        )
        logout(request)
        messages.info(request, "Has cerrado sesión correctamente.")

    return redirect("login")


@rol_requerido(Usuario.Rol.DUENO)
def usuarios_list_view(request):
    usuarios = Usuario.objects.select_related("repartidor").order_by("nombre")
    return render(
        request,
        "usuarios/usuario_list.html",
        {"usuarios": usuarios, "seccion_usuarios": "personal"},
    )


@rol_requerido(Usuario.Rol.DUENO)
def usuarios_create_view(request):
    form = UsuarioCrearForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        nuevo_usuario = form.save()
        messages.success(
            request,
            f"Cuenta de {nuevo_usuario.nombre} ({nuevo_usuario.get_rol_display()}) creada exitosamente.",
        )
        return redirect("usuarios_personal")
    return render(
        request,
        "usuarios/usuario_form.html",
        {"form": form, "seccion_usuarios": "personal"},
    )


@rol_requerido(Usuario.Rol.DUENO)
def usuarios_update_view(request, pk):
    usuario_obj = get_object_or_404(Usuario, pk=pk)
    form = UsuarioEditarForm(request.POST or None, instance=usuario_obj)
    if request.method == "POST" and form.is_valid():
        usuario_editado = form.save()
        messages.success(
            request,
            f"Cuenta de {usuario_editado.nombre} actualizada correctamente.",
        )
        return redirect("usuarios_personal")
    return render(
        request,
        "usuarios/usuario_form.html",
        {"form": form, "object": usuario_obj, "seccion_usuarios": "personal"},
    )


@rol_requerido(Usuario.Rol.DUENO)
@require_POST
def usuarios_toggle_activo_view(request, pk):
    usuario_obj = get_object_or_404(Usuario, pk=pk)
    if usuario_obj.pk == request.user.pk:
        messages.error(request, "No puedes desactivar tu propia cuenta en uso.")
        return redirect("usuarios_personal")

    usuario_obj.activo = not usuario_obj.activo
    usuario_obj.save(update_fields=["activo"])
    if usuario_obj.repartidor and usuario_obj.repartidor.activo != usuario_obj.activo:
        usuario_obj.repartidor.activo = usuario_obj.activo
        usuario_obj.repartidor.save(update_fields=["activo"])
    estado_txt = "activada" if usuario_obj.activo else "desactivada"
    messages.info(request, f"La cuenta de {usuario_obj.nombre} fue {estado_txt}.")
    return redirect("usuarios_personal")


@rol_requerido(Usuario.Rol.DUENO)
@require_POST
def usuarios_desbloquear_view(request, pk):
    usuario_obj = get_object_or_404(Usuario, pk=pk)
    usuario_obj.resetear_intentos()
    messages.success(request, f"Se desbloqueó el acceso de {usuario_obj.nombre}.")
    return redirect("usuarios_personal")


@rol_requerido(Usuario.Rol.DUENO)
@require_POST
def usuarios_delete_view(request, pk):
    usuario_obj = get_object_or_404(Usuario, pk=pk)
    if usuario_obj.pk == request.user.pk:
        messages.error(request, "No puedes eliminar tu propia cuenta en uso.")
        return redirect("usuarios_personal")

    nombre = usuario_obj.nombre
    repartidor_asociado = usuario_obj.repartidor
    usuario_obj.delete()
    if repartidor_asociado:
        repartidor_asociado.delete()
    messages.success(request, f"El usuario '{nombre}' fue eliminado.")
    return redirect("usuarios_personal")


@rol_requerido(Usuario.Rol.DUENO)
def repartidores_list_view(request):
    repartidores = Repartidor.objects.select_related("cuenta_usuario").order_by("nombre_repartidor")
    return render(
        request,
        "usuarios/repartidor_list.html",
        {"repartidores": repartidores, "seccion_usuarios": "repartidores"},
    )


@rol_requerido(Usuario.Rol.DUENO)
def repartidores_create_view(request):
    form = RepartidorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        repartidor = form.save()
        messages.success(request, f"Repartidor '{repartidor.nombre_repartidor}' registrado.")
        return redirect("usuarios_repartidores")
    return render(
        request,
        "usuarios/repartidor_form.html",
        {"form": form, "seccion_usuarios": "repartidores"},
    )


@rol_requerido(Usuario.Rol.DUENO)
def repartidores_update_view(request, pk):
    repartidor = get_object_or_404(Repartidor, pk=pk)
    form = RepartidorForm(request.POST or None, instance=repartidor)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Repartidor '{repartidor.nombre_repartidor}' actualizado.")
        return redirect("usuarios_repartidores")
    return render(
        request,
        "usuarios/repartidor_form.html",
        {"form": form, "object": repartidor, "seccion_usuarios": "repartidores"},
    )


@rol_requerido(Usuario.Rol.DUENO)
@require_POST
def repartidores_toggle_view(request, pk):
    repartidor = get_object_or_404(Repartidor, pk=pk)
    repartidor.activo = not repartidor.activo
    repartidor.save(update_fields=["activo"])
    if hasattr(repartidor, "cuenta_usuario") and repartidor.cuenta_usuario:
        if repartidor.cuenta_usuario.activo != repartidor.activo:
            repartidor.cuenta_usuario.activo = repartidor.activo
            repartidor.cuenta_usuario.save(update_fields=["activo"])
    messages.info(request, f"Estado de '{repartidor.nombre_repartidor}' actualizado.")
    return redirect("usuarios_repartidores")


@rol_requerido(Usuario.Rol.DUENO)
@require_POST
def repartidores_delete_view(request, pk):
    repartidor = get_object_or_404(Repartidor, pk=pk)
    nombre = repartidor.nombre_repartidor
    cuenta = getattr(repartidor, "cuenta_usuario", None)
    if cuenta and cuenta.pk != request.user.pk:
        cuenta.delete()
    repartidor.delete()
    messages.success(request, f"El repartidor '{nombre}' fue eliminado.")
    return redirect("usuarios_repartidores")


@rol_requerido(Usuario.Rol.DUENO)
def bitacora_list_view(request):
    tipo_filtro = request.GET.get("tipo", "")
    eventos = BitacoraEvento.objects.select_related("usuario").all()
    if tipo_filtro:
        eventos = eventos.filter(tipo=tipo_filtro)

    return render(
        request,
        "usuarios/bitacora_list.html",
        {
            "eventos": eventos[:100],
            "tipos_evento": BitacoraEvento.TipoEvento.choices,
            "tipo_actual": tipo_filtro,
            "seccion_usuarios": "bitacora",
        },
    )


def datos_entrega_view(request):
    datos_guardados = request.session.get("datos_entrega_pedido", {})
    carrito = request.session.get("carrito", [])
    subtotal = 0

    for item in carrito:
        subtotal += int(item.get("precio_unitario", 0)) * int(item.get("cantidad", 1))
    request.session["subtotal_carrito"] = subtotal

    if request.method == "POST":
        form = DatosEntregaCheckoutForm(request.POST)
        if form.is_valid():
            datos = form.cleaned_data
            costo_despacho = datos["costo_despacho"]
            total_estimado = subtotal + costo_despacho

            datos_sesion = {
                "nombre_cliente": datos["nombre_cliente"],
                "telefono": datos["telefono"],
                "modalidad_entrega": datos["modalidad_entrega"],
                "direccion": datos["direccion"],
                "referencia": datos["referencia"],
                "observaciones": datos["observaciones"],
                "subtotal": subtotal,
                "costo_despacho": costo_despacho,
                "total_estimado": total_estimado,
            }
            request.session["datos_entrega_pedido"] = datos_sesion
            messages.success(
                request,
                "Datos de entrega y observaciones guardados correctamente. Puedes continuar al pago.",
            )
            return redirect("datos_entrega")
        else:
            modalidad_actual = request.POST.get(
                "modalidad_entrega", DatosEntregaCheckoutForm.MODALIDAD_RETIRO
            )
            costo_despacho = (
                DatosEntregaCheckoutForm.COSTO_DESPACHO_FIJO
                if modalidad_actual == DatosEntregaCheckoutForm.MODALIDAD_DESPACHO
                else 0
            )
            messages.error(
                request,
                "Por favor completa los campos obligatorios marcados en rojo antes de confirmar.",
            )
    else:
        initial = datos_guardados if datos_guardados else {
            "modalidad_entrega": DatosEntregaCheckoutForm.MODALIDAD_RETIRO
        }
        form = DatosEntregaCheckoutForm(initial=initial)
        modalidad_actual = initial.get(
            "modalidad_entrega", DatosEntregaCheckoutForm.MODALIDAD_RETIRO
        )
        costo_despacho = (
            DatosEntregaCheckoutForm.COSTO_DESPACHO_FIJO
            if modalidad_actual == DatosEntregaCheckoutForm.MODALIDAD_DESPACHO
            else 0
        )

    total_estimado = subtotal + costo_despacho
    return render(
        request,
        "datos-entrega.html",
        {
            "form": form,
            "modalidad_actual": modalidad_actual,
            "subtotal": subtotal,
            "costo_despacho": costo_despacho,
            "costo_despacho_fijo": DatosEntregaCheckoutForm.COSTO_DESPACHO_FIJO,
            "total_estimado": total_estimado,
            "datos_guardados": request.session.get("datos_entrega_pedido"),
        },
    )
