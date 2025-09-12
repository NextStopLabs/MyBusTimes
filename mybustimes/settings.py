from dotenv import load_dotenv
from pathlib import Path
import os

from django.utils.translation import gettext_lazy as _

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / "mybustimes/.env")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = ['*']

DISCORD_FOR_SALE_WEBHOOK = os.environ["DISCORD_FOR_SALE_WEBHOOK"]
DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK = os.environ["DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK"]
DISCORD_TYPE_REQUEST_WEBHOOK = os.environ["DISCORD_TYPE_REQUEST_WEBHOOK"]
DISCORD_WEB_ERROR_WEBHOOK = os.environ["DISCORD_WEB_ERROR_WEBHOOK"]
DISCORD_404_ERROR_WEBHOOK = os.environ["DISCORD_404_ERROR_WEBHOOK"]

# Cloudflare Turnstile Site Key
CF_SITE_KEY = os.environ.get("CF_SITE_KEY")
CF_SECRET_KEY = os.environ.get("CF_SECRET_KEY")

# Discord Bot API URL
DISCORD_BOT_API_URL = os.environ.get("DISCORD_BOT_API_URL")

# Channel IDs for Discord
DISCORD_LIVERY_ID = os.environ.get("DISCORD_LIVERY_ID")
DISCORD_MIGRATION_ERROR_ID = os.environ.get("DISCORD_MIGRATION_ERROR_ID")
DISCORD_REPORTS_CHANNEL_ID = os.environ["DISCORD_REPORTS_CHANNEL_ID"]
DISCORD_GAME_ID = os.environ.get("DISCORD_GAME_ID")

if not DEBUG:
    STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]
    STRIPE_PUBLISHABLE_KEY = os.environ["STRIPE_PUBLISHABLE_KEY"]
    STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
    STRIPE_BILLING_PORTAL_URL = os.environ["STRIPE_BILLING_PORTAL_URL"]
else:
    STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY_TEST"]
    STRIPE_PUBLISHABLE_KEY = os.environ["STRIPE_PUBLISHABLE_KEY_TEST"]
    STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET_TEST"]
    STRIPE_BILLING_PORTAL_URL = "#"

CSRF_TRUSTED_ORIGINS = [
    'https://v2.mybustimes.cc',
    'https://dev-v2.mybustimes.cc',
    'https://www.mybustimes.cc',
    'https://www.myfleets.cc'
]

AUTH_USER_MODEL = 'main.CustomUser'
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_filters',
    'rest_framework',
    'tracking',
    'main',
    'fleet',
    'routes',
    'gameData',
    'corsheaders',
    'group',
    'wiki',
    'markdownx',
    'account',
    'admin_dash',
    'debug_toolbar',
    'forum',
    'tickets',
    'apply',
    'messaging',
    'django_select2',
    'a',

    'djangocms_simple_admin_style',
    'django.contrib.sites',
    'cms',
    'menus',

    'djangocms_text',
    'djangocms_link',
    'djangocms_alias',
    'djangocms_versioning',

    'sekizai',
    'treebeard',
    'parler',

    'filer',
    'easy_thumbnails',
    'djangocms_frontend',
    'djangocms_frontend.contrib.accordion',
    'djangocms_frontend.contrib.alert',
    'djangocms_frontend.contrib.badge',
    'djangocms_frontend.contrib.card',
    'djangocms_frontend.contrib.carousel',
    'djangocms_frontend.contrib.collapse',
    'djangocms_frontend.contrib.content',
    'djangocms_frontend.contrib.grid',
    'djangocms_frontend.contrib.icon',
    'djangocms_frontend.contrib.image',
    'djangocms_frontend.contrib.jumbotron',
    'djangocms_frontend.contrib.link',
    'djangocms_frontend.contrib.listgroup',
    'djangocms_frontend.contrib.media',
    'djangocms_frontend.contrib.navigation',
    'djangocms_frontend.contrib.tabs',
    'djangocms_frontend.contrib.utilities',
]

MIDDLEWARE = []

if DEBUG == True:
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
else:
    MIDDLEWARE.append('main.middleware.CustomErrorMiddleware')

MIDDLEWARE.append('main.middleware.CustomErrorMiddleware')

MIDDLEWARE.extend([
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'main.middleware.SiteLockMiddleware',
    'main.middleware.SiteImportingMiddleware',
    'main.middleware.SiteUpdatingMiddleware',
    'main.middleware.QueueMiddleware',
    'mybustimes.middleware.rest_last_active.UpdateLastActiveMiddleware',
    'django_ratelimit.middleware.RatelimitMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'cms.middleware.user.CurrentUserMiddleware',
    'cms.middleware.page.CurrentPageMiddleware',
    'cms.middleware.toolbar.ToolbarMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'cms.middleware.language.LanguageCookieMiddleware',
    "main.middleware.StaffOnlyDocsMiddleware",
])

CORS_ALLOW_ALL_ORIGINS = True

RATELIMIT_VIEW = 'main.views.ratelimit_view'

INTERNAL_IPS = [
    "127.0.0.1",  # localhost
]

ROOT_URLCONF = 'mybustimes.urls'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)
    
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'main.context_processors.theme_settings',
                'sekizai.context_processors.sekizai',
                'cms.context_processors.cms_settings',
            ],
        },
    },
]

THUMBNAIL_PROCESSORS = (
    'easy_thumbnails.processors.colorspace',
    'easy_thumbnails.processors.autocrop',
    'filer.thumbnail_processors.scale_and_crop_with_subject_location',
    'easy_thumbnails.processors.filters',
)

ASGI_APPLICATION = 'mybustimes.asgi.application'

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

try:
    from .settings_local import *
except ImportError:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv("DB_NAME"),
            'USER': os.getenv("DB_USER"),
            'PASSWORD': os.getenv("DB_PASSWORD"),
            'HOST': os.getenv("DB_HOST"),
            'PORT': os.getenv("DB_PORT"),
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


AUTHENTICATION_BACKENDS = [
    'mybustimes.auth_backends.PHPFallbackBackend',
    'django.contrib.auth.backends.ModelBackend',  # fallback to default just in case
]

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_L10N = True
USE_TZ = True

DEFAULT_FROM_EMAIL = 'MyBusTimes <no-reply@mybustimes.cc>'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv("SMTP_HOST")
EMAIL_PORT = os.getenv("SMTP_PORT")
EMAIL_HOST_USER = os.getenv("SMTP_USER")
EMAIL_HOST_PASSWORD = os.getenv("SMTP_PASSWORD")
EMAIL_USE_TLS = False
EMAIL_USE_SSL = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = '/account/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'ERROR',
    },
}

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

CMS_CONFIRM_VERSION4 = True
SITE_ID = 1
CMS_TEMPLATES = (
    ("base.html", _("Standard")),
)
CMS_PERMISSION = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
TEXT_INLINE_EDITING = True
DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True
