import secrets

from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from usuarios.models import Repartidor


class Command(BaseCommand):
    help = "Carga un producto y cuentas ficticias para la demostración local."

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("La demostración requiere DEBUG.")
        Categoria = apps.get_model("catalogo", "Categoria")
        Producto = apps.get_model("catalogo", "Producto")
        categoria, _ = Categoria.objects.get_or_create(nombre="Demo ATOMS", defaults={"activa": True})
        producto, _ = Producto.objects.get_or_create(
            categoria=categoria, nombre="Sándwich de demostración",
            defaults={"precio_base": 3500, "descripcion": "Producto ficticio para revisar el checkout.", "activo": True},
        )
        User = get_user_model()
        for rol in (User.Rol.DUENO, User.Rol.CAJERO, User.Rol.REPARTIDOR):
            correo = f"{rol.lower()}.demo@example.test"
            if User.objects.filter(correo=correo).exists():
                self.stdout.write(f"{correo} ya existe; se conserva su contraseña.")
                continue
            password = secrets.token_urlsafe(15)
            perfil = Repartidor.objects.create(nombre_repartidor="Rayo de demostración") if rol == User.Rol.REPARTIDOR else None
            User.objects.create_user(correo, f"{rol.label} de demostración", password, rol=rol, repartidor=perfil)
            self.stdout.write(f"{correo} | {password}")
        self.stdout.write(f"Producto de demostración: {producto.nombre}")
