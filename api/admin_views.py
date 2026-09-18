import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from .models import LeaseApplication, Order
from shop.models import ShopOrder

User = get_user_model()


def serialize_admin_user(user):
    return {
        'id': user.id,
        'name': user.get_full_name(),
        'username': user.username,
        'email': user.email,
        'is_active': user.is_active,
        'date_joined': user.date_joined.isoformat(),
    }


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


@csrf_exempt
@login_required
def admin_users(request):
    if request.method == 'GET':
        return JsonResponse({
            'users': [
                {
                    **serialize_admin_user(user),
                }
                for user in User.objects.filter(is_staff=True).order_by('username')
            ],
        })

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    name = str(data.get('name', '')).strip()
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))
    if not name or not username or not email or not password:
        return JsonResponse({'error': 'Name, username, email, and password are required'}, status=400)
    if len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': 'That username is already in use'}, status=409)
    if User.objects.filter(email=email).exists():
        return JsonResponse({'error': 'That email is already in use'}, status=409)

    name_parts = name.split(None, 1)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=name_parts[0],
        last_name=name_parts[1] if len(name_parts) > 1 else '',
        is_staff=True,
        is_active=True,
    )
    return JsonResponse({
        'success': True,
        'user': serialize_admin_user(user),
    }, status=201)


@csrf_exempt
@login_required
def admin_user_detail(request, user_id):
    if request.method != 'PUT':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user = User.objects.filter(id=user_id, is_staff=True).first()
    if user is None:
        return JsonResponse({'error': 'Admin user not found'}, status=404)

    name = str(data.get('name', '')).strip()
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', ''))
    if not name or not username or not email:
        return JsonResponse({'error': 'Name, username, and email are required'}, status=400)
    if password and len(password) < 8:
        return JsonResponse({'error': 'Password must be at least 8 characters'}, status=400)
    if User.objects.filter(username=username).exclude(id=user.id).exists():
        return JsonResponse({'error': 'That username is already in use'}, status=409)
    if User.objects.filter(email=email).exclude(id=user.id).exists():
        return JsonResponse({'error': 'That email is already in use'}, status=409)

    name_parts = name.split(None, 1)
    user.first_name = name_parts[0]
    user.last_name = name_parts[1] if len(name_parts) > 1 else ''
    user.username = username
    user.email = email
    if password:
        user.set_password(password)
    user.save()
    return JsonResponse({'success': True, 'user': serialize_admin_user(user)})


@login_required
def admin_orders(request):
    shop_orders = ShopOrder.objects.select_related('product').order_by('-created_at')
    legacy_orders = Order.objects.order_by('-created_at')
    orders = [
        {
            'id': f'shop-{order.id}',
            'invoice_number': order.invoice_number,
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
            'invoice_number': 'Legacy order',
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


@csrf_exempt
@login_required
def admin_delete_order(request, order_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        prefix, raw_id = order_id.split('-', 1)
        record_id = int(raw_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid order ID'}, status=400)

    if prefix == 'shop':
        deleted, _ = ShopOrder.objects.filter(id=record_id).delete()
    elif prefix == 'order':
        deleted, _ = Order.objects.filter(id=record_id).delete()
    else:
        return JsonResponse({'error': 'Invalid order ID'}, status=400)

    if not deleted:
        return JsonResponse({'error': 'Order not found'}, status=404)
    return JsonResponse({'success': True})


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


@csrf_exempt
@login_required
def admin_delete_lease_application(request, application_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    deleted, _ = LeaseApplication.objects.filter(id=application_id).delete()
    if not deleted:
        return JsonResponse({'error': 'Application not found'}, status=404)
    return JsonResponse({'success': True})