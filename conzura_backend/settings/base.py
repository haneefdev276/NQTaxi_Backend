from datetime import timedelta
from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-replace-this-with-50-char-secret-key')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'drf_spectacular',
    'apps.core',
    'apps.users',
    'apps.customers.apps.CustomersConfig',
    'apps.trips',
    'apps.ratings',
    'apps.notifications',
    'supportapps.apps.SupportappsConfig',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conzura_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'conzura_backend.wsgi.application'
ASGI_APPLICATION = 'conzura_backend.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='conzura_data'),
        'USER': config('DB_USER', default='postgres'),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=int(config('ACCESS_TOKEN_LIFETIME_MINUTES', default=60))),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=int(config('REFRESH_TOKEN_LIFETIME_DAYS', default=7))),
}

CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000,http://127.0.0.1:3000').split(',')

RAZORPAY_KEY_ID = config('RAZORPAY_KEY_ID', default='')
RAZORPAY_KEY_SECRET = config('RAZORPAY_KEY_SECRET', default='')
RAZORPAY_AUTO_COMPLETE_TOPUP = config('RAZORPAY_AUTO_COMPLETE_TOPUP', default=False, cast=bool)

SPECTACULAR_SETTINGS = {
    'TITLE': 'NQTaxi API',
    'DESCRIPTION': 'Backend API for NQTaxi ride-hailing application',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'TAGS': [
        {'name': 'Auth', 'description': 'Authentication and token endpoints'},
        {'name': 'Emergency Contacts', 'description': 'Manage emergency contacts'},
        {'name': 'Payment Methods', 'description': 'Manage rider payment methods'},
        {'name': 'Profile', 'description': 'Rider profile operations'},
        {'name': 'Ratings', 'description': 'Rating history and feedback'},
        {'name': 'Saved Places', 'description': 'Saved home/work/other locations'},
        {'name': 'Trip History', 'description': 'Rider trip history'},
        {'name': 'Wallet', 'description': 'Wallet balance and top-up'},
        {'name': 'Notifications', 'description': 'In-app notification feed and FCM device token registration'},
    ],
    'SWAGGER_UI_SETTINGS': {
        'operationsSorter': 'alpha',
        'tagsSorter': 'alpha',
        'filter': True,
        'displayRequestDuration': True,
        'defaultModelsExpandDepth': -1,
        'docExpansion': 'list',
        'showExtensions': True,
    },
    'SCHEMA_PATH_PREFIX': '/api/v1',
    'SCHEMA_PATH_PREFIX_TRIM': True,
}
