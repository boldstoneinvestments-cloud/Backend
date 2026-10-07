import json
import secrets
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps

from django.contrib.auth import authenticate, get_user_model
from django.core.exceptions import ValidationError
from django.core import signing
from django.core.validators import EmailValidator
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    FarmerAdvice,
    FarmerAgronomyTask,
    FarmerCoffeePrice,
    FarmerCoffeeSale,
    FarmerFarm,
    FarmerHarvestEstimate,
    FarmerLoanApplication,
    FarmerOpportunity,
    FarmerPortalSettings,
    FarmerProfile,
    FarmerRewardBalance,
    FarmerRewardRule,
)

User = get_user_model()
FARMER_TOKEN_MAX_AGE = 60 * 60 * 24 * 30
CENT = Decimal('0.01')


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _json_error(message, status):
    return JsonResponse({'error': message}, status=status)


def _farmer_token(profile):
    return signing.dumps({
        'user_id': profile.user_id,
        'auth_version': profile.auth_version,
    }, salt='farmer-auth')


def _farmer_from_request(request):
    authorization = request.headers.get('Authorization', '')
    if not authorization.startswith('Bearer '):
        return None
    try:
        payload = signing.loads(
            authorization[7:],
            salt='farmer-auth',
            max_age=FARMER_TOKEN_MAX_AGE,
        )
        user = User.objects.filter(
            id=payload.get('user_id'), is_active=True, is_staff=False,
        ).first()
        profile = FarmerProfile.objects.filter(user=user).first() if user else None
        if profile is None or payload.get('auth_version') != profile.auth_version:
            return None
        return profile
    except (signing.BadSignature, TypeError, ValueError):
        return None


def farmer_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        profile = _farmer_from_request(request)
        if profile is None:
            return _json_error('Farmer sign-in required', 401)
        request.farmer_profile = profile
        return view(request, *args, **kwargs)
    return wrapped


def _active_farm(profile):
    return profile.farms.filter(is_active=True).first()


def _farm_payload(farm):
    return {
        'id': farm.id,
        'name': farm.name,
        'location': farm.location,
        'district': farm.district,
        'acres': farm.acres,
        'tree_count': farm.tree_count,
        'coffee_types': farm.coffee_types,
    }


def _task_payload(task):
    return {
        'id': task.id,
        'title': task.title,
        'detail': task.detail,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'is_urgent': task.is_urgent,
        'status': task.status,
        'created_at': task.created_at.isoformat(),
    }


def _sale_payload(sale):
    return {
        'id': sale.id,
        'delivery_date': sale.delivery_date.isoformat(),
        'grade': sale.grade,
        'quantity_kg': sale.quantity_kg,
        'price_per_kg': sale.price_per_kg,
        'amount': sale.quantity_kg * sale.price_per_kg,
        'buyer': sale.buyer,
        'payment_status': sale.payment_status,
    }


def _setting():
    return FarmerPortalSettings.objects.order_by('-id').first()


def _settings_payload(settings):
    return {
        'interest_rate': settings.interest_rate if settings else Decimal('10.00'),
        'weather_temperature': settings.weather_temperature if settings else Decimal('24.0'),
        'weather_summary': settings.weather_summary if settings else 'Partly cloudy',
        'weather_guidance': settings.weather_guidance if settings else '',
        'dashboard_notice': settings.dashboard_notice if settings else '',
    }


@csrf_exempt
def farmer_sign_up(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    if data is None:
        return _json_error('Invalid JSON body', 400)
    name = str(data.get('name', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    phone = str(data.get('phone', '')).strip()
    farm_name = str(data.get('farm_name', '')).strip()
    location = str(data.get('location', '')).strip()
    district = str(data.get('district', '')).strip()
    try:
        acres = Decimal(str(data.get('acres', '')))
        EmailValidator()(email)
    except (InvalidOperation, TypeError, ValueError):
        return _json_error('Enter a valid farm size', 400)
    except ValidationError:
        return _json_error('Enter a valid email address', 400)

    if not all((name, farm_name, location, district)) or len(password) < 8 or not acres.is_finite() or acres <= 0:
        return _json_error('Name, farm details, and a password of at least 8 characters are required', 400)
    if FarmerProfile.objects.filter(user__email__iexact=email).exists():
        return _json_error('A farmer account with that email already exists', 409)

    first_name, _, last_name = name.partition(' ')
    with transaction.atomic():
        user = User.objects.create_user(
            username=f'farmer-{secrets.token_hex(16)}',
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        profile = FarmerProfile.objects.create(user=user, phone=phone)
        farm = FarmerFarm.objects.create(
            farmer=profile,
            name=farm_name,
            location=location,
            district=district,
            acres=acres,
        )
    return JsonResponse({
        'token': _farmer_token(profile),
        'farmer': {'name': name, 'email': user.email, 'phone': profile.phone, 'farm': _farm_payload(farm)},
    }, status=201)


@csrf_exempt
def farmer_sign_in(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    if data is None:
        return _json_error('Invalid JSON body', 400)
    email = str(data.get('email', '')).strip().lower()
    user = User.objects.filter(
        email__iexact=email,
        is_staff=False,
        is_active=True,
        farmer_profile__isnull=False,
    ).first()
    password = data.get('password', '')
    user = authenticate(username=user.username, password=password if isinstance(password, str) else '') if user else None
    profile = FarmerProfile.objects.filter(user=user).first() if user else None
    if profile is None:
        return _json_error('Invalid farmer email or password', 401)
    farm = _active_farm(profile)
    return JsonResponse({
        'token': _farmer_token(profile),
        'farmer': {
            'name': user.get_full_name(),
            'email': user.email,
            'phone': profile.phone,
            'farm': _farm_payload(farm) if farm else None,
        },
    })


@csrf_exempt
@farmer_required
def farmer_sign_out(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    request.farmer_profile.auth_version += 1
    request.farmer_profile.save(update_fields=['auth_version'])
    return JsonResponse({'success': True})


@csrf_exempt
@farmer_required
def farmer_me(request):
    profile = request.farmer_profile
    farm = _active_farm(profile)
    if request.method == 'PATCH':
        data = _body(request)
        if data is None:
            return _json_error('Invalid JSON body', 400)
        phone = str(data.get('phone', profile.phone)).strip()
        farm_data = data.get('farm', {})
        if farm_data is not None and not isinstance(farm_data, dict):
            return _json_error('Farm details must be an object', 400)
        farm_values = {}
        if farm and isinstance(data.get('farm'), dict):
            for field in ('name', 'location', 'district'):
                if field in farm_data:
                    value = str(farm_data[field]).strip()
                    if not value:
                        return _json_error(f'{field.replace("_", " ").capitalize()} cannot be blank', 400)
                    farm_values[field] = value
            if 'acres' in farm_data:
                try:
                    acres = Decimal(str(farm_data['acres']))
                    if not acres.is_finite() or acres <= 0:
                        raise InvalidOperation
                    farm_values['acres'] = acres
                except (InvalidOperation, TypeError, ValueError):
                    return _json_error('Farm size must be a positive number', 400)
            if 'tree_count' in farm_data:
                try:
                    tree_count = int(farm_data['tree_count'])
                    if tree_count < 0:
                        raise ValueError
                    farm_values['tree_count'] = tree_count
                except (TypeError, ValueError):
                    return _json_error('Tree count must be a non-negative integer', 400)
            if 'coffee_types' in farm_data:
                coffee_types = farm_data['coffee_types']
                if not isinstance(coffee_types, list) or any(item not in ('robusta', 'arabica') for item in coffee_types):
                    return _json_error('Coffee types must be a list of robusta and/or arabica', 400)
                farm_values['coffee_types'] = coffee_types
        profile.phone = phone
        profile.save(update_fields=['phone'])
        if farm and farm_values:
            for field, value in farm_values.items():
                setattr(farm, field, value)
            farm.save(update_fields=list(farm_values))
    elif request.method != 'GET':
        return _json_error('Method not allowed', 405)
    return JsonResponse({
        'farmer': {
            'name': profile.user.get_full_name(),
            'email': profile.user.email,
            'phone': profile.phone,
            'farm': _farm_payload(farm) if farm else None,
        },
    })


@csrf_exempt
@farmer_required
def farmer_dashboard(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    latest_yield = farm.yield_records.order_by('-season').first()
    prices = list(FarmerCoffeePrice.objects.filter(is_active=True))
    highlighted_price = next((price for price in prices if price.grade.lower() == 'robusta faq'), prices[0] if prices else None)
    open_tasks = farm.agronomy_tasks.filter(status='open')
    priority_task = open_tasks.filter(is_urgent=True).first() or open_tasks.first()
    advice = FarmerAdvice.objects.filter(is_published=True).first()
    return JsonResponse({
        'farm': _farm_payload(farm),
        'settings': _settings_payload(_setting()),
        'metrics': {
            'expected_yield_tonnes': latest_yield.yield_tonnes if latest_yield else Decimal('0'),
            'productivity_kg_per_acre': latest_yield.productivity_kg_per_acre if latest_yield else Decimal('0'),
            'crop_health_score': latest_yield.crop_health_score if latest_yield else 0,
            'tree_survival_percent': latest_yield.tree_survival_percent if latest_yield else Decimal('0'),
            'coffee_price_per_kg': highlighted_price.price_per_kg if highlighted_price else None,
            'coffee_price_grade': highlighted_price.grade if highlighted_price else '',
            'open_task_count': open_tasks.count(),
        },
        'priority_task': _task_payload(priority_task) if priority_task else None,
        'advice': {
            'slug': advice.slug,
            'category': advice.category,
            'title': advice.title,
            'summary': advice.summary,
            'image': advice.image,
        } if advice else None,
    })


@csrf_exempt
@farmer_required
def farmer_performance(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    records = list(farm.yield_records.all())
    latest = records[-1] if records else None
    return JsonResponse({
        'farm': _farm_payload(farm),
        'records': [{
            'season': item.season,
            'yield_tonnes': item.yield_tonnes,
            'productivity_kg_per_acre': item.productivity_kg_per_acre,
            'crop_health_score': item.crop_health_score,
            'tree_survival_percent': item.tree_survival_percent,
            'notes': item.notes,
        } for item in records],
        'summary': {
            'productivity_kg_per_acre': latest.productivity_kg_per_acre if latest else Decimal('0'),
            'crop_health_score': latest.crop_health_score if latest else 0,
            'tree_survival_percent': latest.tree_survival_percent if latest else Decimal('0'),
        },
    })


@csrf_exempt
@farmer_required
def farmer_prices(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    prices = FarmerCoffeePrice.objects.filter(is_active=True)
    return JsonResponse({'prices': [{
        'id': item.id,
        'coffee_type': item.coffee_type,
        'grade': item.grade,
        'price_per_kg': item.price_per_kg,
        'change_30d_percent': item.change_30d_percent,
        'updated_at': item.updated_at.isoformat(),
    } for item in prices]})


@csrf_exempt
@farmer_required
def farmer_agronomy(request):
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    if request.method == 'GET':
        tasks = farm.agronomy_tasks.all()
        settings = _settings_payload(_setting())
        return JsonResponse({
            'tasks': [_task_payload(task) for task in tasks],
            'open_count': tasks.filter(status='open').count(),
            'settings': settings,
        })
    if request.method == 'POST':
        data = _body(request)
        title = str((data or {}).get('title', '')).strip()
        if not title:
            return _json_error('Task title is required', 400)
        task = FarmerAgronomyTask.objects.create(
            farm=farm,
            title=title,
            detail=str(data.get('detail', '')).strip(),
        )
        return JsonResponse({'task': _task_payload(task)}, status=201)
    return _json_error('Method not allowed', 405)


@csrf_exempt
@farmer_required
def farmer_agronomy_task(request, task_id):
    task = FarmerAgronomyTask.objects.filter(id=task_id, farm__farmer=request.farmer_profile).first()
    if task is None:
        return _json_error('Task not found', 404)
    if request.method != 'PATCH':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    status = (data or {}).get('status')
    if status not in ('open', 'completed'):
        return _json_error('Status must be open or completed', 400)
    task.status = status
    task.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'task': _task_payload(task)})


def _current_season(day):
    month = day.month
    if month in (9, 10, 11, 12, 1):
        return f'Main harvest {day.year if month >= 9 else day.year - 1}/{day.year + 1 if month >= 9 else day.year}'
    if month in (2, 3, 4):
        return f'Early harvest {day.year}'
    return f'Late harvest {day.year}'


@csrf_exempt
@farmer_required
def farmer_harvest(request):
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    estimates = farm.harvest_estimates.all()
    sales = farm.coffee_sales.all()
    return JsonResponse({
        'estimates': [{
            'id': item.id,
            'season': item.season,
            'coffee_type': item.coffee_type,
            'expected_quantity_kg': item.expected_quantity_kg,
            'updated_at': item.updated_at.isoformat(),
        } for item in estimates],
        'sales': [_sale_payload(sale) for sale in sales],
        'summary': {
            'harvest_forecast_kg': sum((item.expected_quantity_kg for item in estimates), Decimal('0')),
            'coffee_sold_kg': sum((sale.quantity_kg for sale in sales), Decimal('0')),
            'revenue_received': sum((sale.quantity_kg * sale.price_per_kg for sale in sales if sale.payment_status == 'paid'), Decimal('0')),
            'payment_pending': sum((sale.quantity_kg * sale.price_per_kg for sale in sales if sale.payment_status == 'pending'), Decimal('0')),
        },
    })


@csrf_exempt
@farmer_required
def farmer_harvest_estimate(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    if data is None:
        return _json_error('Invalid JSON body', 400)
    try:
        quantity = Decimal(str(data.get('expected_quantity_kg', '')))
        season = str(data.get('season', '')).strip()
        coffee_type = str(data.get('coffee_type', '')).strip().lower()
        if quantity <= 0 or not season or coffee_type not in ('robusta', 'arabica'):
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return _json_error('Enter a valid season, coffee type, and expected quantity', 400)
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    estimate, _ = FarmerHarvestEstimate.objects.update_or_create(
        farm=farm,
        season=season,
        coffee_type=coffee_type,
        defaults={'expected_quantity_kg': quantity},
    )
    return JsonResponse({'estimate': {
        'id': estimate.id,
        'season': estimate.season,
        'coffee_type': estimate.coffee_type,
        'expected_quantity_kg': estimate.expected_quantity_kg,
    }}, status=201)


@csrf_exempt
@farmer_required
def farmer_sale(request):
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    if data is None:
        return _json_error('Invalid JSON body', 400)
    try:
        delivery_date = date.fromisoformat(str(data.get('delivery_date', '')))
        quantity = Decimal(str(data.get('quantity_kg', '')))
        grade = str(data.get('grade', '')).strip()
        if quantity <= 0 or not grade:
            raise InvalidOperation
        price = Decimal(str(data.get('price_per_kg', '0')))
        if price < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError, ValueError):
        return _json_error('Enter a valid delivery date, grade, quantity, and price', 400)
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    sale = FarmerCoffeeSale.objects.create(
        farm=farm,
        delivery_date=delivery_date,
        grade=grade,
        quantity_kg=quantity,
        price_per_kg=price,
        buyer=str(data.get('buyer', '')).strip(),
    )
    return JsonResponse({'sale': _sale_payload(sale)}, status=201)


@csrf_exempt
@farmer_required
def farmer_opportunities(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    return JsonResponse({'opportunities': [{
        'id': item.id,
        'type': item.opportunity_type,
        'title': item.title,
        'detail': item.detail,
        'location': item.location,
        'closes_at': item.closes_at.isoformat() if item.closes_at else None,
        'action_label': item.action_label,
    } for item in FarmerOpportunity.objects.filter(is_published=True)]})


@csrf_exempt
@farmer_required
def farmer_rewards(request):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    balance = FarmerRewardBalance.objects.filter(farm=farm).first()
    rules = FarmerRewardRule.objects.filter(is_published=True)
    return JsonResponse({
        'balance': {
            'points': balance.points,
            'quality_score': balance.quality_score,
            'sustainability_score': balance.sustainability_score,
        } if balance else {'points': 0, 'quality_score': 0, 'sustainability_score': 0},
        'rewards': [{
            'id': item.id,
            'title': item.title,
            'description': item.description,
            'points_required': item.points_required,
        } for item in rules],
    })


@csrf_exempt
@farmer_required
def farmer_advice(request, slug=None):
    if request.method != 'GET':
        return _json_error('Method not allowed', 405)
    queryset = FarmerAdvice.objects.filter(is_published=True)
    if slug:
        item = queryset.filter(slug=slug).first()
        if item is None:
            return _json_error('Advice not found', 404)
        items = [item]
    else:
        items = list(queryset)
    return JsonResponse({'advice': [{
        'slug': item.slug,
        'category': item.category,
        'title': item.title,
        'summary': item.summary,
        'image': item.image,
        'image_alt': item.image_alt,
        'photo_caption': item.photo_caption,
        'lead': item.lead,
        'steps': item.steps,
        'note': item.note,
        'read_time': item.read_time,
    } for item in items]})


@csrf_exempt
@farmer_required
def farmer_loans(request):
    farm = _active_farm(request.farmer_profile)
    if farm is None:
        return _json_error('No active farm is assigned to this account', 404)
    if request.method == 'GET':
        settings = _setting()
        return JsonResponse({
            'interest_rate': settings.interest_rate if settings else Decimal('10.00'),
            'coffee_prices': [{
                'grade': item.grade,
                'coffee_type': item.coffee_type,
                'price_per_kg': item.price_per_kg,
            } for item in FarmerCoffeePrice.objects.filter(is_active=True)],
            'applications': [{
                'id': item.id,
                'loan_type': item.loan_type,
                'amount_requested': item.amount_requested,
                'coffee_grade': item.coffee_grade,
                'interest_rate': item.interest_rate,
                'repayment_amount': item.repayment_amount,
                'repayment_coffee_kg': item.repayment_coffee_kg,
                'harvest_season': item.harvest_season,
                'application_date': item.application_date.isoformat(),
                'status': item.status,
                'submitted_at': item.submitted_at.isoformat(),
            } for item in farm.loan_applications.all()],
        })
    if request.method != 'POST':
        return _json_error('Method not allowed', 405)
    data = _body(request)
    if data is None:
        return _json_error('Invalid JSON body', 400)
    try:
        amount = Decimal(str(data.get('amount_requested', '')))
        application_date = date.fromisoformat(str(data.get('application_date', '')))
        loan_type = str(data.get('loan_type', '')).strip()
        grade = FarmerCoffeePrice.objects.get(grade=str(data.get('coffee_grade', '')).strip(), is_active=True)
        if amount < Decimal('100000') or loan_type not in ('cash', 'fertilizer'):
            raise InvalidOperation
        if not amount.is_finite() or amount > Decimal('9999999999.99') or grade.price_per_kg <= 0:
            raise InvalidOperation
    except FarmerCoffeePrice.DoesNotExist:
        return _json_error('Select a currently available coffee grade', 400)
    except (InvalidOperation, TypeError, ValueError):
        return _json_error('Enter a valid loan type, amount, application date, and coffee grade', 400)

    settings = _setting()
    interest_rate = settings.interest_rate if settings else Decimal('10.00')
    repayment = (amount * (Decimal('1') + interest_rate / Decimal('100'))).quantize(CENT, rounding=ROUND_HALF_UP)
    if repayment > Decimal('9999999999.99'):
        return _json_error('The requested loan is above the supported maximum', 400)
    repayment_kg = (repayment / grade.price_per_kg).quantize(CENT, rounding=ROUND_HALF_UP)
    application = FarmerLoanApplication.objects.create(
        farm=farm,
        loan_type=loan_type,
        amount_requested=amount.quantize(CENT, rounding=ROUND_HALF_UP),
        coffee_grade=grade.grade,
        coffee_price_per_kg=grade.price_per_kg,
        interest_rate=interest_rate,
        repayment_amount=repayment,
        repayment_coffee_kg=repayment_kg,
        harvest_season=_current_season(application_date),
        application_date=application_date,
    )
    return JsonResponse({
        'application': {
            'id': application.id,
            'loan_type': application.loan_type,
            'amount_requested': application.amount_requested,
            'coffee_grade': application.coffee_grade,
            'interest_rate': application.interest_rate,
            'repayment_amount': application.repayment_amount,
            'repayment_coffee_kg': application.repayment_coffee_kg,
            'harvest_season': application.harvest_season,
            'application_date': application.application_date.isoformat(),
            'status': application.status,
        },
    }, status=201)