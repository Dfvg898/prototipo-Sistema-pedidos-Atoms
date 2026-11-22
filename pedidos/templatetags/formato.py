from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """Muestra un número como precio chileno: 2800 -> $2.800"""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return valor
    return f"${numero:,}".replace(",", ".")
