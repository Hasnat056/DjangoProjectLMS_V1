"""
Django settings for DjangoProjectLMS_V1 project.

Generated by 'django-admin startproject' using Django 5.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-eksy&y%u2hzay@cq=(x(em(603u^2%b7z3w@sd1387@*cq&x=f')

# SECURITY WARNING: don't run with debug turned on in production!
# For local development, DEBUG is True by default
DEBUG = True

# Allowed hosts - Local development only
ALLOWED_HOSTS = [
    'localhost',                                      # Local development
    '127.0.0.1',                                     # Local development alternative
    # 'djangoprojectlmsv1-production.up.railway.app',  # Railway production (commented out)
]

# CSRF settings for local development
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',                                  # Local development
    'http://127.0.0.1:8000',                                 # Local development alternative
    # 'https://djangoprojectlmsv1-production.up.railway.app',  # Railway production (commented out)
]

# Railway production security settings (all commented out for local development)
# if not DEBUG and os.environ.get('RAILWAY_ENVIRONMENT'):
#     # Railway production settings
#     SESSION_COOKIE_SECURE = True
#     CSRF_COOKIE_SECURE = True
#     SESSION_COOKIE_HTTPONLY = True
#     CSRF_COOKIE_HTTPONLY = True
#     SESSION_COOKIE_SAMESITE = 'Lax'
#     CSRF_COOKIE_SAMESITE = 'Lax'
#     SESSION_COOKIE_AGE = 86400  # 24 hours
#     SESSION_EXPIRE_AT_BROWSER_CLOSE = False
#     SESSION_SAVE_EVERY_REQUEST = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'Person.apps.PersonConfig',
    'AcademicStructure.apps.AcademicstructureConfig',
    'FacultyModule.apps.FacultymoduleConfig',
    'StudentModule.apps.StudentmoduleConfig',
    'pages.apps.PagesConfig',
    'accounts.apps.AccountsConfig',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'Person.middleware.AuditMiddleware',
]

ROOT_URLCONF = 'DjangoProjectLMS_V1.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'DjangoProjectLMS_V1.wsgi.application'

# Database configuration - Local development only
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'LMS',
        'USER': 'root',
        'PASSWORD': '@databaselab123',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
print("Using local MySQL database")

# Railway database configuration (commented out)
# if os.environ.get('RAILWAY_ENVIRONMENT'):
#     # Production (Railway) - Hardcoded MySQL connection
#     DATABASES = {
#         'default': {
#             'ENGINE': 'mysql.connector.django',
#             'NAME': 'railway',
#             'USER': 'root',
#             'PASSWORD': 'OfIdpzYBYZLTWhASnwvGOPqpKrsNGWVU',
#             'HOST': 'crossover.proxy.rlwy.net',
#             'PORT': 58556,
#             'OPTIONS': {
#                 'autocommit': True,
#             },
#         }
#     }
#     print("Using Railway MySQL database")

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images) - Local development configuration
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Railway production static files configuration (commented out)
# if IS_RAILWAY:
#     # Production static files configuration
#     STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#     STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# else:
#     # Local development - simpler configuration
#     STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
#     # Don't use WhiteNoise for local development

# Additional static files settings
STATICFILES_DIRS = [
    BASE_DIR / 'static',
] if (BASE_DIR / 'static').exists() else []

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Railway WhiteNoise configuration (commented out for local development)
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'