from django.shortcuts import render, redirect, get_object_or_404
from .models import Categoria, Producto, OpcionPersonalizacion
from .forms import CategoriaForm, ProductoForm, OpcionPersonalizacionForm
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.db.models import Count
#restricciones de acceso
from django.views.decorators.http import require_POST
from usuarios.decorators import rol_requerido
from usuarios.models import Usuario

# Create your views here.
def homeView(request):
    # Traemos también las categorías y productos para que la página de inicio no se quede vacía
    categorias = Categoria.objects.all()
    productos = Producto.objects.filter(activo=True)
    
    context = {
        'categorias': categorias,
        'productos': productos,
    }
    return render(request, "catalogo/lista.html", context)

def listaView(request):
    # 1. Obtenemos todas las categorías para los botones del filtro
    categorias = Categoria.objects.all()
    
    # 2. Capturamos el parámetro 'categoria' de la URL (ej: ?categoria=1)
    categoria_id = request.GET.get('categoria')
    
    categoria_actual = None
    
    if categoria_id:
        # get_object_or_404 busca la categoría o da error 404 si no existe
        categoria_actual = get_object_or_404(Categoria, pk=categoria_id)
        # Filtramos los productos asociados a esa categoría
        productos = Producto.objects.filter(categoria=categoria_actual, activo=True)
    else:
        # Si no hay filtro, mostramos todos los productos
        productos = Producto.objects.filter(activo=True)
        
    context = {
        'categorias': categorias,
        'productos': productos,
        'categoria_actual': categoria_actual,
    }
    # Renderizamos tu plantilla principal del menú
    return render(request, "catalogo/lista.html", context)

#Vista categorias
@rol_requerido(Usuario.Rol.DUENO)
def categoriasListView(request):
    categorias = Categoria.objects.all()
    context = {
        'categorias': categorias,
    }
    return render(request, "catalogo/categoria_list.html", context)

@rol_requerido(Usuario.Rol.DUENO)
def categoriasCreateView(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría guardada correctamente.")
            return redirect("categorias")
        messages.error(request, "Revisa los campos marcados en rojo.")
    return render(request, "catalogo/categoria_form.html", {"form":form})

@rol_requerido(Usuario.Rol.DUENO)
def categoriasUpdateView(request, pk):
    # Buscamos la categoría existente o devolvemos un error 404 si no existe
    categoria = get_object_or_404(Categoria, pk=pk)
    
    # Pasamos instance=categoria para que el formulario se cargue con los datos actuales
    form = CategoriaForm(request.POST or None, instance=categoria)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Categoría actualizada correctamente.")
            return redirect("categorias") # Redirige al listado de categorías
        messages.error(request, "Revisa los campos marcados en rojo.")
            
    return render(request, "catalogo/categoria_form.html", {"form": form})

@rol_requerido(Usuario.Rol.DUENO)
def categoriasDeleteView(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == "POST":
        try:
            categoria.delete()
            messages.success(request, "Categoría eliminada correctamente.")
        except ProtectedError:
            messages.error(request, "No se puede eliminar la categoría porque tiene productos asociados.",)
        return redirect("categorias")
        
    return redirect("categorias")

############# Productos #############
@rol_requerido(Usuario.Rol.DUENO)
def productosListView(request):
    productos = Producto.objects.all()
    context = {
        'productos': productos,
    }
    return render(request, "catalogo/producto_list.html", context)

@rol_requerido(Usuario.Rol.DUENO)
def productosCreateView(request):
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Producto creado correctamente.")
            return redirect("productos")
        messages.error(request, "Revisa los campos marcados en rojo.")
    return render(request, "catalogo/producto_form.html", {"form": form})

@rol_requerido(Usuario.Rol.DUENO)
def productosUpdateView(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Producto actualizado correctamente.")
            return redirect("productos")
        messages.error(request, "Revisa los campos marcados en rojo.")
            
    return render(request, "catalogo/producto_form.html", {"form": form, "producto": producto})
def productosDeleteView(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        producto.activo = not producto.activo
        producto.save()
        
        return redirect("productos")
    return redirect("productos")

# opcion de personalizacion
@rol_requerido(Usuario.Rol.DUENO)
def opcionesPersonalizacionListView(request):
    opciones = OpcionPersonalizacion.objects.annotate(
        num_productos=Count("productos", distinct=True)
    )
    context = {
        'opciones': opciones,
    }
    return render(request, "catalogo/opcion_list.html", context)

@rol_requerido(Usuario.Rol.DUENO)
def opcionesPersonalizacionCreateView(request):
    form = OpcionPersonalizacionForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Opción de personalización creada correctamente.")
            return redirect("opciones_personalizacion")
        messages.error(request, "Revisa los campos marcados en rojo.")
    return render(request, "catalogo/opcion_form.html", {"form": form})

@rol_requerido(Usuario.Rol.DUENO)
def opcionesPersonalizacionUpdateView(request, pk):
    opcion = get_object_or_404(OpcionPersonalizacion, pk=pk)
    form = OpcionPersonalizacionForm(request.POST or None, instance=opcion)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Opción de personalización actualizada correctamente.")
            return redirect("opciones_personalizacion")
        messages.error(request, "Revisa los campos marcados en rojo.")
            
    return render(request, "catalogo/opcion_form.html", {"form": form, "opcion": opcion})

@rol_requerido(Usuario.Rol.DUENO)
def opcionesPersonalizacionDeleteView(request, pk):
    opcion = get_object_or_404(OpcionPersonalizacion, pk=pk)
    if request.method == "POST":
        opcion.delete()
        return redirect("opciones_personalizacion")
    return redirect("opciones_personalizacion")