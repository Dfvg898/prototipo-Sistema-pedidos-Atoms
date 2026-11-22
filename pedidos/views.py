from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from .models import Cliente, DetallePedido, Pedido, Pago
from usuarios.decorators import rol_requerido
from usuarios.models import Usuario, Repartidor
from catalogo.models import Producto, OpcionPersonalizacion
from django.db import transaction
# Create your views here.

#Listar Pedidos
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
def ver_pedidos(request):
    #Consulta el pedido segun su estado
    pedidos_recibidos = Pedido.objects.filter(
        estado='RECI'
    ).order_by('fecha_creacion')

    pedidos_preparacion = Pedido.objects.filter(
        estado='PREP'
    ).order_by('fecha_creacion')

    pedidos_listos = Pedido.objects.filter(
        estado='LIST'
    ).order_by('fecha_creacion')

    pedidos_camino = Pedido.objects.filter(
        estado='ECAM'
    ).order_by('fecha_creacion')

    #Se envia el pedido a la plantilla html
    return render(request, "pedidos/pedido.html", {
        'pedidos_recibidos': pedidos_recibidos,
        'pedidos_preparacion': pedidos_preparacion,
        'pedidos_listos': pedidos_listos,
        'pedidos_camino': pedidos_camino,
    })

#Cambiar estado del pedido
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
@require_POST
def cambiar_estado(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    #se busca pedido
    nuevo_estado = request.POST.get('estado')
    #se comprueba que exista
    estados_validos = [estado[Q] for estado in Pedido.ESTADOS]
    if nuevo_estado in estados_validos:
        pedido.estado = nuevo_estado

        #en caso que se cancele se guarda con un motivo
        if nuevo_estado == 'CANC':
            motivo = request.POST.get('motivo_cancelacion', '').strip()

            if motivo:
                pedido.observaciones += '\nMotivo: ' + motivo
        pedido.save()
        messages.success(request, 'El estado del pedido fue actualizado correctamente')

    else:
        messages.error(request, 'El estado seleccionado no es vàlido')
    return redirect('ver_pedidos')

#historial de pedido
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
def historial_pedidos(request):
    #se busca todos los pedidos
    pedidos = Pedido.objects.all().order_by('-fecha_creacion')
    #se obtiene los filtros del formulario
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    busqueda = request.GET.get('busqueda', '')

    #filtrar por fecha de inicial-final-folio o nombre
    if fecha_inicio:
        pedidos = pedidos.filter(fecha_creacion__date__gte=fecha_inicio)
    if fecha_fin:
        pedidos = pedidos.filter(fecha_creacion__date__lte=fecha_fin)
    if busqueda:
        pedidos = pedidos.filter(Q(folio__icontains=busqueda) | Q(cliente__nombre__icontains=busqueda))
    #se refleja los resultados al html
#se refleja los resultados al html
    return render(request, 'pedidos/historial.html', {
        'pedidos': pedidos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'busqueda': busqueda,
    })
#medios de pago
def seleccionar_pago(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    pago = Pago.objects.filter(pedido=pedido).first()#buscar el pedido si ya tiene pago registrado

    if request.method == 'POST':
        medio_pago = request.POST.get('medio_pago')
        #validamos el medio de pago 
        medios_validos = [medio[0] for medio in Pago.MEDIOS_PAGO]
        #se queda en pendiente la trasferencia para su verificacion
        if medio_pago in medios_validos:
            if medio_pago == 'TRAN':
                estado_pago = 'VERI'
            else:
                estado_pago = 'PEND'

            pago, creado = Pago.objects.update_or_create(
                pedido=pedido,
                defaults={
                    'medio_pago':medio_pago,
                    'estado':estado_pago,
                    'monto':pedido.total,
                    'referencia_transferencia':request.POST.get(
                        'referencia_transferencia', '').strip()
                })
            messages.success(request, 'El medio de pago fue registrado correctamente')
            return redirect('seleccionar_pago',pedido_id=pedido.id)
        else:
            messages.error(request, 'Selecciona un medio de pago válido')
    return render(request, 'pedidos/pagos.html',{
        'pedido':pedido,
        'pago':pago,
        'medios_pago':Pago.MEDIOS_PAGO,
    })

#confirmar pago por transferencia
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
@require_POST

@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
@require_POST
def confirmar_pago_trans(request, pago_id):
    pago = get_object_or_404(Pago, pk=pago_id)

    if pago.medio_pago == 'TRAN' and pago.estado == 'VERI':
        pago.estado = 'PAGA'
        pago.fecha_registro = timezone.now()
        pago.verificado_por = request.user

        pago.save()

        messages.success(
            request,
            'La transferencia fue confirmada correctamente'
        )
    else:
        messages.error(
            request,
            'Este pago no está pendiente de verificación'
        )

    return redirect('historial_pedidos')


#listar pedidos delivery
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO, Usuario.Rol.REPARTIDOR)
def lista_delivery(request):
    #buscamos pedidos con despacho
    pedidos = Pedido.objects.filter(
        modalidad_entrega='DESP').exclude(estado__in=['ENTR', 'CANC']).order_by('fecha_creacion')
    #validamos si el usuario es repartidor para mostrarle los pedidos que hay
    if request.user.rol == Usuario.Rol.REPARTIDOR:
        if request.user.repartidor:
            pedidos = pedidos.filter(repartidor=request.user.repartidor)
        else:
            pedidos = Pedido.objects.none()
    repartidores = Repartidor.objects.filter(activo=True)
    return render(request, 'pedidos/delivery.html',{
        'pedidos': pedidos,
        'repartidores': repartidores,
    })

#asignar repartidor
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
@require_POST
def asignar_repartidor(request, pedido_id):
    #se busca el pedido y si no encuentra nada devuelve con un error
    pedido = get_object_or_404(Pedido, pk=pedido_id)
    #Obtenemos el repartidor seleccionado
    repartidor_id = request.POST.get('repartidor_id')

    if pedido.modalidad_entrega != 'DESP':
        messages.error(request,'Este pedido no necesita repartidor')
        return redirect('lista_delivery')
    if repartidor_id:
        repartidor = get_object_or_404(Repartidor, pk=repartidor_id, activo=True)

        pedido.repartidor = repartidor
        pedido.save()
        messages.success(request, 'Repartidor asignado correctamente')
    else:
        messages.error(request, 'Debes seleccionar un repartidor')
    return redirect('lista_delivery')

#notificaciones
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
def notificaciones_pedidos(request):
    #consultamos los pedidos recientes
    pedidos = Pedido.objects.all().order_by('-fecha_creacion')[:50]
    folio = request.GET.get('folio', '')
    pedido = None
    mensaje = ''
    #aqui buscamos el pedido seleccionado
    if folio:
        pedido = Pedido.objects.filter(folio=folio).first()

        if pedido:
            detalle = ''

            for producto in pedido.detalle.all():
                detalle += (
                    f'{producto.cantidad} X ' f'{producto.nombre_producto},')
            mensaje = (
                f'Hola {pedido.cliente.nombre}, '
                f'recibimos tu pedido {pedido.folio}. '
                f'Detalle: {detalle}. '
                f'Gracias por preferir ATOMS '
            )
        else:
            messages.error(request, 'No se encontró el pedido')
    return render(request, 'pedidos/notificaciones.html',{
        'pedidos': pedidos,
        'pedido': pedido,
        'mensaje': mensaje,
    })    

@rol_requerido
def agregar_carrito(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    carrito = request.session.get('carrito', [])
    encontrado = False

    for item in carrito:
        if item['producto_id'] == producto.id:
            item['cantidad'] += 1
            item['subtotal'] += item['cantidad'] * item['precio_unitario']
            encontrado = True

    if not encontrado:
        item = {
            'producto_id': producto.id,
            'nombre_producto': producto.nombre,
            'precio_unitario': producto.precio_base,
            'cantidad': 1,
            'personalizacion': '',
            'subtotal': producto.precio_base
        }

        carrito.append(item)
    request.session['carrito'] = carrito
    return redirect('lista')

def crear_pedido(request):
    carrito = request.session.get('carrito', [])
    datos = request.session.get('datos_entrega_pedido', {})

    if not carrito:
        messages.error(request, 'Tu carrito está vacío')
        return redirect('lista')
    if not datos:
        messages.error(request, 'Primero debes ingresar tus datos de entrega')
        return redirect('datos_entrega')

    productos_pedido = []
    subtotal = 0

    for item in carrito:
        producto = Producto.objects.filter(pk=item.get('producto_id'), activo=True).first()

        if producto is None:
            messages.error(request, 'Uno de los productos ya no está disponible')
            return redirect('lista')
        try:
            cantidad = int(item.get('cantidad', 1))
            precio = int(item.get('precio_unitario', producto.precio_base))
        except (TypeError, ValueError):
            messages.error(request, 'Hay datos incorrectos en el carrito')
            return redirect('lista')

        if cantidad <= 0 or precio < 0:
            messages.error(request, 'La cantidad o el precio no son válidos')
            return redirect('lista')

        productos_pedido.append({
            'producto': producto,
            'nombre': item.get('nombre_producto', producto.nombre),
            'precio': precio,
            'cantidad': cantidad,
            'personalizacion': item.get('personalizacion', '')})
        
        subtotal += precio * cantidad


def crear_pedido(request):
    datos = request.session.get('datos_entrega_pedido')
    carrito = request.session.get('carrito', [])

    if not datos or not carrito:
        messages.error(
            request,
            'No hay datos de entrega o productos para crear el pedido.'
        )
        return redirect('lista')

    subtotal = 0
    productos_validos = []

    for item in carrito:
        producto = Producto.objects.filter(
            pk=item.get('producto_id'),
            activo=True
        ).first()

        if producto is None:
            messages.error(
                request,
                'Uno de los productos del carrito ya no está disponible.'
            )
            return redirect('lista')

        cantidad = int(item.get('cantidad', 1))
        precio = int(item.get('precio_unitario', producto.precio_base))

        if cantidad < 1 or precio < 0:
            messages.error(request, 'Hay un producto con datos inválidos.')
            return redirect('lista')

        subtotal += precio * cantidad
        productos_validos.append((item, producto, cantidad, precio))

    costo_despacho = int(datos.get('costo_despacho', 0))
    total = subtotal + costo_despacho

    if datos.get('modalidad_entrega') == 'DESPACHO':
        modalidad = 'DESP'
    else:
        modalidad = 'LOCA'

    with transaction.atomic():
        cliente = Cliente.objects.create(
            nombre=datos.get('nombre_cliente', ''),
            telefono=datos.get('telefono', ''),
            correo=''
        )

        pedido = Pedido.objects.create(
            cliente=cliente,
            origen='WEB',
            modalidad_entrega=modalidad,
            direccion_entrega=datos.get('direccion', ''),
            referencia=datos.get('referencia', ''),
            observaciones=datos.get('observaciones', ''),
            costo_despacho=costo_despacho,
            total=total
        )

        for item, producto, cantidad, precio in productos_validos:
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                nombre_producto=item.get('nombre_producto', producto.nombre),
                precio_unitario=precio,
                cantidad=cantidad,
                personalizacion=item.get('personalizacion', '')
            )

    request.session['carrito'] = []
    request.session.pop('datos_entrega_pedido', None)
    request.session.pop('subtotal_carrito', None)

    messages.success(request, 'Tu pedido fue creado correctamente.')
    return redirect('seleccionar_pago', pedido_id=pedido.id)
