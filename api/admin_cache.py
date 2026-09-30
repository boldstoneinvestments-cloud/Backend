import hashlib
import json
from functools import wraps

from django.core.cache import cache
from django.http import JsonResponse


CACHE_TTLS = {
    'admin_users': 60,
    'admin_customers': 30,
    'admin_orders': 30,
    'admin_lease_applications': 30,
    'admin_chat': 60,
    'admin_activity': 15,
    'customer_chat': 60,
    'shop_products': 300,
    'estate': 60,
}


def cache_scope(value):
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()


def _version_key(namespace, scope):
    return f'boldstone:cache-version:{namespace}:{scope}'


def _data_key(namespace, scope):
    global_version = cache.get(_version_key(namespace, 'all'), 0)
    scope_version = 0 if scope == 'all' else cache.get(_version_key(namespace, cache_scope(scope)), 0)
    scope_key = 'all' if scope == 'all' else cache_scope(scope)
    return f'boldstone:data:{namespace}:{global_version}:{scope_version}:{scope_key}'


def get_admin_cache(namespace, scope='all'):
    return cache.get(_data_key(namespace, scope))


def set_admin_cache(namespace, data, scope='all'):
    cache.set(_data_key(namespace, scope), data, CACHE_TTLS[namespace])


def invalidate_admin_cache(namespace, scope='all'):
    version_scope = 'all' if scope == 'all' else cache_scope(scope)
    version_key = _version_key(namespace, version_scope)
    try:
        if not cache.add(version_key, 1, timeout=max(CACHE_TTLS.values()) * 2):
            cache.incr(version_key)
    except Exception:
        return


def cache_json_response(namespace, scope=None):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if request.method != 'GET':
                return view(request, *args, **kwargs)

            cache_scope_value = scope(request) if callable(scope) else (scope or 'all')
            cached_data = get_admin_cache(namespace, cache_scope_value)
            if cached_data is not None:
                return JsonResponse(cached_data)

            response = view(request, *args, **kwargs)
            if response.status_code == 200 and isinstance(response, JsonResponse):
                try:
                    response_data = json.loads(response.content)
                except (TypeError, ValueError):
                    return response
                set_admin_cache(namespace, response_data, cache_scope_value)
            return response

        return wrapped

    return decorate