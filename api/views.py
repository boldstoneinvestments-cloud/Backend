import json
import time
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.mail import send_mail
from django.http import JsonResponse, StreamingHttpResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from .models import ChatMessage, ContactMessage, CustomerProfile, Lease, LeaseApplication, Order
from email_service import send_lease_application_confirmation

ESTATE = {
    'name': 'Kyenjojo Coffee Estate',
    'location': 'Kyenjojo District, Uganda',
    'altitude': '1,200 – 1,700m',
    'rainfall': '1,300 – 1,600mm',
    'soil': 'Volcanic Loam',
    'coordinates': {'lat': 0.6167, 'lng': 30.6167},
    'TOTAL_ACRES': 3000,
}
User = get_user_model()


def customer_required(view):
    def wrapped(request, *args, **kwargs):
        if request.user.is_anonymous or request.user.is_staff:
            return JsonResponse({'error': 'Sign in required'}, status=401)
        return view(request, *args, **kwargs)
    return wrapped


def body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def health(request):
    return JsonResponse({'status': 'ok'})


def account_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def serialize_account(user):
    profile, _ = CustomerProfile.objects.get_or_create(user=user)
    return {'id': str(profile.public_id), 'name': user.get_full_name(), 'email': user.email}


def account_signup(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = body(request) or {}
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    if not name or not email or len(password) < 8:
        return JsonResponse({'error': 'Name, email, and a password of at least 8 characters are required'}, status=400)
    if User.objects.filter(email__iexact=email).exists():
        return JsonResponse({'error': 'An account with that email already exists'}, status=409)
    first_name, _, last_name = name.partition(' ')
    user = User.objects.create_user(username=email, email=email, password=password, first_name=first_name, last_name=last_name)
    CustomerProfile.objects.create(user=user)
    ChatMessage.objects.filter(user__isnull=True, email__iexact=email).update(user=user)
    login(request, user)
    return JsonResponse({'user': serialize_account(user)}, status=201)


def account_login(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = body(request) or {}
    email = str(data.get('email', '')).strip().lower()
    user = User.objects.filter(email__iexact=email, is_staff=False, is_active=True).first()
    user = authenticate(username=user.username, password=data.get('password', '')) if user else None
    if user is None:
        return JsonResponse({'error': 'Invalid email or password'}, status=401)
    login(request, user)
    return JsonResponse({'user': serialize_account(user)})


@customer_required
def account_me(request):
    return JsonResponse({'user': serialize_account(request.user)})


@customer_required
def account_logout(request):
    logout(request)
    return JsonResponse({'success': True})


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


def chat(request):
    if request.user.is_anonymous or request.user.is_staff:
        return JsonResponse({'error': 'Sign in required'}, status=401)
    data = body(request)
    if request.method == 'GET':
        return JsonResponse({
            'messages': [
                {
                    'id': message.id,
                    'message': message.message,
                    'is_admin': message.is_admin,
                    'created_at': message.created_at.isoformat(),
                }
                for message in ChatMessage.objects.filter(user=request.user).order_by('created_at')
            ],
        })

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    if not data or not data.get('message'):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    msg = ChatMessage.objects.create(user=request.user, name=request.user.get_full_name(), email=request.user.email, message=data['message'], is_admin=False)
    from email_service import send_chat_notification
    send_chat_notification(msg)
    return JsonResponse({'success': True, 'message': {
        'id': msg.id, 'message': msg.message, 'is_admin': False,
        'created_at': msg.created_at.isoformat(),
    }})


@customer_required
def chat_stream(request):
    try:
        last_id = int(request.GET.get('last_id', 0))
    except (TypeError, ValueError):
        last_id = 0

    def events():
        deadline = time.monotonic() + 25
        while time.monotonic() < deadline:
            messages = ChatMessage.objects.filter(user=request.user, id__gt=last_id).order_by('id')
            if messages.exists():
                for message in messages:
                    yield f"data: {json.dumps({'id': message.id, 'message': message.message, 'is_admin': message.is_admin, 'created_at': message.created_at.isoformat()})}\n\n"
                return
            yield ': keep-alive\n\n'
            time.sleep(2)

    response = StreamingHttpResponse(events(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


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
    send_lease_application_confirmation(application)
    return JsonResponse({'success': True, 'applicationId': application.id}, status=201)