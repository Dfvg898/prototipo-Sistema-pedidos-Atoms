from django.shortcuts import render, redirect, get_object_or_404
from .models import Categoria, Producto, OpcionPersonalizacion
from .forms import CategoriaForm, ProductoForm

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
        productos = Producto.objects.filter(categoria=categoria_actual)
    else:
        # Si no hay filtro, mostramos todos los productos
        productos = Producto.objects.all()
        
    context = {
        'categorias': categorias,
        'productos': productos,
        'categoria_actual': categoria_actual,
    }
    # Renderizamos tu plantilla principal del menú
    return render(request, "catalogo/lista.html", context)

#Vista categorias
def categoriasListView(request):
    categorias = Categoria.objects.all()
    context = {
        'categorias': categorias,
    }
    return render(request, "catalogo/categoria_list.html", context)

def categoriasCreateView(request):
    form = CategoriaForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("categorias")
    return render(request, "catalogo/categoria_form.html", {"form":form})

def categoriasUpdateView(request, pk):
    # Buscamos la categoría existente o devolvemos un error 404 si no existe
    categoria = get_object_or_404(Categoria, pk=pk)
    
    # Pasamos instance=categoria para que el formulario se cargue con los datos actuales
    form = CategoriaForm(request.POST or None, instance=categoria)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("categorias") # Redirige al listado de categorías
            
    return render(request, "catalogo/categoria_form.html", {"form": form})

def categoriasDeleteView(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == "POST":
        categoria.delete()
        return redirect("categorias")
        
    return redirect("categorias")

############# Productos #############
def productosListView(request):
    productos = Producto.objects.all()
    context = {
        'productos': productos,
    }
    return render(request, "catalogo/producto_list.html", context)

def productosCreateView(request):
    form = ProductoForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("productos")
    return render(request, "catalogo/producto_form.html", {"form": form})

def productosUpdateView(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    form = ProductoForm(request.POST or None, request.FILES or None, instance=producto)
    
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("productos")
            
    return render(request, "catalogo/producto_form.html", {"form": form, "producto": producto})
def productosDeleteView(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == "POST":
        producto.activo = not producto.activo
        producto.save()
        
        return redirect("productos")
    return redirect("productos")