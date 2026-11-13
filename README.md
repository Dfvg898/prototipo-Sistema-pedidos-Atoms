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
| `catalogo` | Categoria, Producto, OpcionPersonalizacion | HU-01 a HU-05 |
| `pedidos` | Cliente, Pedido, DetallePedido, Pago | HU-06 a HU-11 |
| `usuarios` | Usuario (con rol), Repartidor, BitacoraEvento | HU-12 a HU-15 |

Dependencias entre apps: `pedidos` usa `Producto` (de `catalogo`) y `Repartidor` (de `usuarios`).

## Tecnologías

- Python 3 y Django
- SQLite (base de datos de desarrollo)
- Bootstrap 5 y Bootstrap Icons
- django-crispy-forms con crispy-bootstrap5
- Pillow (imágenes de productos)
- Pipenv (entorno virtual)

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