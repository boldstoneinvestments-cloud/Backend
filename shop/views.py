import json
from datetime import datetime
from uuid import uuid4
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Product, ShopOrder
from email_service import send_shop_order_confirmation


CATEGORY_ORDER = ['seedlings', 'roasted', 'trees']

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
    ordered = {k: catalog[k] for k in CATEGORY_ORDER if k in catalog}
    ordered.update({k: v for k, v in catalog.items() if k not in ordered})
    return JsonResponse(ordered)


@csrf_exempt
def orders(request):
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        data = None

    required = ('name', 'phone', 'email', 'country', 'province', 'district')
    if not data or any(not data.get(field) for field in required):
        return JsonResponse({'error': 'Missing required fields'}, status=400)

    items = data.get('items')
    if not isinstance(items, list) or not items:
        items = [{
            'id': data.get('productId'),
            'productName': data.get('product'),
            'qty': data.get('quantity'),
        }]

    invoice_number = f'BS-{datetime.now().strftime("%Y%m%d")}-{uuid4().hex[:6].upper()}'
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
                    invoice_number=invoice_number, name=data['name'], phone=data['phone'], email=data['email'], product=product,
                    product_name=line_name, quantity=quantity, location=data['location'],
                    country=data['country'], province=data['province'], district=data['district'],
                    street=data.get('street', ''), village=data.get('village', ''),
                    notes=data.get('notes', ''),
                )
                order_ids.append(order.id)

    if not order_ids:
        return JsonResponse({'error': 'Cart quantity must be at least 1'}, status=400)
    created_orders = list(ShopOrder.objects.filter(id__in=order_ids).select_related('product'))
    send_shop_order_confirmation(created_orders, invoice_number)
    return JsonResponse({'success': True, 'orderIds': order_ids, 'invoiceNumber': invoice_number}, status=201)