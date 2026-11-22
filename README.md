# Sandwichs Atom's

Sistema web de pedidos para una sanguchería: catálogo de productos con personalización, pedidos con retiro en local o despacho a domicilio, pagos y gestión interna del local.

## Integrantes

| Integrante | Usuario de GitHub | App a cargo | Rama |
|---|---|---|---|
| Diego Quispe | `@Dfvg898` | `catalogo` | `feature/dquispe` |
| Leonel Humire | `@manzana728` | `pedidos` | `feature/lhumire` |
| Alonso Molina | `@vlonzz` | `usuarios` | `feature/amolina` |

## Gestores del sistema

Cada gestor es una app de Django a cargo de un integrante. Así cada uno trabaja en sus propios archivos y se reducen los conflictos al integrar.

| App | Modelos | Historias de usuario |
|---|---|---|
| `catalogo` | Categoria, Producto, OpcionPersonalizacion | HU-13, HU-14, HU-15, HU-16, HU-26, HU-29, HU-01, HU-02, HU-03, HU-04 |
| `pedidos` | Cliente, Pedido, DetallePedido, Pago | HU-09, HU-10, HU-23, HU-24, HU-25, HU-22, HU-30, HU-17, HU-18, HU-19 |
| `usuarios` | Usuario (con rol), Repartidor, BitacoraEvento | HU-05, HU-06, HU-07, HU-08, HU-11, HU-12, HU-27, HU-28, HU-20, HU-21 |

Dependencias entre apps: `pedidos` usa `Producto` (de `catalogo`) y `Repartidor` (de `usuarios`).

## Tecnologías

- Python 3 y Django
- SQLite (base de datos de desarrollo)
- Bootstrap 5 y Bootstrap Icons
- django-crispy-forms con crispy-bootstrap5
- Pillow (imágenes de productos)
- Pipenv (entorno virtual)

## Demostración de la integración

En una copia de revisión con Python 3.13, ejecuta estos comandos desde la raíz en PowerShell:

```powershell
python -m venv .venv
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Define SECRET_KEY en .env antes de continuar.
& ./.venv/Scripts/python.exe manage.py migrate
& ./.venv/Scripts/python.exe manage.py preparar_demo_integracion
& ./.venv/Scripts/python.exe manage.py test usuarios catalogo pedidos
& ./.venv/Scripts/python.exe manage.py runserver
```

El comando de demostración muestra las contraseñas generadas para las cuentas nuevas. Conserva las cuentas existentes al volver a ejecutarlo. Abre el catálogo en `http://127.0.0.1:8000/` como visitante y compra el producto de demostración. En otra sesión, entra como Cajero para ver el panel de pedidos recibidos y Gestión de entregas.

La integración registra avisos para efectivo al seleccionar el medio de pago, para transferencia al verificarla y para pedidos al entrar a Listo. Son avisos de prueba, sin conexión a WhatsApp. Para ver el texto usa `python manage.py simular_whatsapp ATOM-FOLIO confirmacion --registrar` con un folio de tu base.

## Instalación

Requisitos: Python 3, Git y Pipenv.

```bash
# 1. Clonar el repositorio
git clone https://github.com/<organizacion-o-usuario>/<repositorio>.git
cd <repositorio>

# 2. Instalar dependencias y activar el entorno
pipenv install -r requirements.txt
pipenv shell

# 3. Crear el archivo de variables de entorno
copy .env.example .env        # en Linux o Mac: cp .env.example .env
# Abre .env y escribe tu propia SECRET_KEY

# 4. Crear la base de datos
py manage.py migrate

# 5. Crear un superusuario para el panel de administración
py manage.py createsuperuser

# 6. Iniciar el servidor
py manage.py runserver
```
