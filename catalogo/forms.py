from django import forms
from .models import Categoria, Producto, OpcionPersonalizacion

class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = '__all__'

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'

class OpcionPersonalizacionForm(forms.ModelForm):
    class Meta:
        model = OpcionPersonalizacion
        fields = '__all__'
