import json
from functools import wraps
from pathlib import Path
from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import AdminActivity, AdminPresence, ChatMessage, LeaseApplication, Order
from shop.models import ShopOrder

MAX_CHAT_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_CHAT_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.pdf', '.doc', '.docx', '.txt', '.csv'}

User = get_user_model()

ADMIN_IDENTITIES = {
    'SSEMATA SABIRA': 'https://address-restaurant2.odoo.com/web/image/1888-df4ef49b/Sabira.webp',
    'MOSES ALICWAMU': 'https://address-restaurant2.odoo.com/web/image/1571-51dfbae5/Moses%20Photo%20-%20up%20to%20date.webp',
    'HABIB TUMWESIGE': 'https://address-restaurant2.odoo.com/web/image/1982-2595a3af/Habib%20Salah.webp',
}


def staff_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Admin sign in required'}, status=401)
        if not request.user.is_active or not request.user.is_staff:
            return JsonResponse({'error': 'Admin access required'}, status=403)
        return view(request, *args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Admin sign in required'}, status=401)
        if not request.user.is_active or not request.user.is_staff:
            return JsonResponse({'error': 'Admin access required'}, status=403)
        if request.session.get('admin_identity_name') not in ADMIN_IDENTITIES:
            return JsonResponse({'error': 'Choose your admin identity first'}, status=409)
        return view(request, *args, **kwargs)
    return wrapped


def identity_payload(identity_name):
    if identity_name not in ADMIN_IDENTITIES:
        return None
    return {'name': identity_name, 'avatar': ADMIN_IDENTITIES[identity_name]}


def log_admin_activity(request, action, target_type='', target_id='', details=None, identity_name=None, page=None):
    AdminActivity.objects.create(
        actor=request.user,
        actor_username=request.user.username,
        identity_name=identity_name or request.session.get('admin_identity_name', ''),
        action=action,
        page=page or request.session.get('admin_current_page', ''),
        target_type=target_type,
        target_id=str(target_id)[:255],
        details=details or {},
    )


def serialize_activity(activity):
    return {
        'id': activity.id,
        'actor_username': activity.actor_username,
        'identity_name': activity.identity_name,
        'action': activity.action,
        'page': activity.page,
        'target_type': activity.target_type,
        'target_id': activity.target_id,
        'details': activity.details,
        'created_at': activity.created_at.isoformat(),
    }


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


@staff_required
def admin_session(request):
    identity_name = request.session.get('admin_identity_name', '')
    return JsonResponse({
        'authenticated': True,
        'username': request.user.username,
        'identity': identity_payload(identity_name),
        'identities': [{'name': name, 'avatar': avatar} for name, avatar in ADMIN_IDENTITIES.items()],
    })


@csrf_exempt
@staff_required
def admin_identity(request):
    if request.method == 'GET':
        return JsonResponse({
            'identity': identity_payload(request.session.get('admin_identity_name', '')),
            'identities': [{'name': name, 'avatar': avatar} for name, avatar in ADMIN_IDENTITIES.items()],
        })
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    identity_name = str(data.get('identity_name', '')).strip().upper()
    previous_identity = request.session.get('admin_identity_name', '')
    if identity_name and identity_name not in ADMIN_IDENTITIES:
        return JsonResponse({'error': 'Choose a valid admin identity'}, status=400)
    if identity_name:
        request.session['admin_identity_name'] = identity_name
        AdminPresence.objects.update_or_create(
            user=request.user,
            defaults={'identity_name': identity_name, 'identity_avatar': ADMIN_IDENTITIES[identity_name]},
        )
        log_admin_activity(
            request,
            'Selected admin identity' if not previous_identity else 'Changed admin identity',
            target_type='identity',
            target_id=identity_name,
            details={'previous_identity': previous_identity},
            identity_name=identity_name,
        )
        return JsonResponse({'identity': identity_payload(identity_name)})

    if previous_identity:
        log_admin_activity(request, 'Cleared admin identity', target_type='identity', target_id=previous_identity)
    request.session.pop('admin_identity_name', None)
    AdminPresence.objects.filter(user=request.user).update(identity_name='', identity_avatar='')
    return JsonResponse({'identity': None})


@csrf_exempt
@staff_required
def logout_admin(request):
    if request.session.get('admin_identity_name'):
        log_admin_activity(request, 'Signed out', 'admin session', request.user.username)
    AdminPresence.objects.filter(user=request.user).update(last_seen=timezone.now() - timedelta(seconds=61))
    logout(request)
    return JsonResponse({'success': True})


@csrf_exempt
@admin_required
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
    log_admin_activity(request, 'Created admin account', 'admin account', user.username, {'user_id': user.id})
    return JsonResponse({
        'success': True,
        'user': serialize_admin_user(user),
    }, status=201)


@csrf_exempt
@admin_required
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

    changed_fields = []
    if user.get_full_name() != name:
        changed_fields.append('name')
    if user.username != username:
        changed_fields.append('username')
    if user.email != email:
        changed_fields.append('email')
    if password:
        changed_fields.append('password')
    name_parts = name.split(None, 1)
    user.first_name = name_parts[0]
    user.last_name = name_parts[1] if len(name_parts) > 1 else ''
    user.username = username
    user.email = email
    if password:
        user.set_password(password)
    user.save()
    log_admin_activity(request, 'Updated admin account', 'admin account', user.username, {'user_id': user.id, 'changed_fields': changed_fields})
    return JsonResponse({'success': True, 'user': serialize_admin_user(user)})


@csrf_exempt
@admin_required
def admin_customers(request):
    if request.method == 'GET':
        contacts = {}

        def add_contact(email, name='', phone='', source='', reason='', created_at=None, account=None, details=None):
            key = email.lower()
            contact = contacts.setdefault(key, {
                'id': account.id if account else f'contact-{len(contacts) + 1}',
                'account_id': account.id if account else None,
                'name': name,
                'username': account.username if account else '',
                'email': email,
                'phone': phone,
                'sources': [],
                'date_joined': created_at.isoformat() if created_at else '',
                'is_active': account.is_active if account else None,
                'records': [],
            })
            if account:
                contact.update({
                    'id': account.id,
                    'account_id': account.id,
                    'name': account.get_full_name() or contact['name'],
                    'username': account.username,
                    'email': account.email,
                    'is_active': account.is_active,
                    'date_joined': account.date_joined.isoformat(),
                })
            elif not contact['name']:
                contact['name'] = name
            if phone and not contact['phone']:
                contact['phone'] = phone
            if source and source not in contact['sources']:
                contact['sources'].append(source)
            if source and not any(record['source'] == source and record['date'] == created_at.isoformat() for record in contact['records']):
                contact['records'].append({
                    'source': source,
                    'reason': reason,
                    'date': created_at.isoformat() if created_at else '',
                    'details': details or {},
                })
            if created_at and (not contact['date_joined'] or created_at.isoformat() > contact['date_joined']):
                contact['date_joined'] = created_at.isoformat()

        for user in User.objects.filter(is_staff=False).order_by('first_name', 'last_name', 'email'):
            add_contact(user.email, user.get_full_name(), source='Chat account', reason='Signed up to use customer chat', created_at=user.date_joined, account=user, details={'username': user.username})
        for order in ShopOrder.objects.order_by('created_at'):
            add_contact(order.email, order.name, order.phone, 'Order page', 'Placed an order', order.created_at, details={'product': order.product_name, 'quantity': order.quantity, 'location': order.location, 'country': order.country, 'province': order.province, 'district': order.district, 'street': order.street, 'village': order.village, 'notes': order.notes, 'invoice_number': order.invoice_number})
        for order in Order.objects.order_by('created_at'):
            add_contact(order.email, order.name, order.phone, 'Order page', 'Placed an order', order.created_at, details={'product': order.product, 'quantity': order.quantity, 'location': order.location, 'notes': order.notes})
        for application in LeaseApplication.objects.order_by('created_at'):
            add_contact(application.email, application.full_name, application.phone, 'Lease page', 'Applied to lease a coffee farm', application.created_at, details={'plan': application.plan, 'country': application.country, 'address': application.address, 'status': application.status, 'notes': application.notes})

        return JsonResponse({
            'customers': sorted(contacts.values(), key=lambda contact: (contact['name'] or contact['email']).lower()),
        })

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
@admin_required
def admin_customer_delete(request, email):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    with transaction.atomic():
        user_deleted, _ = User.objects.filter(email__iexact=email, is_staff=False).delete()
        orders_deleted, _ = ShopOrder.objects.filter(email__iexact=email).delete()
        legacy_orders_deleted, _ = Order.objects.filter(email__iexact=email).delete()
        applications_deleted, _ = LeaseApplication.objects.filter(email__iexact=email).delete()
        messages_deleted, _ = ChatMessage.objects.filter(email__iexact=email).delete()

    if not any((user_deleted, orders_deleted, legacy_orders_deleted, applications_deleted, messages_deleted)):
        return JsonResponse({'error': 'Customer not found'}, status=404)
    log_admin_activity(request, 'Deleted customer records', 'customer', email, {
        'accounts': user_deleted,
        'shop_orders': orders_deleted,
        'legacy_orders': legacy_orders_deleted,
        'applications': applications_deleted,
        'chat_messages': messages_deleted,
    })
    return JsonResponse({'success': True})


@admin_required
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
@admin_required
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
    log_admin_activity(request, 'Deleted order', f'{prefix} order', record_id)
    return JsonResponse({'success': True})


@admin_required
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


@admin_required
def admin_chat_messages(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    messages = ChatMessage.objects.order_by('-created_at')
    return JsonResponse({
        'messages': [
            {
                'id': message.id,
                'name': message.name,
                'email': message.email,
                'message': message.message,
                'is_admin': message.is_admin,
                'is_ai': message.is_ai,
                'admin_name': message.admin_name,
                'admin_avatar': message.admin_avatar,
                'attachment_url': f'/api/chat/attachments/{message.id}' if message.attachment else '',
                'attachment_name': message.attachment.name.rsplit('/', 1)[-1] if message.attachment else '',
                'created_at': message.created_at.isoformat(),
            }
            for message in messages
        ],
    })


@csrf_exempt
@admin_required
def admin_presence(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    page = str(data.get('page', '/admin')).split('?', 1)[0].strip()[:255]
    if page != '/admin' and not page.startswith('/admin/'):
        page = '/admin'
    identity_name = request.session['admin_identity_name']
    presence, created = AdminPresence.objects.get_or_create(
        user=request.user,
        defaults={
            'identity_name': identity_name,
            'identity_avatar': ADMIN_IDENTITIES[identity_name],
            'current_page': page,
        },
    )
    previous_page = presence.current_page
    page_changed = created or previous_page != page
    if page_changed and not created:
        presence.last_page = previous_page
    presence.identity_name = identity_name
    presence.identity_avatar = ADMIN_IDENTITIES[identity_name]
    presence.current_page = page
    presence.last_seen = timezone.now()
    presence.save(update_fields=['identity_name', 'identity_avatar', 'current_page', 'last_page', 'last_seen'])
    request.session['admin_current_page'] = page
    if page_changed:
        log_admin_activity(
            request,
            'Viewed admin page',
            target_type='page',
            target_id=page,
            details={'previous_page': previous_page},
            page=page,
        )
    return JsonResponse({'success': True, 'current_page': page, 'last_page': presence.last_page})


@csrf_exempt
@admin_required
def admin_chat_reply(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip()
    message = str(data.get('message', '')).strip()
    admin_name = request.session['admin_identity_name']
    uploads = request.FILES.getlist('attachment')
    admin_avatar = ADMIN_IDENTITIES.get(admin_name)
    if any(upload.size > MAX_CHAT_FILE_SIZE or Path(upload.name).suffix.lower() not in ALLOWED_CHAT_EXTENSIONS for upload in uploads):
        return JsonResponse({'error': 'Files must be images, documents, or text files smaller than 5 MB'}, status=400)
    if not name or not email or (not message and not uploads) or not admin_name:
        return JsonResponse({'error': 'Admin identity and message or attachment are required'}, status=400)
    if not admin_avatar:
        return JsonResponse({'error': 'Select a valid admin identity'}, status=400)

    customer = User.objects.filter(email__iexact=email, is_staff=False).first()
    if customer is None:
        return JsonResponse({'error': 'Customer account not found'}, status=404)
    replies = [ChatMessage.objects.create(user=customer, name=customer.get_full_name(), email=customer.email, message=message if index == 0 else '', is_admin=True, admin_name=admin_name, admin_avatar=admin_avatar, attachment=upload) for index, upload in enumerate(uploads or [None])]
    reply = replies[0]
    log_admin_activity(request, 'Replied to chat', 'chat', customer.email, {
        'message_id': reply.id,
        'attachment_count': len(uploads),
    })
    serialized = [{
        'id': item.id,
        'name': item.name,
        'email': item.email,
        'message': item.message,
        'is_admin': item.is_admin,
        'is_ai': item.is_ai,
        'admin_name': item.admin_name,
        'admin_avatar': item.admin_avatar,
        'attachment_url': f'/api/chat/attachments/{item.id}' if item.attachment else '',
        'attachment_name': item.attachment.name.rsplit('/', 1)[-1] if item.attachment else '',
        'created_at': item.created_at.isoformat(),
    } for item in replies]
    return JsonResponse({
        'success': True,
        'message': {
            'id': reply.id,
            'name': reply.name,
            'email': reply.email,
            'message': reply.message,
            'is_admin': reply.is_admin,
            'is_ai': reply.is_ai,
            'admin_name': reply.admin_name,
            'admin_avatar': reply.admin_avatar,
            'attachment_url': serialized[0]['attachment_url'],
            'attachment_name': serialized[0]['attachment_name'],
            'created_at': reply.created_at.isoformat(),
        },
        'messages': serialized,
    }, status=201)


@csrf_exempt
@admin_required
def admin_chat_message_actions(request, message_id):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    message = ChatMessage.objects.filter(id=message_id).first()
    if message is None:
        return JsonResponse({'error': 'Message not found'}, status=404)
    if request.method == 'DELETE':
        message_email = message.email
        message.delete()
        log_admin_activity(request, 'Deleted chat message', 'chat message', message_id, {'email': message_email})
        return JsonResponse({'success': True, 'id': message_id})
    if request.method != 'PATCH' or not message.is_admin:
        return JsonResponse({'error': 'Only admin messages can be edited'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    text = str(data.get('message', '')).strip()
    if not text:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)
    message.message = text
    message.save(update_fields=['message'])
    log_admin_activity(request, 'Edited chat message', 'chat message', message_id, {'email': message.email, 'message_length': len(text)})
    return JsonResponse({'success': True, 'message': {'id': message.id, 'message': message.message}})


@csrf_exempt
@admin_required
def admin_delete_chat(request, email):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    deleted, _ = ChatMessage.objects.filter(email__iexact=email).delete()
    if deleted:
        log_admin_activity(request, 'Deleted customer chat', 'chat', email, {'deleted_messages': deleted})
    return JsonResponse({'success': True, 'deleted': deleted})


@csrf_exempt
@admin_required
def admin_delete_all_chats(request):
    if not request.user.is_staff:
        return JsonResponse({'error': 'Admin access required'}, status=403)
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    deleted, _ = ChatMessage.objects.all().delete()
    if deleted:
        log_admin_activity(request, 'Deleted all chats', 'chat inbox', 'all', {'deleted_messages': deleted})
    return JsonResponse({'success': True, 'deleted': deleted})


@csrf_exempt
@admin_required
def admin_delete_lease_application(request, application_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    deleted, _ = LeaseApplication.objects.filter(id=application_id).delete()
    if not deleted:
        return JsonResponse({'error': 'Application not found'}, status=404)
    log_admin_activity(request, 'Deleted lease application', 'lease application', application_id)
    return JsonResponse({'success': True})


@csrf_exempt
@admin_required
def admin_activity(request):
    if request.method == 'GET':
        now = timezone.now()
        presences = AdminPresence.objects.filter(user__is_staff=True, user__is_active=True).select_related('user').order_by('-last_seen')
        return JsonResponse({
            'admins': [{
                'username': presence.user.username,
                'name': presence.identity_name or presence.user.get_full_name() or presence.user.username,
                'avatar': presence.identity_avatar,
                'is_online': presence.last_seen >= now - timedelta(seconds=60),
                'current_page': presence.current_page,
                'last_page': presence.last_page or presence.current_page,
                'last_visited_page': presence.current_page,
                'last_seen': presence.last_seen.isoformat(),
            } for presence in presences],
            'activity': [serialize_activity(activity) for activity in AdminActivity.objects.select_related('actor')[:100]],
        })
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    action_map = {
        'blog.post.created': 'Created blog post',
        'blog.post.deleted': 'Deleted blog post',
    }
    action = action_map.get(str(data.get('action', '')))
    if not action:
        return JsonResponse({'error': 'Unsupported activity action'}, status=400)
    page = str(data.get('page', '/admin/blog')).strip()
    if page != '/admin' and not page.startswith('/admin/'):
        page = '/admin/blog'
    details = data.get('details')
    title = str(details.get('title', '') if isinstance(details, dict) else '').strip()[:200]
    log_admin_activity(
        request,
        action,
        target_type='blog post',
        target_id=data.get('target_id', ''),
        details={'title': title},
        page=page,
    )
    return JsonResponse({'success': True}, status=201)