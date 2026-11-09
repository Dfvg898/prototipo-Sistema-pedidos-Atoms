from django.shortcuts import render

# Create your views here.
def homeView(request):
    return render(request, "catalogo/lista.html")

def listaView(request):
    return render(request, "catalogo/lista.html")