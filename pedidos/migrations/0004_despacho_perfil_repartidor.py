from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copiar_asignaciones(apps, schema_editor):
    Pedido = apps.get_model('pedidos', 'Pedido')
    Asignacion = apps.get_model('pedidos', 'AsignacionDespacho')
    alias = schema_editor.connection.alias
    pedidos = Pedido.objects.using(alias).exclude(repartidor_cuenta_anterior_id=None)
    pedidos = pedidos.select_related('repartidor_cuenta_anterior')
    for pedido in pedidos.iterator():
        cuenta = pedido.repartidor_cuenta_anterior
        if cuenta.rol != 'REPARTIDOR' or not cuenta.repartidor_id:
            raise RuntimeError(f'Pedido {pedido.pk}: revisar cuenta de reparto antes de migrar.')
        pedido.repartidor_id = cuenta.repartidor_id
        pedido.save(using=alias, update_fields=['repartidor'])
        Asignacion.objects.using(alias).create(
            pedido_id=pedido.pk, repartidor_id=cuenta.repartidor_id, estado_pedido=pedido.estado
        )


class Migration(migrations.Migration):
    dependencies = [
        ('pedidos', '0003_alter_pago_medio_pago_alter_pedido_estado'),
        ('usuarios', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='pedido', old_name='repartidor', new_name='repartidor_cuenta_anterior',
        ),
        migrations.AddField(
            model_name='pedido', name='repartidor',
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name='pedidos_asignados', to='usuarios.repartidor',
            ),
        ),
        migrations.CreateModel(
            name='AsignacionDespacho',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estado_pedido', models.CharField(choices=[
                    ('RECI', 'Recibido'), ('PREP', 'En preparacion'), ('LIST', 'Listo'),
                    ('ECAM', 'En camino'), ('ENTR', 'Entregado'), ('CANC', 'Cancelado'),
                ], max_length=15)),
                ('registrada_en', models.DateTimeField(auto_now_add=True)),
                ('asignado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('pedido', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='asignaciones_despacho', to='pedidos.pedido')),
                ('repartidor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='usuarios.repartidor')),
            ],
        ),
        migrations.RunPython(copiar_asignaciones),
    ]
