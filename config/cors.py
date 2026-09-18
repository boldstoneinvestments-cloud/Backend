import os


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        configured_origins = os.getenv(
            'CORS_ALLOWED_ORIGINS',
            'http://localhost:5173,http://localhost:5175,https://www.boldstoneinvestments.com,https://boldstoneinvestments.com',
        )
        self.allowed_origins = {
            origin.strip().rstrip('/')
            for origin in configured_origins.split(',')
            if origin.strip()
        }
        self.allowed_origins.update({
            'https://www.boldstoneinvestments.com',
            'https://boldstoneinvestments.com',
        })

    def __call__(self, request):
        response = self.get_response(request)
        origin = request.headers.get('Origin', '').strip().rstrip('/')
        if origin in self.allowed_origins:
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Headers'] = 'Content-Type'
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Vary'] = 'Origin'
        return response