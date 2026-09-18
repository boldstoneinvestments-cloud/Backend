import json
from django.db import transaction
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

    required = ('name', 'phone', 'email', 'location')
    if not data or any(not data.get(field) for field in required):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    items = data.get('items')
    if not isinstance(items, list) or not items:
        items = [{
            'id': data.get('productId'),
            'productName': data.get('product'),
            'qty': data.get('quantity'),
        }]

    order_ids = []
    with transaction.atomic():
        for item in items:
            product_id = item.get('id')
            product_name = item.get('productName', '')
            product = Product.objects.filter(id=product_id, active=True).first()
            if product is None:
                product = Product.objects.filter(name=product_name, active=True).first()
            if product is None:
                return JsonResponse({'error': f'Product not found: {product_name}'}, status=404)

            selections = item.get('selections')
            lines = selections if isinstance(selections, list) and selections else [item]
            for line in lines:
                try:
                    quantity = int(line.get('qty', 0))
                except (TypeError, ValueError):
                    quantity = 0
                if quantity < 1:
                    continue
                variety = line.get('variety')
                line_name = f'{product.name} — {variety}' if variety else product.name
                order = ShopOrder.objects.create(
                    name=data['name'], phone=data['phone'], email=data['email'], product=product,
                    product_name=line_name, quantity=quantity, location=data['location'],
                    notes=data.get('notes', ''),
                )
                order_ids.append(order.id)

    if not order_ids:
        return JsonResponse({'error': 'Cart quantity must be at least 1'}, status=400)
    return JsonResponse({'success': True, 'orderIds': order_ids}, status=201)