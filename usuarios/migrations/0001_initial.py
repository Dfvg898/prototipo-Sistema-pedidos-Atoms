import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Repartidor',
            fields=[
                ('id_repartidor', models.AutoField(primary_key=True, serialize=False)),
                ('nombre_repartidor', models.CharField(max_length=100, verbose_name='Nombre del repartidor')),
                ('telefono', models.CharField(blank=True, max_length=20, verbose_name='Teléfono de contacto')),
                ('activo', models.BooleanField(default=True, verbose_name='Repartidor activo')),
            ],
            options={
                'verbose_name': 'Repartidor',
                'verbose_name_plural': 'Repartidores',
                'db_table': 'Repartidor',
            },
        ),
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('id_usuario', models.AutoField(primary_key=True, serialize=False)),
                ('correo', models.EmailField(max_length=150, unique=True, verbose_name='Correo electrónico')),
                ('nombre', models.CharField(max_length=100, verbose_name='Nombre completo')),
                ('rol', models.CharField(choices=[('DUENO', 'Administrador (Dueño)'), ('CAJERO', 'Cajero'), ('REPARTIDOR', 'Repartidor')], default='CAJERO', max_length=15, verbose_name='Rol en el sistema')),
                ('activo', models.BooleanField(default=True, verbose_name='Cuenta activa')),
                ('intentos_fallidos', models.PositiveIntegerField(default=0, verbose_name='Intentos fallidos de inicio de sesión')),
                ('bloqueado_hasta', models.DateTimeField(blank=True, null=True, verbose_name='Bloqueado temporalmente hasta')),
                ('is_staff', models.BooleanField(default=False, verbose_name='Acceso al admin de Django')),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
                ('repartidor', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='cuenta_usuario', to='usuarios.repartidor', verbose_name='Perfil de repartidor asociado')),
            ],
            options={
                'verbose_name': 'Usuario del Personal',
                'verbose_name_plural': 'Usuarios del Personal',
                'db_table': 'Usuario_Personal',
            },
        ),
        migrations.CreateModel(
            name='BitacoraEvento',
            fields=[
                ('id_evento', models.AutoField(primary_key=True, serialize=False)),
                ('id_pedido', models.IntegerField(blank=True, null=True, verbose_name='ID de pedido referenciado (si aplica)')),
                ('tipo', models.CharField(choices=[('LOGIN_EXITOSO', 'Inicio de sesión exitoso'), ('LOGIN_FALLIDO', 'Intento de inicio de sesión fallido'), ('CUENTA_BLOQUEADA', 'Cuenta bloqueada por fuerza bruta (15 min)'), ('LOGOUT', 'Cierre de sesión'), ('ACCESO_DENEGADO', 'Acceso denegado por rol (HTTP 403)'), ('CAMBIO_ESTADO_PEDIDO', 'Cambio de estado de pedido'), ('CONFIRMACION_PAGO', 'Confirmación de pago por transferencia')], max_length=30, verbose_name='Tipo de evento')),
                ('descripcion', models.CharField(max_length=255, verbose_name='Descripción del evento (sin datos sensibles)')),
                ('ip_origen', models.GenericIPAddressField(blank=True, null=True, verbose_name='Dirección IP')),
                ('fecha_hora', models.DateTimeField(auto_now_add=True, verbose_name='Fecha y hora del evento')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='eventos_bitacora', to=settings.AUTH_USER_MODEL, verbose_name='Usuario asociado')),
            ],
            options={
                'verbose_name': 'Evento de Bitácora',
                'verbose_name_plural': 'Bitácora de Eventos',
                'db_table': 'bitacora_eventos',
                'ordering': ['-fecha_hora'],
            },
        ),
    ]
