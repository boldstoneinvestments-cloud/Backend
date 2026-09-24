from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-development-only')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [host for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.railway.app').split(',') if host]
CSRF_TRUSTED_ORIGINS = [origin for origin in os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:5173,http://localhost:5175,http://127.0.0.1:5173,http://127.0.0.1:5175,https://www.boldstoneinvestments.com,https://boldstoneinvestments.com').split(',') if origin]

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'api',
	'shop',
]
MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'config.cors.CorsMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
	'BACKEND': 'django.template.backends.django.DjangoTemplates',
	'DIRS': [],
	'APP_DIRS': True,
	'OPTIONS': {
		'context_processors': [
			'django.template.context_processors.request',
			'django.contrib.auth.context_processors.auth',
			'django.contrib.messages.context_processors.messages',
		],
	},
}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {
	'default': dj_database_url.config(
		default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
		conn_max_age=60,
		conn_health_checks=True,
		ssl_require=os.getenv('DATABASE_SSL_REQUIRE', '0') == '1',
	)
}
if DATABASES['default']['ENGINE'].endswith('postgresql'):
	DATABASES['default'].setdefault('OPTIONS', {})['connect_timeout'] = 5
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
USE_TZ = True
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' if os.getenv('EMAIL_HOST') else 'django.core.mail.backends.console.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', '1') == '1'
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'webmaster@localhost')
EMAIL_TO = os.getenv('EMAIL_TO', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
APPEND_SLASH = False
STATIC_URL = '/static/'
MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_URL = '/media/'
SESSION_COOKIE_SAMESITE = 'None' if not DEBUG else 'Lax'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'None' if not DEBUG else 'Lax'
CSRF_COOKIE_SECURE = not DEBUG