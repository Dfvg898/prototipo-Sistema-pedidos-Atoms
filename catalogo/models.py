from django.db import models

# Create your models here.
class Categoria(models.Model):
    """Agrupa los productos (Sandwiches, Completos, Bebidas, Promociones)."""
 
    nombre = models.CharField(max_length=60, unique=True)
    activa = models.BooleanField(default=True)

 
    def __str__(self):
        return self.nombre

class Producto(models.Model):
    """Item del catalogo. Si ya fue vendido no se borra: se desactiva."""
 
    nombre = models.CharField(max_length=100)
    descripcion = models.CharField(max_length=250)
    precio_base = models.PositiveIntegerField(help_text='Precio en pesos chilenos')
    imagen = models.ImageField(upload_to='productos/', blank=True)
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,  # no se borra una categoría que tiene productos
        related_name='productos',
    )
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False, help_text='Muestra la etiqueta "Más pedido"')
 
 
    def __str__(self):
        return self.nombre

class OpcionPersonalizacion(models.Model):
    """Ingrediente, salsa o extra que el cliente puede elegir en un producto."""
 
    INGREDIENTE = 'ingrediente'
    SALSA = 'salsa'
    EXTRA = 'extra'
    TIPOS = [
        (INGREDIENTE, 'Ingrediente'),
        (SALSA, 'Salsa'),
        (EXTRA, 'Extra'),
    ]
 
    nombre = models.CharField(max_length=60)
    tipo = models.CharField(max_length=15, choices=TIPOS)
    precio_extra = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    productos = models.ManyToManyField(
        Producto,
        related_name='opciones',
        blank=True,
        help_text='Productos en los que aparece esta opción',
    )
 
    def __str__(self):
        return f'{self.nombre} ({self.get_tipo_display()})'