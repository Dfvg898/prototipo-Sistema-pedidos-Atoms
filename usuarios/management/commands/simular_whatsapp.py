from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from usuarios.models import AvisoWhatsApp
from usuarios.notificaciones import registrar_aviso_whatsapp, simular_aviso_whatsapp


class Command(BaseCommand):
    help = "Muestra una vista previa local del aviso de WhatsApp sin enviarlo."

    def add_arguments(self, parser):
        parser.add_argument("folio")
        parser.add_argument("evento", choices=("confirmacion", "listo"))
        parser.add_argument("--estado-anterior")
        parser.add_argument("--registrar", action="store_true", help="Guarda la simulación local una sola vez por evento.")

    def handle(self, *args, **options):
        if not apps.is_installed("pedidos"):
            raise CommandError("La aplicación pedidos debe estar instalada.")
        Pedido = apps.get_model("pedidos", "Pedido")
        pedido = Pedido.objects.filter(folio=options["folio"]).first()
        if pedido is None:
            raise CommandError("No se encontró el pedido.")
        estado_anterior = options["estado_anterior"]
        if options["evento"] == "listo" and estado_anterior not in dict(Pedido.ESTADOS):
            raise CommandError("Indica el estado anterior con --estado-anterior.")
        if options["registrar"]:
            aviso, _ = registrar_aviso_whatsapp(pedido, options["evento"], estado_anterior=estado_anterior)
            if aviso is None:
                raise CommandError("El pedido no tiene una transición válida a Listo.")
            actualizado = AvisoWhatsApp.objects.using(aviso._state.db).filter(
                pk=aviso.pk, simulado_en__isnull=True,
            ).update(
                simulado_en=timezone.now(),
            )
            if not actualizado:
                self.stdout.write("Este evento ya fue simulado.")
                return
            mensaje = aviso.mensaje
        else:
            mensaje = simular_aviso_whatsapp(pedido, options["evento"], estado_anterior=estado_anterior)
            if mensaje is None:
                raise CommandError("El pedido no tiene una transición válida a Listo.")
        self.stdout.write(mensaje)
