from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_POST
from .models import Pedido, Pago
from usuarios.decorators import rol_requerido
from usuarios.models import Usuario, Repartidor
# Create your views here.

#Listar Pedidos
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
def ver_pedidos(request):
    #Consulta el pedido segun su estado
    pedidos_recibidos = Pedido.objects.filter(
        estado='RECIBIDO'
    ).order_by('fecha_creacion')

    pedidos_preparacion = Pedido.objects.filter(
        estado='PREPARACION'
    ).order_by('fecha_creacion')

    pedidos_listos = Pedido.objects.filter(
        estado='LISTO'
    ).order_by('fecha_creacion')

    pedidos_camino = Pedido.objects.filter(
        estado='EN_CAMINO'
    ).order_by('fecha_creacion')

    #Se envia el pedido a la plantilla html
    return render(request, 'pedidos/pedido.html', {
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
        pedidos = pedidos.filter(Q(folio__icontains=busqueda) | Q(cliente__nombre_icontains=busqueda))
    #se refleja los resultados al html
    return render(request, 'pedidos/histotial.html', {
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
        medios_validos = [medio[0] for medio in pago.MEDIOS_PAGO]
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
                    'estado_pago':estado_pago,
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
        'medios_pado':Pago.MEDIOS_PAGO,
    })

#confirmar pago por transferencia
@rol_requerido(Usuario.Rol.DUENO, Usuario.Rol.CAJERO)
@require_POST
def confirmar_pago_trans(request, pago_id):
    pago = get_object_or_404(Pago, pk=pago_id)

    if (pago.medio_pago == 'TRAN' and pago.estado == 'VERI'):
        pago.estado = 'PAGA'
        pago.fecha_confirmacion = timezone.now()
        pago.verificado_por = request.user

        pago.save()
        messages.success(request, 'La transferencia fue confirmada correctamente')
    else:
        messages.error(request,'Este pago no está pendiente de verificación')
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

            for producto in pedido.detalles.all():
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
    