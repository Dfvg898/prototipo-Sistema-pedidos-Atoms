from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalogo.models import Categoria, OpcionPersonalizacion, Producto
from usuarios.models import AvisoWhatsApp, Repartidor
from .models import AsignacionDespacho, Cliente, Pago, Pedido


class CheckoutTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nombre="Sándwiches")
        self.producto = Producto.objects.create(
            nombre="Sándwich Rayo", descripcion="Producto de prueba", precio_base=3500, categoria=categoria,
        )
        self.agregar = reverse("agregar_carrito", args=[self.producto.pk])

    def test_visitante_compra_dos_productos_y_registra_pago(self):
        self.assertContains(self.client.get(reverse("lista")), f'action="{self.agregar}"')
        self.assertEqual(self.client.get(self.agregar).status_code, 405)
        for _ in range(2):
            self.assertRedirects(self.client.post(self.agregar), reverse("ver_carrito"))
        self.assertContains(self.client.get(reverse("ver_carrito")), "7000")
        entrega = self.client.post(reverse("datos_entrega"), {
            "nombre_cliente": "Cliente de prueba", "telefono": "+56912345678",
            "modalidad_entrega": "DESPACHO", "direccion": "Calle de prueba 123",
        }, follow=True)
        self.assertContains(entrega, f'action="{reverse("crear_pedido")}"')
        self.assertEqual(self.client.get(reverse("crear_pedido")).status_code, 405)
        respuesta = self.client.post(reverse("crear_pedido"))
        pedido = Pedido.objects.get()
        url_pago = reverse("seleccionar_pago", args=[pedido.pk])
        self.assertRedirects(respuesta, url_pago)
        self.assertEqual(pedido.total, 9000)
        self.assertEqual(pedido.detalle.get().cantidad, 2)
        self.assertFalse(self.client.session["carrito"])
        self.assertEqual(self.client_class().get(url_pago).status_code, 404)
        self.assertRedirects(self.client.post(url_pago, {"medio_pago": "EFEC"}), url_pago)
        self.assertEqual(Pago.objects.get(pedido=pedido).medio_pago, "EFEC")
        self.assertRedirects(self.client.post(url_pago, {"medio_pago": "EFEC"}), url_pago)
        aviso = AvisoWhatsApp.objects.get(folio=pedido.folio, evento="confirmacion")
        self.assertIn("2 × Sándwich Rayo", aviso.mensaje)
        self.assertIsNone(aviso.simulado_en)

    def test_opciones_validas_actualizan_precio_y_las_ajenas_se_rechazan(self):
        opcion = OpcionPersonalizacion.objects.create(nombre="Extra", tipo="extra", precio_extra=500)
        ajena = OpcionPersonalizacion.objects.create(nombre="Otra", tipo="extra", precio_extra=500)
        opcion.productos.add(self.producto)
        self.assertRedirects(
            self.client.post(self.agregar, {"opciones": [opcion.pk], "cantidad": 2, "nota": "Cortar"}),
            reverse("ver_carrito"),
        )
        linea = self.client.session["carrito"][0]
        self.assertEqual(linea["subtotal"], 8000)
        self.assertEqual(linea["personalizacion"], "Extra, Cortar")
        self.client.post(self.agregar, {"opciones": [ajena.pk]})
        self.assertEqual(self.client.session["carrito"], [linea])


class AvisosPedidoTests(TestCase):
    def setUp(self):
        self.cajero = get_user_model().objects.create_user("caja@example.test", "Caja", rol="CAJERO")
        cliente = Cliente.objects.create(nombre="Cliente", telefono="12345678")
        self.pedido = Pedido.objects.create(cliente=cliente, estado="PREP")
        self.client.force_login(self.cajero)

    def test_transferencia_registra_aviso_solo_al_confirmarse(self):
        seleccionar = reverse("seleccionar_pago", args=[self.pedido.pk])
        self.assertRedirects(self.client.post(seleccionar, {"medio_pago": "TRAN"}), seleccionar)
        self.assertFalse(AvisoWhatsApp.objects.exists())
        pago = Pago.objects.get(pedido=self.pedido)
        confirmar = reverse("confirmar_pago_trans", args=[pago.pk])
        for _ in range(2):
            self.assertRedirects(self.client.post(confirmar), reverse("historial_pedidos"))
        self.assertEqual(AvisoWhatsApp.objects.get(folio=self.pedido.folio).evento, "confirmacion")

    def test_pedido_listo_registra_un_aviso_por_folio(self):
        cambiar = reverse("cambiar_estado", args=[self.pedido.pk])
        self.assertRedirects(self.client.post(cambiar, {"estado": "PREP"}), reverse("ver_pedidos"))
        self.assertFalse(AvisoWhatsApp.objects.exists())
        for estado in ("LIST", "LIST", "PREP", "LIST"):
            self.assertRedirects(self.client.post(cambiar, {"estado": estado}), reverse("ver_pedidos"))
        self.assertEqual(AvisoWhatsApp.objects.get(folio=self.pedido.folio).evento, "listo")


class DespachoRayoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.cajero = User.objects.create_user('caja@example.test', 'Caja', rol=User.Rol.CAJERO)
        self.externo = Repartidor.objects.create(nombre_repartidor='Rayo externo')
        self.perfil = Repartidor.objects.create(nombre_repartidor='Con cuenta')
        self.inactivo = Repartidor.objects.create(nombre_repartidor='Inactivo', activo=False)
        self.cuenta = User.objects.create_user(
            'rayo@example.test', 'Rayo', rol=User.Rol.REPARTIDOR, repartidor=self.perfil,
        )
        self.sin_perfil = User.objects.create_user('sin@example.test', 'Sin perfil', rol=User.Rol.REPARTIDOR)
        self.cliente = Cliente.objects.create(nombre='Cliente', telefono='12345678')

    def test_cajero_asigna_externo_y_reasignar_conserva_historial(self):
        pedido = Pedido.objects.create(cliente=self.cliente, modalidad_entrega='DESP')
        url = reverse('asignar_repartidor', args=[pedido.pk])
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'repartidor_id': self.inactivo.pk}).status_code, 404)
        for perfil in (self.externo, self.perfil):
            self.assertRedirects(
                self.client.post(url, {'repartidor_id': perfil.pk}), reverse('lista_delivery'),
            )
        pedido.refresh_from_db()
        self.assertEqual(pedido.repartidor, self.perfil)
        self.assertEqual(
            list(AsignacionDespacho.objects.order_by('pk').values_list('repartidor_id', flat=True)),
            [self.externo.pk, self.perfil.pk],
        )

    def test_cajero_actualiza_estado_sin_borrar_la_asignacion(self):
        pedido = Pedido.objects.create(cliente=self.cliente, modalidad_entrega='DESP')
        self.client.force_login(self.cajero)
        self.client.post(reverse('asignar_repartidor', args=[pedido.pk]), {'repartidor_id': self.externo.pk})
        self.assertRedirects(
            self.client.post(reverse('cambiar_estado', args=[pedido.pk]), {'estado': 'ECAM'}),
            reverse('ver_pedidos'),
        )
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, 'ECAM')
        self.assertEqual(pedido.asignaciones_despacho.get().estado_pedido, 'RECI')

    def test_repartidor_solo_ve_sus_pedidos_y_no_puede_asignar(self):
        propio = Pedido.objects.create(cliente=self.cliente, modalidad_entrega='DESP', repartidor=self.perfil)
        ajeno = Pedido.objects.create(cliente=self.cliente, modalidad_entrega='DESP', repartidor=self.externo)
        libre = Pedido.objects.create(cliente=self.cliente, modalidad_entrega='DESP')
        self.client.force_login(self.cuenta)
        response = self.client.get(reverse('lista_delivery'))
        self.assertContains(response, propio.folio)
        self.assertNotContains(response, ajeno.folio)
        self.assertNotContains(response, libre.folio)
        url = reverse('asignar_repartidor', args=[ajeno.pk])
        self.assertEqual(self.client.post(url, {'repartidor_id': self.perfil.pk}).status_code, 403)
        self.client.force_login(self.sin_perfil)
        self.assertNotContains(self.client.get(reverse('lista_delivery')), propio.folio)
