import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(path):
        """Load simple KEY=VALUE pairs when dependencies are not installed yet."""
        if not Path(path).exists():
            return
        for line in Path(path).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ('true', '1', 'yes')


DEBUG = env_bool('DEBUG', False)
SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-expansio-build-and-dev-secret-key-change-in-prod'
)
if not SECRET_KEY or SECRET_KEY == 'replace-with-a-long-random-secret':
    SECRET_KEY = 'django-insecure-expansio-build-and-dev-secret-key-change-in-prod'

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,.railway.app').split(',')
    if host.strip()
]
railway_public_domain = (
    os.environ.get('RAILWAY_PUBLIC_DOMAIN', '')
    .strip()
    .removeprefix('https://')
    .removeprefix('http://')
    .rstrip('/')
)
if railway_public_domain and railway_public_domain not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(railway_public_domain)

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]
if railway_public_domain:
    railway_origin = f'https://{railway_public_domain}'
    if railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(railway_origin)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'expansio',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
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
    },
]

WSGI_APPLICATION = 'project.wsgi.application'


DATABASE_URL = os.environ.get('DATABASE_URL') or os.environ.get('MYSQL_URL')

mysql_db = os.environ.get('MYSQLDATABASE') or os.environ.get('MYSQL_DATABASE')
mysql_user = os.environ.get('MYSQLUSER') or os.environ.get('MYSQL_USER')
mysql_password = os.environ.get('MYSQLPASSWORD') or os.environ.get('MYSQL_PASSWORD', '')
mysql_host = os.environ.get('MYSQLHOST') or os.environ.get('MYSQL_HOST')
mysql_port = os.environ.get('MYSQLPORT') or os.environ.get('MYSQL_PORT', '3306')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    }
elif mysql_db and (mysql_host or mysql_user):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': mysql_db,
            'USER': mysql_user or 'root',
            'PASSWORD': mysql_password,
            'HOST': mysql_host or '127.0.0.1',
            'PORT': int(mysql_port) if str(mysql_port).isdigit() else 3306,
            'CONN_MAX_AGE': 600,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'expansio.sqlite3',
        }
    }

if DATABASES['default'].get('ENGINE') == 'django.db.backends.mysql':
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS'].setdefault('charset', 'utf8mb4')
    DATABASES['default']['OPTIONS'].setdefault(
        'init_command', "SET sql_mode='STRICT_TRANS_TABLES'"
    )


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_TZ = True


STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {
        'BACKEND': (
            'django.contrib.staticfiles.storage.StaticFilesStorage'
            if DEBUG
            else 'whitenoise.storage.CompressedManifestStaticFilesStorage'
        )
    },
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)
EMAIL_TIMEOUT = 10

LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/login/'

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Railway health checks reach the application directly over its private network.
    SECURE_REDIRECT_EXEMPT = [r'^health/$']

SESSION_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
