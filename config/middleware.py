import os

from django.http import HttpResponseRedirect

from api.admin_two_factor import IDENTITY_SELECTION_SESSION_KEY, VERIFIED_SESSION_KEY


class RequireAdminTwoFactorMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith('/admin/')
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_staff
            and not request.session.get(VERIFIED_SESSION_KEY)
        ):
            request.session[IDENTITY_SELECTION_SESSION_KEY] = True
            request.session.pop('admin_identity_name', None)
            request.session.modified = True
            frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173').strip().rstrip('/')
            return HttpResponseRedirect(f'{frontend_url}/admin')
        return self.get_response(request)