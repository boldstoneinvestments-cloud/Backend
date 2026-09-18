import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import LeaseApplication, Order
from shop.models import ShopOrder


@csrf_exempt
def login_admin(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user = authenticate(username=data.get('username', ''), password=data.get('password', ''))
    if user is None or not user.is_staff:
        return JsonResponse({'error': 'Invalid admin credentials'}, status=401)
    login(request, user)
    return JsonResponse({'success': True, 'username': user.username})


@csrf_exempt
@login_required
def logout_admin(request):
    logout(request)
    return JsonResponse({'success': True})


@login_required
def admin_orders(request):
    shop_orders = ShopOrder.objects.select_related('product').order_by('-created_at')
    legacy_orders = Order.objects.order_by('-created_at')
    orders = [
        {
            'id': f'shop-{order.id}',
            'created_at': order.created_at.isoformat(),
            'name': order.name,
            'phone': order.phone,
            'email': order.email,
            'product': order.product_name,
            'quantity': order.quantity,
            'location': order.location,
            'notes': order.notes,
        }
        for order in shop_orders
    ] + [
        {
            'id': f'order-{order.id}',
            'created_at': order.created_at.isoformat(),
            'name': order.name,
            'phone': order.phone,
            'email': order.email,
            'product': order.product,
            'quantity': order.quantity,
            'location': order.location,
            'notes': order.notes,
        }
        for order in legacy_orders
    ]
    orders.sort(key=lambda order: order['created_at'], reverse=True)
    return JsonResponse({
        'orders': orders,
    })


@login_required
def admin_lease_applications(request):
    applications = LeaseApplication.objects.order_by('-created_at')
    return JsonResponse({
        'applications': [
            {
                'id': application.id,
                'created_at': application.created_at.isoformat(),
                'full_name': application.full_name,
                'email': application.email,
                'phone': application.phone,
                'country': application.country,
                'address': application.address,
                'plan': application.plan,
                'notes': application.notes,
                'status': application.status,
            }
            for application in applications
        ],
    })