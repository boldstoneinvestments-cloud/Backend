import json
from django.conf import settings
from django.core.mail import send_mail
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ContactMessage, Lease, LeaseApplication, Order

ESTATE = {
    'name': 'Kyenjojo Coffee Estate',
    'location': 'Kyenjojo District, Uganda',
    'altitude': '1,200 – 1,700m',
    'rainfall': '1,300 – 1,600mm',
    'soil': 'Volcanic Loam',
    'coordinates': {'lat': 0.6167, 'lng': 30.6167},
    'TOTAL_ACRES': 3000,
}


def body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def health(request):
    return JsonResponse({'status': 'ok'})


def estate(request):
    leases = list(Lease.objects.values('acres'))
    total_leased = sum(lease['acres'] for lease in leases)
    available = ESTATE['TOTAL_ACRES'] - total_leased
    return JsonResponse({**ESTATE, 'totalLeased': total_leased, 'available': available,
                         'pct': round(total_leased / ESTATE['TOTAL_ACRES'] * 100, 1),
                         'leaseCount': len(leases), 'leases': leases})


@csrf_exempt
def invest(request):
    data = body(request)
    acres = data.get('acres') if data else None
    if not isinstance(acres, (int, float)) or isinstance(acres, bool) or acres < 1:
        return JsonResponse({'error': 'Invalid acres value'}, status=400)
    total_leased = sum(lease.acres for lease in Lease.objects.all())
    available = ESTATE['TOTAL_ACRES'] - total_leased
    if acres > available:
        return JsonResponse({'error': f'Only {available} acres available'}, status=400)
    Lease.objects.create(acres=acres)
    return estate(request)


@csrf_exempt
def orders(request):
    data = body(request)
    required = ('name', 'phone', 'email', 'product', 'quantity', 'location')
    if not data or any(not data.get(field) for field in required):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    order = Order.objects.create(**{field: data[field] for field in required}, notes=data.get('notes', ''))
    return JsonResponse({'success': True, 'orderId': order.id}, status=201)


@csrf_exempt
def contact(request):
    data = body(request)
    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    message = ContactMessage.objects.create(name=data['name'], email=data['email'],
                                            subject=data.get('subject', ''), message=data['message'])
    if settings.EMAIL_TO:
        send_mail(message.subject or f'New Contact Message from {message.name}',
                  message.message, settings.DEFAULT_FROM_EMAIL, [settings.EMAIL_TO],
                  reply_to=[message.email])
    return JsonResponse({'success': True})


@csrf_exempt
def lease_applications(request):
    data = body(request)
    required = ('full_name', 'email', 'phone', 'country', 'plan')
    if not data or any(not data.get(field) for field in required):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    application = LeaseApplication.objects.create(
        full_name=data['full_name'], email=data['email'], phone=data['phone'],
        country=data['country'], address=data.get('address', ''), plan=data['plan'],
        notes=data.get('notes', ''),
    )
    return JsonResponse({'success': True, 'applicationId': application.id}, status=201)