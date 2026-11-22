from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone


class Repartidor(models.Model):
    id_repartidor = models.AutoField(primary_key=True)
    nombre_repartidor = models.CharField(
        max_length=100,
        verbose_name="Nombre del repartidor",
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono de contacto",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Repartidor activo",
    )

    class Meta:
        db_table = "Repartidor"
        verbose_name = "Repartidor"
        verbose_name_plural = "Repartidores"

    def __str__(self):
        return self.nombre_repartidor


class UsuarioManager(BaseUserManager):
    def create_user(self, correo, nombre, password=None, **extra_fields):
        if not correo:
            raise ValueError("El correo electrónico es obligatorio.")

        correo = self.normalize_email(correo).lower()
        usuario = self.model(correo=correo, nombre=nombre, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, nombre, password=None, **extra_fields):
        extra_fields.setdefault("rol", Usuario.Rol.DUENO)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("activo", True)

        return self.create_user(correo, nombre, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        DUENO = "DUENO", "Administrador (Dueño)"
        CAJERO = "CAJERO", "Cajero"
        REPARTIDOR = "REPARTIDOR", "Repartidor"

    id_usuario = models.AutoField(primary_key=True)
    correo = models.EmailField(
        unique=True,
        max_length=150,
        verbose_name="Correo electrónico",
    )
    nombre = models.CharField(
        max_length=100,
        verbose_name="Nombre completo",
    )
    rol = models.CharField(
        max_length=15,
        choices=Rol.choices,
        default=Rol.CAJERO,
        verbose_name="Rol en el sistema",
    )
    repartidor = models.OneToOneField(
        Repartidor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cuenta_usuario",
        verbose_name="Perfil de repartidor asociado",
    )
    activo = models.BooleanField(
        default=True,
        verbose_name="Cuenta activa",
    )
    intentos_fallidos = models.PositiveIntegerField(
        default=0,
        verbose_name="Intentos fallidos de inicio de sesión",
    )
    bloqueado_hasta = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Bloqueado temporalmente hasta",
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Acceso al admin de Django",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        db_table = "Usuario_Personal"
        verbose_name = "Usuario del Personal"
        verbose_name_plural = "Usuarios del Personal"

    def __str__(self):
        return f"{self.nombre} ({self.get_rol_display()}) - {self.correo}"

    @property
    def is_active(self):
        return self.activo

    MAX_INTENTOS_FALLIDOS = 5
    MINUTOS_BLOQUEO = 15

    def clean(self):
        super().clean()
        if self.repartidor_id and self.rol != self.Rol.REPARTIDOR:
            raise ValidationError({"repartidor": "Solo una cuenta con rol repartidor puede vincularse a un perfil."})

    def esta_bloqueado(self) -> bool:
        if self.bloqueado_hasta:
            if timezone.now() < self.bloqueado_hasta:
                return True
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return False

    def registrar_intento_fallido(self) -> bool:
        self.intentos_fallidos += 1
        bloqueado_ahora = False

        if self.intentos_fallidos >= self.MAX_INTENTOS_FALLIDOS:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=self.MINUTOS_BLOQUEO)
            bloqueado_ahora = True

        self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return bloqueado_ahora

    def resetear_intentos(self):
        if self.intentos_fallidos > 0 or self.bloqueado_hasta is not None:
            self.intentos_fallidos = 0
            self.bloqueado_hasta = None
            self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])


class BitacoraEvento(models.Model):
    class TipoEvento(models.TextChoices):
        LOGIN_EXITOSO = "LOGIN_EXITOSO", "Inicio de sesión exitoso"
        LOGIN_FALLIDO = "LOGIN_FALLIDO", "Intento de inicio de sesión fallido"
        CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA", "Cuenta bloqueada por fuerza bruta (15 min)"
        LOGOUT = "LOGOUT", "Cierre de sesión"
        ACCESO_DENEGADO = "ACCESO_DENEGADO", "Acceso denegado por rol (HTTP 403)"
        CAMBIO_ESTADO_PEDIDO = "CAMBIO_ESTADO_PEDIDO", "Cambio de estado de pedido"
        CONFIRMACION_PAGO = "CONFIRMACION_PAGO", "Confirmación de pago por transferencia"

    id_evento = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_bitacora",
        verbose_name="Usuario asociado",
    )
    id_pedido = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="ID de pedido referenciado (si aplica)",
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoEvento.choices,
        verbose_name="Tipo de evento",
    )
    descripcion = models.CharField(
        max_length=255,
        verbose_name="Descripción del evento",
    )
    ip_origen = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dirección IP",
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y hora del evento",
    )

    class Meta:
        db_table = "bitacora_eventos"
        ordering = ["-fecha_hora"]
        verbose_name = "Evento de Bitácora"
        verbose_name_plural = "Bitácora de Eventos"

    def __str__(self):
        return f"[{self.fecha_hora:%Y-%m-%d %H:%M}] {self.get_tipo_display()} - {self.descripcion}"


class AvisoWhatsApp(models.Model):
    class Evento(models.TextChoices):
        CONFIRMACION = "confirmacion", "Confirmación"
        LISTO = "listo", "Pedido listo"

    folio = models.CharField(max_length=21)
    evento = models.CharField(max_length=12, choices=Evento.choices)
    mensaje = models.TextField()
    creado_en = models.DateTimeField(auto_now_add=True)
    simulado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["folio", "evento"], name="usuarios_aviso_folio_evento_unico"),
        ]
