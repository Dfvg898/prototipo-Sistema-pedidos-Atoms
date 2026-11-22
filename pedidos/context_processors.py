def carrito(request):
    """Deja el carrito (guardado en la sesión) disponible en todas las plantillas:
    panel lateral, contador del botón y total."""
    items = request.session.get('carrito', [])
    return {
        'items_carrito': items,
        'total_carrito': sum(item['subtotal'] for item in items),
        'cantidad_carrito': sum(item['cantidad'] for item in items),
    }
