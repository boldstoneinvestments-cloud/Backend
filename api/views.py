import json
import os
import time
import secrets
import threading
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.mail import send_mail
from django.http import FileResponse, JsonResponse, StreamingHttpResponse
from django.middleware.csrf import get_token
from django.core import signing
from django.db import connection
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
MAX_CHAT_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_CHAT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.txt', '.csv'}
CUSTOMER_TOKEN_MAX_AGE = 60 * 60 * 24 * 365 * 10


def chat_attachment_url(message):
    return f'/api/chat/attachments/{message.id}' if message.attachment else ''


def chat_message_payload(message):
    return {
        'id': message.id,
        'message': message.message,
        'is_admin': message.is_admin,
        'is_ai': message.is_ai,
        'admin_name': message.admin_name,
        'admin_avatar': message.admin_avatar,
        'attachment_url': chat_attachment_url(message),
        'attachment_name': message.attachment.name.rsplit('/', 1)[-1] if message.attachment else '',
        'created_at': message.created_at.isoformat(),
    }


def chat_history_for(user):
    return [
        {'role': 'model' if item.is_admin or item.is_ai else 'user', 'text': item.message}
        for item in list(ChatMessage.objects.filter(user=user).order_by('-created_at')[:12])[::-1]
    ]


def process_chat_ai_followup(user_id, message_id):
    user = User.objects.filter(id=user_id, is_active=True, is_staff=False).first()
    message = ChatMessage.objects.filter(id=message_id, user_id=user_id).first()
    if user is None or message is None or ChatMessage.objects.filter(user=user, is_admin=True).exists():
        return

    try:
        from .gemini import generate_supported_reply
        ai_text = generate_supported_reply(chat_history_for(user))
    except Exception:
        ai_text = None
    if ChatMessage.objects.filter(user=user, is_admin=True).exists():
        return

    if ai_text:
        ChatMessage.objects.create(user=user, name='Boldstone AI', email=user.email, message=ai_text, is_ai=True)
        return

    handoff_text = 'I could not confidently solve that question, so a support ticket has been registered. Customer care will review it and contact you. Please do not share passwords, payment details, or other private information here.'
    ChatMessage.objects.create(user=user, name='Boldstone AI', email=user.email, message=handoff_text, is_ai=True)
    if not ChatMessage.objects.filter(user=user, is_admin=True).exists():
        from email_service import send_chat_notification
        threading.Thread(target=send_chat_notification, args=(message,), kwargs={'ticket': True}, daemon=True).start()


def customer_token(user):
    return signing.dumps({'user_id': user.id}, salt='customer-auth')


def token_user(request):
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer '):
        return None
    try:
        payload = signing.loads(header[7:], salt='customer-auth', max_age=CUSTOMER_TOKEN_MAX_AGE)
        return User.objects.filter(id=payload.get('user_id'), is_active=True, is_staff=False).first()
    except (signing.BadSignature, TypeError, ValueError):
        return None


def customer_required(view):
    def wrapped(request, *args, **kwargs):
        user = token_user(request)
        if user is None and not request.user.is_anonymous and not request.user.is_staff:
            user = request.user
        if user is None:
            return JsonResponse({'error': 'Sign in required'}, status=401)
        request.api_user = user
        return view(request, *args, **kwargs)
    return wrapped


def body(request):
    try:
        return json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return None


def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'database_unavailable'}, status=503)
    return JsonResponse({'status': 'ok'})


def account_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def google_start(request):
    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '').strip()
    if not client_id or not redirect_uri:
        return JsonResponse({'error': 'Google sign-in is not configured'}, status=503)
    state = signing.dumps({'nonce': secrets.token_urlsafe(32)}, salt='google-oauth-state')
    query = urlencode({
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
    })
    from django.shortcuts import redirect
    return redirect(f'https://accounts.google.com/o/oauth2/v2/auth?{query}')


def google_callback(request):
    from django.shortcuts import redirect
    frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173').strip().rstrip('/')
    if request.GET.get('error'):
        return redirect(f'{frontend_url}/account/sign-in?error=google_cancelled')
    try:
        signing.loads(request.GET.get('state', ''), salt='google-oauth-state', max_age=600)
    except signing.BadSignature:
        return JsonResponse({'error': 'Invalid Google OAuth state'}, status=400)

    client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '').strip()
    try:
        token_request = Request('https://oauth2.googleapis.com/token', data=urlencode({
            'code': request.GET.get('code', ''), 'client_id': client_id,
            'client_secret': client_secret, 'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }).encode(), headers={'Content-Type': 'application/x-www-form-urlencoded'})
        with urlopen(token_request, timeout=8) as response:
            token_data = json.loads(response.read())
        access_token = token_data.get('access_token')
        if not access_token:
            raise ValueError('Google did not return an access token')
        profile_request = Request('https://openidconnect.googleapis.com/v1/userinfo', headers={
            'Authorization': f'Bearer {access_token}'
        })
        with urlopen(profile_request, timeout=8) as response:
            profile = json.loads(response.read())
        email = str(profile.get('email', '')).strip().lower()
        if not email or not profile.get('email_verified'):
            raise ValueError('Google email is not verified')
    except Exception:
        return redirect(f'{frontend_url}/account/sign-in?error=google_failed')

    user = User.objects.filter(email__iexact=email, is_staff=False).first()
    if user is None:
        user = User.objects.create_user(username=email, email=email, first_name=profile.get('given_name', ''), last_name=profile.get('family_name', ''))
    CustomerProfile.objects.get_or_create(user=user)
    ChatMessage.objects.filter(user__isnull=True, email__iexact=email).update(user=user)
    login(request, user)
    return redirect(f'{frontend_url}/#google_token={customer_token(user)}')


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
    return JsonResponse({'user': serialize_account(user), 'token': customer_token(user)}, status=201)


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
    return JsonResponse({'user': serialize_account(user), 'token': customer_token(user)})


def account_me(request):
    user = token_user(request)
    if user is None and not request.user.is_anonymous and not request.user.is_staff:
        user = request.user
    if user is None:
        return JsonResponse({'authenticated': False})
    return JsonResponse({'authenticated': True, 'user': serialize_account(user)})


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
    user = token_user(request)
    if user is None and not request.user.is_anonymous and not request.user.is_staff:
        user = request.user
    if user is None:
        return JsonResponse({'error': 'Sign in required'}, status=401)
    if request.method == 'GET':
        return JsonResponse({
            'messages': [
                chat_message_payload(message)
                for message in ChatMessage.objects.filter(user=user).order_by('created_at')
            ],
        })

    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = body(request) if request.content_type == 'application/json' else None
    message_text = str((data or {}).get('message', '') if data is not None else request.POST.get('message', '')).strip()
    uploads = request.FILES.getlist('attachment')
    if not message_text and not uploads:
        return JsonResponse({'error': 'Message or attachment is required'}, status=400)
    for upload in uploads:
        from pathlib import Path
        if upload.size > MAX_CHAT_FILE_SIZE or Path(upload.name).suffix.lower() not in ALLOWED_CHAT_EXTENSIONS:
            return JsonResponse({'error': 'Files must be images, documents, or text files smaller than 5 MB'}, status=400)
    messages = [ChatMessage.objects.create(user=user, name=user.get_full_name(), email=user.email, message=message_text if index == 0 else '', is_admin=False, attachment=upload) for index, upload in enumerate(uploads or [None])]
    msg = messages[0]
    response = {'success': True, 'message': chat_message_payload(msg), 'messages': [chat_message_payload(item) for item in messages]}

    admin_has_replied = ChatMessage.objects.filter(user=user, is_admin=True).exists()
    ai_message = None
    if not admin_has_replied:
        from .gemini import quick_response
        local_reply = quick_response(chat_history_for(user))
        if local_reply:
            ai_message = ChatMessage.objects.create(user=user, name='Boldstone AI', email=user.email, message=local_reply, is_ai=True)
        else:
            threading.Thread(target=process_chat_ai_followup, args=(user.id, msg.id), daemon=True).start()
    if ai_message:
        response['ai_message'] = chat_message_payload(ai_message)
    return JsonResponse(response)


def chat_attachment(request, message_id):
    user = token_user(request)
    if user is None and not request.user.is_anonymous:
        user = request.user
    if user is None:
        return JsonResponse({'error': 'Sign in required'}, status=401)
    queryset = ChatMessage.objects.filter(id=message_id)
    if not user.is_staff:
        queryset = queryset.filter(user=user)
    message = queryset.first()
    if message is None or not message.attachment:
        return JsonResponse({'error': 'Attachment not found'}, status=404)
    return FileResponse(message.attachment.open('rb'), as_attachment=False, filename=message.attachment.name.rsplit('/', 1)[-1])


@csrf_exempt
@customer_required
def chat_message_actions(request, message_id):
    message = ChatMessage.objects.filter(id=message_id, user=request.api_user, is_admin=False, is_ai=False).first()
    if message is None:
        return JsonResponse({'error': 'Message not found'}, status=404)
    if request.method == 'DELETE':
        message.delete()
        return JsonResponse({'success': True, 'id': message_id})
    if request.method not in ('PATCH', 'PUT'):
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    data = body(request)
    text = str((data or {}).get('message', '')).strip()
    if not text:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    message.message = text
    message.save(update_fields=['message'])
    return JsonResponse({'success': True, 'message': chat_message_payload(message)})


@customer_required
def chat_stream(request):
    request.api_user = token_user(request)
    if request.api_user is None and not request.user.is_anonymous and not request.user.is_staff:
        request.api_user = request.user
    try:
        last_id = int(request.GET.get('last_id', 0))
    except (TypeError, ValueError):
        last_id = 0

    def events():
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            messages = ChatMessage.objects.filter(user=request.api_user, id__gt=last_id).order_by('id')
            if messages.exists():
                for message in messages:
                    yield f"data: {json.dumps(chat_message_payload(message))}\n\n"
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