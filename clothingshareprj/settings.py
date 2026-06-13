"""
Django settings for clothingshareprj project - PRODUCTION READY
Compatible with both local development and free hosting on Render
"""

from pathlib import Path
import os
import dj_database_url
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================
# SECURITY WARNING: Keep these secrets safe!
# ============================================================

# SECURITY WARNING: keep the secret key used in production secret!
# Use environment variable in production, fallback for local development
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-*1ihil(n@8wliktg00m**yoaln)+!uwq$u21#j=-uki3ak1r)4')

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG=False in production environment variables
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Allow all hosts in production (Render provides domain), restrict locally
ALLOWED_HOSTS = [
    '127.0.0.1',
    'localhost',
    '0.0.0.0',
    '.onrender.com',  # Allows any Render subdomain
    'clothshare.onrender.com',  # Your specific Render URL
]

# ============================================================
# Application definition
# ============================================================

INSTALLED_APPS = [
    'jazzmin',  # Admin theme
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',  # Required for password reset functionality
    
    # WhiteNoise for static files in production
    'whitenoise.runserver_nostatic',
    
    # Your custom apps
    'core.apps.CoreConfig',
    'userauths',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # For serving static files in production
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'clothingshareprj.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'clothingshareprj.wsgi.application'

# ============================================================
# Database Configuration
# Supports PostgreSQL (production) and SQLite (local fallback)
# ============================================================

# Use DATABASE_URL environment variable if provided (Render sets this automatically)
# Otherwise use local PostgreSQL for development
if os.getenv('DATABASE_URL'):
    DATABASES = {
        'default': dj_database_url.config(
            conn_max_age=600,
            ssl_require=True  # Render requires SSL for PostgreSQL
        )
    }
else:
    # Local development database (PostgreSQL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('DB_NAME', 'clothshare_db'),
            'USER': os.getenv('DB_USER', 'postgres'),
            'PASSWORD': os.getenv('DB_PASSWORD', '0769116880JK'),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }

# ============================================================
# Password validation
# ============================================================

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

# ============================================================
# Internationalization
# ============================================================

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# ============================================================
# Static files (CSS, JavaScript, Images)
# ============================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

# WhiteNoise configuration for static files in production
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files (User uploaded images)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# ============================================================
# Default primary key field type
# ============================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================
# Jazzmin Admin Theme Settings
# ============================================================

JAZZMIN_SETTINGS = {
    "site_header": "Share Donation",
    "site_brand": "Donate Now",
    "site_logo": "assets/images/logo.png",
    "copyright": "cloth_share.com",
    "show_ui_builder": True,
}

# ============================================================
# Custom User Model
# ============================================================

AUTH_USER_MODEL = 'userauths.User'

# ============================================================
# Authentication Settings
# ============================================================

LOGIN_URL = '/auth/sign-in/'
LOGIN_REDIRECT_URL = '/profile/'
LOGOUT_REDIRECT_URL = '/'

# Session settings
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = True

# ============================================================
# Email Configuration (Gmail SMTP)
# ============================================================

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'clothshareinfo@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'pqimlvsexviqpbac')
DEFAULT_FROM_EMAIL = f'ClothShare <{EMAIL_HOST_USER}>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMIN_EMAIL = EMAIL_HOST_USER
EMAIL_TIMEOUT = 30

# ============================================================
# Site Information (for password reset)
# ============================================================

SITE_ID = 1
PASSWORD_RESET_TIMEOUT = 86400  # 24 hours

# ============================================================
# Newsletter Settings
# ============================================================

SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')
NEWSLETTER_FROM_EMAIL = f'ClothShare Newsletter <{EMAIL_HOST_USER}>'
NEWSLETTER_ADMIN_EMAILS = [EMAIL_HOST_USER]

NEWSLETTER_DEFAULT_PREFERENCES = {
    'receive_donation_updates': True,
    'receive_exchange_notifications': False,
    'receive_new_items_alerts': True,
    'receive_community_news': True,
    'receive_request_updates': False,
}

# ============================================================
# Media files configuration for development
# ============================================================

if DEBUG:
    # This will be used in urls.py to serve media files
    from django.conf.urls.static import static
    MEDIA_URL_CONFIG = static(MEDIA_URL, document_root=MEDIA_ROOT)
else:
    MEDIA_URL_CONFIG = []

# ============================================================
# Security Settings for Production
# ============================================================

if not DEBUG:
    # HTTPS security
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    
    # HTTP Strict Transport Security
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Additional security headers
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    
    # Referrer Policy
    SECURE_REFERRER_POLICY = 'same-origin'

# ============================================================
# CSRF Trusted Origins
# ============================================================

CSRF_TRUSTED_ORIGINS = [
    'http://127.0.0.1:8000',
    'http://localhost:8000',
    'https://clothshare.onrender.com',
    'https://*.onrender.com',
]

# ============================================================
# Logging Configuration
# ============================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console', 'file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

# ============================================================
# Custom Settings for Your Application
# ============================================================

# Maximum size for uploaded files (5MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880

# Number of fields allowed in a form submission
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000