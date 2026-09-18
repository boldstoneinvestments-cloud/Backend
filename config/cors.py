import os


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.allowed_origins = set(os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5173').split(','))

    def __call__(self, request):
        response = self.get_response(request)
        origin = request.headers.get('Origin')
        if origin in self.allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        return response