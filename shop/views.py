import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, ShopOrder


def products(request):
    catalog = {}
    for product in Product.objects.filter(active=True):
        catalog.setdefault(product.category, []).append({
            'id': product.id,
            'name': product.name,
            'variety': '',
            'price': product.price,
            'unit': product.unit,
            'image': product.image,
            'desc': product.description,
            'badge': product.badge,
            'varieties': product.varieties,
        })
    return JsonResponse(catalog)


@csrf_exempt
def orders(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        data = None

    required = ('name', 'phone', 'email', 'product', 'quantity', 'location')
    if not data or any(not data.get(field) for field in required):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    try:
        quantity = int(data['quantity'])
    except (TypeError, ValueError):
        quantity = 0
    if quantity < 1:
        return JsonResponse({'error': 'Quantity must be at least 1'}, status=400)

    product_name = data['product']
    product_id = data.get('productId')
    product = Product.objects.filter(id=product_id, active=True).first()
    if product is None:
        product = Product.objects.filter(name=product_name, active=True).first()
    if product is None:
        return JsonResponse({'error': 'Product not found'}, status=404)

    order = ShopOrder.objects.create(
        name=data['name'], phone=data['phone'], email=data['email'], product=product,
        product_name=product_name, quantity=quantity, location=data['location'],
        notes=data.get('notes', ''),
    )
    return JsonResponse({'success': True, 'orderId': order.id}, status=201)