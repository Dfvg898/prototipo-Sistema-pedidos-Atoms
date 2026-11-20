import uuid
from django.db import models
from django.conf import settings
from catalogo.models import Producto
# Create your models here.

def generar_folio():
    return f"ATOM-{uuid.uuid4().hex[:16].upper()}"

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    correo = models.EmailField(blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    ESTADOS = [
        ('RECI', 'Recibido'),
        ('PREP', 'En preparacion'),
        ('LIST', 'List'),
        ('ECAM', 'En camino'),
        ('ENTR', 'Entregado'),
        ('CANC', 'Cancelado'),
    ]

    MODALIDADES = [
        ('LOCA', 'Retiro en local'),
        ('DESP', 'Despacho a domicilio'),
    ]

    ORIGENES = [
        ('WEB','Tienda Online'),
        ('MESO','Mesón'),
        ('WHAT','WhatsApp'),
    ]

    folio = models.CharField(max_length=21, unique=True, default=generar_folio, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='Pedidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    origen = models.CharField(max_length=15, choices=ORIGENES, default='WEB')
    modalidad_entrega = models.CharField(max_length=10, choices=MODALIDADES, default='LOCA')
    direccion_entrega = models.CharField(max_length=200, blank=True)
    referencia = models.CharField(max_length=200, blank=True)
    observaciones = models.TextField(blank=True)
    costo_despacho = models.PositiveBigIntegerField(default=0)
    total = models.PositiveBigIntegerField(default=0)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='RECI')
    repartidor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='Pedidos_asignados')

    def calcular_total(self):
        subtotal = 0

        for detalle in self.detalles.all():
            subtotal += detalle.costo_despacho
        return subtotal + self.costo_despacho

    def __str__(self):
        return f"Pedido {self.folio}"


class DetallePedido(models.Model):
    pedido =models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalle')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name='detalles_pedido')

    nombre_producto = models.CharField(max_length=100)
    precio_unitario = models.PositiveBigIntegerField()
    cantidad = models.PositiveBigIntegerField(default=1)
    personalizacion = models.TextField(blank=True)

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f"{self.cantidad} X {self.nombre_producto}"


class Pago(models.Model):
    MEDIOS_PAGO = [
        ('EFEC', 'Efectivo'),
        ('TRANS', 'Transferencia'),
        ('TARJ', 'Tarjeta / Mercado Pago'),
    ]

    ESTADO_PAGO = [
        ('PEND','Pendiente'),
        ('VERI','Pendiente en verificacion'),
        ('PAGA','Pagado'),
        ('RECH','Rechazado'),
    ]

    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='pago')
    medio_pago = models.CharField(max_length=15, choices=MEDIOS_PAGO)
    estado = models.CharField(max_length=15, choices=ESTADO_PAGO, default='PEND')
    monto = models.PositiveBigIntegerField()
    referencia_transferencia = models.CharField(max_length=100, blank=True)
    fecha_registro = models.DateTimeField(null=True, blank=True)
    verificado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_verificados')

    def __str__(self):
        return f"Pago del pedido {self.pedido.folio}"