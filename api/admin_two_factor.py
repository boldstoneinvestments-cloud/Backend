import base64
import hashlib
import hmac
import secrets
import time

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django_otp.plugins.otp_totp.models import TOTPDevice

from .models import AdminRecoveryCodes

PENDING_SESSION_KEY = 'admin_2fa_pending'
VERIFIED_SESSION_KEY = 'admin_2fa_verified'
IDENTITY_SELECTION_SESSION_KEY = 'admin_identity_selection_pending'
RECOVERY_FAILURES_SESSION_KEY = 'admin_2fa_recovery_failures'
PENDING_CHALLENGE_SECONDS = 600
RECOVERY_CODE_COUNT = 10
MAX_RECOVERY_ATTEMPTS = 5
TOTP_STEP_SECONDS = 30


def begin_admin_two_factor(request, user, identity_name):
    device_name = f'admin:{identity_name}'
    device, created = TOTPDevice.objects.get_or_create(
        user=user,
        name=device_name,
        defaults={'confirmed': False, 'step': TOTP_STEP_SECONDS, 'digits': 6},
    )
    if not created:
        changed = False
        if device.step != TOTP_STEP_SECONDS:
            device.step = TOTP_STEP_SECONDS
            changed = True
        if device.digits != 6:
            device.digits = 6
            changed = True
        if changed:
            device.save(update_fields=['step', 'digits'])
    request.session.pop(VERIFIED_SESSION_KEY, None)
    request.session.pop(RECOVERY_FAILURES_SESSION_KEY, None)
    request.session[PENDING_SESSION_KEY] = {
        'user_id': user.pk,
        'device_id': device.pk,
        'identity_name': identity_name,
        'started_at': int(time.time()),
    }
    request.session.modified = True
    return _two_factor_status(user, device, identity_name)


def pending_admin_two_factor(request):
    pending = request.session.get(PENDING_SESSION_KEY)
    if not isinstance(pending, dict):
        return None
    started_at = pending.get('started_at')
    if not isinstance(started_at, int) or time.time() - started_at > PENDING_CHALLENGE_SECONDS:
        request.session.pop(PENDING_SESSION_KEY, None)
        return None
    identity_name = pending.get('identity_name')
    device = TOTPDevice.objects.select_related('user').filter(
        pk=pending.get('device_id'),
        user_id=pending.get('user_id'),
        name=f'admin:{identity_name}',
    ).first()
    if (
        device is None
        or not isinstance(identity_name, str)
        or not identity_name
        or not device.user.is_active
        or not device.user.is_staff
    ):
        request.session.pop(PENDING_SESSION_KEY, None)
        return None
    return device.user, device, identity_name


def _two_factor_status(user, device, identity_name):
    setup_required = not device.confirmed
    result = {
        'pending': True,
        'setup_required': setup_required,
        'username': user.username,
        'identity_name': identity_name,
    }
    if setup_required:
        result['secret'] = base64.b32encode(device.bin_key).decode('ascii').rstrip('=')
        result['provisioning_uri'] = device.config_url
    return result


def admin_two_factor_status(request):
    pending = pending_admin_two_factor(request)
    if pending is None:
        return {'pending': False}
    user, device, identity_name = pending
    return _two_factor_status(user, device, identity_name)


def _recovery_code_digest(user, identity_name, normalized_code):
    message = f'admin-recovery:{user.pk}:{identity_name}:{normalized_code}'.encode('utf-8')
    digest = hmac.new(settings.SECRET_KEY.encode('utf-8'), message, hashlib.sha256).hexdigest()
    return f'hmac-sha256${digest}'


def _verify_recovery_code(user, identity_name, code):
    recovery, _ = AdminRecoveryCodes.objects.get_or_create(user=user)
    normalized_code = str(code).strip().upper().replace('-', '').replace(' ', '')
    hashes = recovery.identity_code_hashes.get(identity_name, [])
    candidate_digest = _recovery_code_digest(user, identity_name, normalized_code)
    for index, stored_hash in enumerate(hashes):
        if stored_hash.startswith('hmac-sha256$'):
            valid = hmac.compare_digest(candidate_digest, stored_hash)
        else:
            valid = check_password(normalized_code, stored_hash)
        if valid:
            hashes.pop(index)
            recovery.identity_code_hashes[identity_name] = hashes
            recovery.save(update_fields=['identity_code_hashes'])
            return True
    return False


def _new_recovery_codes(user, identity_name):
    codes = [secrets.token_hex(6).upper() for _ in range(RECOVERY_CODE_COUNT)]
    recovery, _ = AdminRecoveryCodes.objects.get_or_create(user=user)
    recovery.identity_code_hashes[identity_name] = [
        _recovery_code_digest(user, identity_name, code)
        for code in codes
    ]
    recovery.save(update_fields=['identity_code_hashes'])
    return [f'{code[:6]}-{code[6:]}' for code in codes]


def complete_admin_two_factor(request, token='', recovery_code=''):
    pending = pending_admin_two_factor(request)
    if pending is None:
        return None, {'error': 'Your verification session expired. Sign in again.'}, 401

    user, device, identity_name = pending
    if not request.user.is_authenticated or request.user.pk != user.pk:
        return None, {'error': 'Sign in again before verifying this admin identity.'}, 401
    setup_required = not device.confirmed
    if recovery_code and not setup_required:
        failures = request.session.get(RECOVERY_FAILURES_SESSION_KEY, 0)
        if failures >= MAX_RECOVERY_ATTEMPTS:
            return None, {'error': 'Too many recovery-code attempts. Sign in again.'}, 429
        valid = _verify_recovery_code(user, identity_name, recovery_code)
        if not valid:
            request.session[RECOVERY_FAILURES_SESSION_KEY] = failures + 1
        else:
            request.session.pop(RECOVERY_FAILURES_SESSION_KEY, None)
    else:
        token_value = str(token).strip()
        valid = token_value.isdigit() and len(token_value) == device.digits and device.verify_token(int(token_value))
    if not valid:
        return None, {'error': 'Invalid verification code.'}, 400

    recovery_codes = []
    if setup_required:
        device.confirmed = True
        device.save(update_fields=['confirmed'])
        recovery_codes = _new_recovery_codes(user, identity_name)

    request.session.pop(PENDING_SESSION_KEY, None)
    request.session.pop(RECOVERY_FAILURES_SESSION_KEY, None)
    request.session[IDENTITY_SELECTION_SESSION_KEY] = False
    request.session['admin_identity_name'] = identity_name
    request.session[VERIFIED_SESSION_KEY] = True
    request.session.modified = True
    return user, {'success': True, 'identity_name': identity_name, 'recovery_codes': recovery_codes}, 200