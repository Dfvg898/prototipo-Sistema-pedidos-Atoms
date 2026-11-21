from django.test import TestCase
from django.urls import reverse
from .models import Usuario, Repartidor, BitacoraEvento
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
