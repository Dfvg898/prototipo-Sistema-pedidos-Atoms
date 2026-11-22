from .models import AvisoWhatsApp


def simular_aviso_whatsapp(pedido, evento, *, estado_anterior=None):
    if evento == "confirmacion":
        lineas = [f"Sandwichs Atom's recibió tu pedido {pedido.folio}."]
        for detalle in pedido.detalle.order_by("pk"):
            producto = f"{detalle.cantidad} × {detalle.nombre_producto}"
            if detalle.personalizacion:
                producto += f" ({detalle.personalizacion})"
            lineas.append(producto)
        return "\n".join(lineas)

    if evento == "listo":
        if pedido.estado != "LIST" or estado_anterior not in dict(pedido.ESTADOS) or estado_anterior == "LIST":
            return None
        if pedido.modalidad_entrega == "DESP":
            instruccion = "Tu pedido está preparado para despacho a domicilio."
        else:
            instruccion = "Puedes retirarlo en el local."
        return f"Tu pedido {pedido.folio} de Sandwichs Atom's está listo. {instruccion}"

    raise ValueError("Evento de WhatsApp desconocido.")


def registrar_aviso_whatsapp(pedido, evento, *, estado_anterior=None):
    if pedido._state.adding:
        raise ValueError("El pedido debe estar guardado.")
    mensaje = simular_aviso_whatsapp(pedido, evento, estado_anterior=estado_anterior)
    if mensaje is None:
        return None, False
    return AvisoWhatsApp.objects.using(pedido._state.db).get_or_create(
        folio=pedido.folio, evento=evento, defaults={"mensaje": mensaje},
    )
