from io import StringIO
from unittest import skipUnless

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from .models import Usuario, Repartidor, BitacoraEvento, AvisoWhatsApp
from .notificaciones import registrar_aviso_whatsapp, simular_aviso_whatsapp
from .views import (
    MENSAJE_ERROR_GENERICO,
    EXPIRACION_SESION_CAJERO_SEG,
    EXPIRACION_SESION_REPARTIDOR_SEG,
)


class AutenticacionYSeguridadHUTests(TestCase):
    def setUp(self):
        self.password = "ClaveSeguraAtoms2026!"
        self.dueno = Usuario.objects.create_user(
            correo="dueno@atoms.cl",
            nombre="Dueño Atoms",
            password=self.password,
            rol=Usuario.Rol.DUENO,
        )
        self.cajero = Usuario.objects.create_user(
            correo="cajero@atoms.cl",
            nombre="Juan Cajero",
            password=self.password,
            rol=Usuario.Rol.CAJERO,
        )
        self.repartidor_perfil = Repartidor.objects.create(
            nombre_repartidor="Pedro Repartidor",
            telefono="+56911112222",
        )
        self.repartidor = Usuario.objects.create_user(
            correo="repartidor@atoms.cl",
            nombre="Pedro Repartidor",
            password=self.password,
            rol=Usuario.Rol.REPARTIDOR,
            repartidor=self.repartidor_perfil,
        )

    def test_login_carga_estilos_y_muestra_errores_de_campos(self):
        url = reverse("login")
        response = self.client.get(url)
        self.assertContains(response, 'href="/static/css/acceso.css"', count=1)
        self.assertContains(response, 'href="/static/catalogo/css/atoms.css"', count=1)

        response = self.client.post(url, {"correo": "correo-invalido", "password": ""})
        self.assertContains(response, MENSAJE_ERROR_GENERICO)
        self.assertContains(response, 'aria-invalid="true"', count=2)
        self.assertContains(response, 'id="error-correo"')
        self.assertContains(response, 'id="error-password"')

    def test_hu21_login_exitoso_expiracion_cajero_30_min(self):
        response = self.client.post(
            reverse("login"),
            {"correo": "cajero@atoms.cl", "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), EXPIRACION_SESION_CAJERO_SEG)
        self.assertTrue(
            BitacoraEvento.objects.filter(
                usuario=self.cajero,
                tipo=BitacoraEvento.TipoEvento.LOGIN_EXITOSO,
            ).exists()
        )

    def test_dueno_registra_repartidor_externo_y_cajero_no_administra_perfiles(self):
        self.client.force_login(self.dueno)
        url = reverse("usuarios_repartidores_crear")
        datos = {"nombre_repartidor": "Rayo", "telefono": "+56911112222", "activo": True}
        self.assertRedirects(self.client.post(url, datos), reverse("usuarios_repartidores"))
        perfil = Repartidor.objects.get(nombre_repartidor="Rayo")
        self.assertFalse(Usuario.objects.filter(repartidor=perfil).exists())
        self.client.force_login(self.cajero)
        self.assertEqual(self.client.post(url, datos).status_code, 403)

    def test_alta_repartidor_con_cuenta_permite_omitir_perfil_y_rechaza_otro_rol(self):
        self.client.force_login(self.dueno)
        url = reverse("usuarios_personal_crear")
        datos = {"nombre": "Nueva cuenta", "correo": "nueva@example.test", "rol": Usuario.Rol.REPARTIDOR,
                 "activo": True, "password": self.password}
        perfiles = Repartidor.objects.count()
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.assertIsNone(Usuario.objects.get(correo=datos["correo"]).repartidor_id)
        self.assertEqual(Repartidor.objects.count(), perfiles)
        perfil = Repartidor.objects.create(nombre_repartidor="Rayo")
        datos.update(correo="otro@example.test", rol=Usuario.Rol.CAJERO, repartidor=perfil.pk)
        response = self.client.post(url, datos)
        self.assertIn("repartidor", response.context["form"].errors)
        self.assertFalse(Usuario.objects.filter(correo=datos["correo"]).exists())

    def test_estado_del_perfil_es_independiente_y_borrar_cuenta_conserva_perfil(self):
        self.client.force_login(self.dueno)
        estado = reverse("usuarios_repartidores_estado", args=[self.repartidor_perfil.pk])
        self.assertEqual(self.client.post(estado).status_code, 302)
        self.repartidor.refresh_from_db()
        self.repartidor_perfil.refresh_from_db()
        self.assertTrue(self.repartidor.activo)
        self.assertFalse(self.repartidor_perfil.activo)
        eliminar = reverse("usuarios_personal_eliminar", args=[self.repartidor.pk])
        self.assertEqual(self.client.post(eliminar).status_code, 302)
        self.assertTrue(Repartidor.objects.filter(pk=self.repartidor_perfil.pk).exists())

    def test_editar_cuenta_vincula_y_desvincula_perfil_existente_inactivo(self):
        self.client.force_login(self.dueno)
        cuenta = Usuario.objects.create_user(
            "otra@example.test", "Cuenta de reparto", rol=Usuario.Rol.REPARTIDOR,
        )
        perfil = Repartidor.objects.create(nombre_repartidor="Rayo externo", activo=False)
        url = reverse("usuarios_personal_editar", args=[cuenta.pk])
        datos = {"nombre": cuenta.nombre, "correo": cuenta.correo, "rol": cuenta.rol, "activo": True}
        self.assertEqual(self.client.post(url, {**datos, "repartidor": perfil.pk}).status_code, 302)
        cuenta.refresh_from_db()
        perfil.refresh_from_db()
        self.assertEqual(cuenta.repartidor_id, perfil.pk)
        self.assertFalse(perfil.activo)
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        cuenta.refresh_from_db()
        self.assertIsNone(cuenta.repartidor_id)

    def test_borrar_perfil_sin_historial_desvincula_cuenta_sin_borrarla(self):
        self.client.force_login(self.dueno)
        url = reverse("usuarios_repartidores_eliminar", args=[self.repartidor_perfil.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.repartidor.refresh_from_db()
        self.assertIsNone(self.repartidor.repartidor_id)

    def test_entrega_renderiza_plantilla_propia_despues_de_guardar(self):
        url = reverse("datos_entrega")
        self.assertTemplateUsed(self.client.get(url), "usuarios/datos-entrega.html")
        response = self.client.post(url, {
            "nombre_cliente": "Cliente", "telefono": "+56911112222", "modalidad_entrega": "RETIRO",
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "usuarios/datos-entrega.html")

    def test_hu21_login_exitoso_expiracion_repartidor_60_min(self):
        response = self.client.post(
            reverse("login"),
            {"correo": "repartidor@atoms.cl", "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), EXPIRACION_SESION_REPARTIDOR_SEG)

    def test_hu21_bloqueo_fuerza_bruta_tras_5_intentos_fallidos(self):
        for _ in range(5):
            response = self.client.post(
                reverse("login"),
                {"correo": "cajero@atoms.cl", "password": "ClaveIncorrecta123"},
            )
            self.assertContains(response, MENSAJE_ERROR_GENERICO)

        self.cajero.refresh_from_db()
        self.assertEqual(self.cajero.intentos_fallidos, 5)
        self.assertTrue(self.cajero.esta_bloqueado())

        response_bloqueado = self.client.post(
            reverse("login"),
            {"correo": "cajero@atoms.cl", "password": self.password},
        )
        self.assertEqual(response_bloqueado.status_code, 200)
        self.assertContains(response_bloqueado, MENSAJE_ERROR_GENERICO)

    def test_hu20_acceso_denegado_403_a_rol_no_autorizado(self):
        self.client.force_login(self.repartidor)
        response = self.client.get(reverse("usuarios_personal"))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            BitacoraEvento.objects.filter(
                usuario=self.repartidor,
                tipo=BitacoraEvento.TipoEvento.ACCESO_DENEGADO,
            ).exists()
        )

    def test_hu20_dueno_puede_gestionar_personal_repartidores_y_bitacora(self):
        self.client.force_login(self.dueno)

        res_personal = self.client.get(reverse("usuarios_personal"))
        self.assertEqual(res_personal.status_code, 200)

        res_crear = self.client.post(
            reverse("usuarios_personal_crear"),
            {
                "nombre": "Nuevo Cajero",
                "correo": "nuevo@atoms.cl",
                "rol": Usuario.Rol.CAJERO,
                "activo": True,
                "password": "ClaveSeguraNueva2026!",
            },
        )
        self.assertEqual(res_crear.status_code, 302)
        self.assertTrue(Usuario.objects.filter(correo="nuevo@atoms.cl").exists())

        res_bitacora = self.client.get(reverse("usuarios_bitacora"))
        self.assertEqual(res_bitacora.status_code, 200)

    def test_hu05_hu07_hu08_hu27_datos_entrega_retiro_sin_direccion(self):
        response = self.client.post(
            reverse("datos_entrega"),
            {
                "nombre_cliente": "Camila Rojas",
                "telefono": "+56 9 1234 5678",
                "modalidad_entrega": "RETIRO",
                "direccion": "",
                "referencia": "",
                "observaciones": "Sin mayonesa y cortar en dos",
            },
        )
        self.assertEqual(response.status_code, 302)
        datos = self.client.session.get("datos_entrega_pedido")
        self.assertIsNotNone(datos)
        self.assertEqual(datos["nombre_cliente"], "Camila Rojas")
        self.assertEqual(datos["modalidad_entrega"], "RETIRO")
        self.assertEqual(datos["costo_despacho"], 0)
        self.assertEqual(datos["observaciones"], "Sin mayonesa y cortar en dos")

    def test_hu05_hu07_hu08_datos_entrega_despacho_calcula_costo(self):
        response = self.client.post(
            reverse("datos_entrega"),
            {
                "nombre_cliente": "Camila Rojas",
                "telefono": "+56 9 1234 5678",
                "modalidad_entrega": "DESPACHO",
                "direccion": "Av. Principal 1234",
                "referencia": "Casa azul frente a la plaza",
                "observaciones": "Tocar timbre",
            },
        )
        self.assertEqual(response.status_code, 302)
        datos = self.client.session.get("datos_entrega_pedido")
        self.assertEqual(datos["modalidad_entrega"], "DESPACHO")
        self.assertEqual(datos["direccion"], "Av. Principal 1234")
        self.assertEqual(datos["costo_despacho"], 2000)

    def test_hu06_hu08_bloquea_despacho_sin_direccion_y_marca_rojo(self):
        response = self.client.post(
            reverse("datos_entrega"),
            {
                "nombre_cliente": "Camila Rojas",
                "telefono": "",
                "modalidad_entrega": "DESPACHO",
                "direccion": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "is-invalid")
        self.assertContains(
            response,
            "La dirección de entrega es obligatoria cuando eliges despacho a domicilio.",
        )


@skipUnless(apps.is_installed("pedidos"), "Requiere la aplicación pedidos.")
class NotificacionesPedidoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from catalogo.models import Categoria, Producto
        from pedidos.models import Cliente, DetallePedido, Pedido

        cls.cajero = Usuario.objects.create_user(
            "caja@example.test", "Caja", "UnaClaveDePrueba!", rol=Usuario.Rol.CAJERO,
        )
        cls.dueno = Usuario.objects.create_user("dueno@example.test", "Dueño", rol=Usuario.Rol.DUENO)
        cls.repartidor = Usuario.objects.create_user("rayo@example.test", "Rayo", rol=Usuario.Rol.REPARTIDOR)
        cliente = Cliente.objects.create(nombre="Cliente privado", telefono="+56987654321")
        categoria = Categoria.objects.create(nombre="Sándwiches")
        producto = Producto.objects.create(categoria=categoria, nombre="Barros Luco", precio_base=3500)
        cls.recibido = Pedido.objects.create(cliente=cliente, estado="RECI")
        cls.listo = Pedido.objects.create(cliente=cliente, estado="LIST")
        DetallePedido.objects.create(
            pedido=cls.recibido, producto=producto, nombre_producto="Barros Luco",
            precio_unitario=3500, cantidad=2, personalizacion="sin tomate",
        )

    def test_alertas_filtran_estado_y_restringen_acceso(self):
        panel = reverse("usuarios_alertas_pedidos")
        self.assertEqual(self.client.get(panel).status_code, 302)
        self.client.force_login(self.repartidor)
        self.assertEqual(self.client.get(panel).status_code, 403)
        for cuenta in (self.dueno, self.cajero):
            self.client.force_login(cuenta)
            self.assertContains(self.client.get(panel), self.recibido.folio)
            self.assertEqual(self.client.post(panel).status_code, 405)

        # Un pedido que pasa a preparación ya no aparece en la lista
        self.recibido.estado = "PREP"
        self.recibido.save(update_fields=["estado"])
        self.assertNotContains(self.client.get(panel), self.recibido.folio)

    def test_cajero_llega_al_panel_tras_iniciar_sesion(self):
        respuesta = self.client.post(reverse("login"), {
            "correo": self.cajero.correo, "password": "UnaClaveDePrueba!",
        })
        self.assertRedirects(respuesta, reverse("usuarios_alertas_pedidos"))

    def test_simulador_confirma_folio_cantidad_y_personalizacion(self):
        salida = StringIO()
        call_command("simular_whatsapp", self.recibido.folio, "confirmacion", stdout=salida)
        mensaje = salida.getvalue()
        self.assertIn(self.recibido.folio, mensaje)
        self.assertIn("2 × Barros Luco (sin tomate)", mensaje)
        self.assertNotIn("+56987654321", mensaje)
        self.assertFalse(AvisoWhatsApp.objects.exists())

    def test_registro_evitar_duplicados_y_conservar_eventos_distintos(self):
        aviso, creado = registrar_aviso_whatsapp(self.listo, "confirmacion")
        self.assertTrue(creado)
        repetido, creado = registrar_aviso_whatsapp(self.listo, "confirmacion")
        self.assertFalse(creado)
        self.assertEqual(aviso.pk, repetido.pk)
        self.assertEqual(registrar_aviso_whatsapp(self.listo, "listo", estado_anterior="LIST"), (None, False))
        self.assertTrue(registrar_aviso_whatsapp(self.listo, "listo", estado_anterior="PREP")[1])
        self.assertEqual(AvisoWhatsApp.objects.filter(folio=self.listo.folio).count(), 2)

    def test_transaccion_fallida_no_deja_aviso_pendiente(self):
        with self.assertRaisesMessage(RuntimeError, "Error de guardado"):
            with transaction.atomic():
                registrar_aviso_whatsapp(self.recibido, "confirmacion")
                raise RuntimeError("Error de guardado")
        self.assertFalse(AvisoWhatsApp.objects.exists())

    def test_simular_registrando_procesa_solo_una_vez(self):
        salida = StringIO()
        call_command("simular_whatsapp", self.recibido.folio, "confirmacion", registrar=True, stdout=salida)
        self.assertIn(self.recibido.folio, salida.getvalue())
        self.assertIsNotNone(AvisoWhatsApp.objects.get().simulado_en)
        salida = StringIO()
        call_command("simular_whatsapp", self.recibido.folio, "confirmacion", registrar=True, stdout=salida)
        self.assertIn("ya fue simulado", salida.getvalue())
        self.assertEqual(AvisoWhatsApp.objects.count(), 1)

    def test_aviso_listo_requiere_transicion_y_distingue_modalidad(self):
        self.assertIsNone(simular_aviso_whatsapp(self.recibido, "listo", estado_anterior="PREP"))
        self.assertIsNone(simular_aviso_whatsapp(self.listo, "listo", estado_anterior="LIST"))
        self.assertIn("retirarlo en el local", simular_aviso_whatsapp(self.listo, "listo", estado_anterior="PREP"))
        self.listo.modalidad_entrega = "DESP"
        self.assertIn("despacho a domicilio", simular_aviso_whatsapp(self.listo, "listo", estado_anterior="PREP"))
        with self.assertRaises(CommandError):
            call_command("simular_whatsapp", self.listo.folio, "listo", estado_anterior="LIST")
