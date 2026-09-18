from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'local-development-only')
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = [host for host in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,.railway.app').split(',') if host]

INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.auth', 'api', 'shop']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'config.cors.CorsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = []
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {
	'default': dj_database_url.config(
		default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
		conn_max_age=600,
		ssl_require=os.getenv('DATABASE_SSL_REQUIRE', '0') == '1',
	)
}
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