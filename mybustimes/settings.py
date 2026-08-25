from boto3.s3.transfer import TransferConfig
from dotenv import load_dotenv
from pathlib import Path
import os
import subprocess
import urllib.parse as urlparse

from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "https://www.mybustimes.cc"
load_dotenv(BASE_DIR / "mybustimes/.env")

DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
SECRET_KEY = os.environ["SECRET_KEY"]
ALLOWED_HOSTS = ['*']


def _env_float(name, default):
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _env_int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_release():
    if os.getenv("SENTRY_RELEASE"):
        return os.getenv("SENTRY_RELEASE")
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None


MEMORY_DIAGNOSTICS_ENABLED = os.getenv("MEMORY_DIAGNOSTICS_ENABLED", "False").lower() in ("true", "1", "yes")
MEMORY_DIAGNOSTICS_THRESHOLD_MB = _env_float("MEMORY_DIAGNOSTICS_THRESHOLD_MB", 500.0)
MEMORY_DIAGNOSTICS_DELTA_MB = _env_float("MEMORY_DIAGNOSTICS_DELTA_MB", 100.0)
MEMORY_DIAGNOSTICS_SAMPLE_RATE = min(max(_env_float("MEMORY_DIAGNOSTICS_SAMPLE_RATE", 1.0), 0.0), 1.0)
MEMORY_DIAGNOSTICS_TRACE_LIMIT = max(_env_int("MEMORY_DIAGNOSTICS_TRACE_LIMIT", 8), 1)
MEMORY_DIAGNOSTICS_TRACE_FRAMES = max(_env_int("MEMORY_DIAGNOSTICS_TRACE_FRAMES", 25), 1)
MEMORY_DIAGNOSTICS_IGNORED_PATH_PREFIXES = ('/static/', '/media/', '/favicon.ico', '/robots.txt')

DISCORD_GUILD_ID = os.environ["DISCORD_GUILD_ID"]
DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_API_TOKEN"]

DISCORD_FOR_SALE_WEBHOOK = os.environ["DISCORD_FOR_SALE_WEBHOOK"]
DISCORD_FOR_SALE_CHANNEL_ID = os.environ["DISCORD_FOR_SALE_CHANNEL_ID"]
DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK = os.environ["DISCORD_OPERATOR_TYPE_REQUESTS_CHANNEL_WEBHOOK"]
DISCORD_TYPE_REQUEST_WEBHOOK = os.environ["DISCORD_TYPE_REQUEST_WEBHOOK"]
DISCORD_SUSPICIOUS_USER_WEBHOOK = os.getenv("DISCORD_SUSPICIOUS_USER_WEBHOOK")

VPN_DETECTION_API_URL = os.getenv("VPN_DETECTION_API_URL", "https://proxycheck.io/v2")
VPN_DETECTION_API_KEY = os.getenv("VPN_DETECTION_API_KEY")

ROUTEING_URL = os.getenv("VALHALLA_URL")
VALHALLA_USER = os.getenv("VALHALLA_USER")
VALHALLA_PASS = os.getenv("VALHALLA_PASS")

ORR_URL = os.getenv("ORR_URL")

ACKEE_DOMAIN_ID = os.getenv("ACKEE_DOMAIN_ID")

CRON_SECRET = os.getenv("CRON_SECRET")

# Cloudflare Turnstile Site Key
CF_SITE_KEY = os.getenv("CF_SITE_KEY")
CF_SECRET_KEY = os.getenv("CF_SECRET_KEY")

# Discord Bot API URL
DISCORD_BOT_API_URL = os.getenv("DISCORD_BOT_API_URL")

# Channel IDs for Discord
DISCORD_LIVERY_ID = os.getenv("DISCORD_LIVERY_ID")
DISCORD_MIGRATION_ERROR_ID = os.getenv("DISCORD_MIGRATION_ERROR_ID")
DISCORD_REPORTS_CHANNEL_ID = os.environ["DISCORD_REPORTS_CHANNEL_ID"]
DISCORD_GAME_ID = os.getenv("DISCORD_GAME_ID")
DISCORD_OPERATOR_LOGS_ID = os.getenv("DISCORD_OPERATOR_LOGS_ID")
DISCORD_PRO_ROLE_ID = os.getenv("DISCORD_PRO_ROLE_ID", "1509700151361536200")
DISCORD_AD_FREE_ROLE_ID = os.getenv("DISCORD_AD_FREE_ROLE_ID")
DISCORD_BOOSTER_AD_FREE_ENABLED = os.getenv("DISCORD_BOOSTER_AD_FREE_ENABLED", "True").lower() in ("true", "1", "yes")
DISCORD_OAUTH_CLIENT_ID = os.getenv("DISCORD_OAUTH_CLIENT_ID", os.getenv("DISCORD_CLIENT_ID"))
DISCORD_OAUTH_CLIENT_SECRET = os.getenv("DISCORD_OAUTH_CLIENT_SECRET", os.getenv("DISCORD_CLIENT_SECRET"))
DISCORD_OAUTH_REDIRECT_URI = os.getenv(
    "DISCORD_OAUTH_REDIRECT_URI",
    f"{BASE_URL}/account/connections/callback/",
)


STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]
STRIPE_PUBLISHABLE_KEY = os.environ["STRIPE_PUBLISHABLE_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]

# Basic Plan
STRIPE_BASIC_MONTHLY_PRICE_ID = os.environ.get("BASIC_PRICE_ID_MONTHLY")
STRIPE_BASIC_YEARLY_PRICE_ID = os.environ.get("BASIC_PRICE_ID_YEARLY")
STRIPE_BASIC_ONE_OFF_PRICE_ID = os.environ.get("BASIC_PRICE_ID_ONE_OFF")

# Pro Plan
STRIPE_PRO_MONTHLY_PRICE_ID = os.environ.get("PRO_PRICE_ID_MONTHLY")
STRIPE_PRO_YEARLY_PRICE_ID = os.environ.get("PRO_PRICE_ID_YEARLY")
STRIPE_PRO_ONE_OFF_PRICE_ID = os.environ.get("PRO_PRICE_ID_ONE_OFF")

# Legacy / Other
STRIPE_MONTHLY_PRICE_ID = os.environ.get("PRICE_ID_MONTHLY")
STRIPE_YEARLY_PRICE_ID = os.environ.get("PRICE_ID_YEARLY")
STRIPE_CUSTOM_PRICE_ID = os.environ.get("PRICE_ID_CUSTOM")

STRIPE_BILLING_PORTAL_URL = os.environ.get("STRIPE_BILLING_PORTAL_URL")

CSRF_TRUSTED_ORIGINS = [
    #PR preview URL
    'https://*.nextstoplabs.org',
    'https://staging.mybustimes.cc',

    
    'https://mybustimes.cc',
    'https://www.mybustimes.cc',
    'https://local-dev.mybustimes.cc',
    'https://mbt.nextstoplabs.org',
]

AUTH_USER_MODEL = 'main.CustomUser'
USE_X_FORWARDED_HOST = True

INSTALLED_APPS = [
    'django_otp',
    'django_otp.plugins.otp_static',
    'django_otp.plugins.otp_totp',
    'two_factor',
#    'djangocms_simple_admin_style',  # ← only once, before django.contrib.admin
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'django_filters',
    "admin_auto_filters",
    
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
    #'debug_toolbar',
    'forum',
    'storages',
    'tickets',
    'apply',
    'messaging',
    'django_select2',
    'a',
    'simple_history',
    'words',
    'django.contrib.sites',
    'cms',
    'menus',

    'giveaway',

    'djangocms_text',
    'djangocms_link',
    'djangocms_alias',
    'djangocms_versioning',

    'sekizai',
    'treebeard',
    'parler',

    'filer',
    'easy_thumbnails',
    "mozilla_django_oidc",
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

MIDDLEWARE = [
#    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

MIDDLEWARE.extend([
    #'mybustimes.middleware.performance_middleware.PerformanceLoggingMiddleware',
    #'mybustimes.middleware.performance_middleware.DatabaseQueryLoggingMiddleware',
    #'mybustimes.middleware.memory_debug.MemoryDebugMiddleware',
    #'mybustimes.middleware.db_diagnostics.DatabaseDiagnosticsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_otp.middleware.OTPMiddleware',
    'main.middleware.FeatureBanMiddleware',
    'admin_dash.middleware.RequireOTPMiddleware',  
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
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
    "mybustimes.middleware.rest_last_active.ResetProMiddleware",
])

CORS_ALLOW_ALL_ORIGINS = True

RATELIMIT_VIEW = 'main.views.ratelimit_view'

INTERNAL_IPS = ["127.0.0.1", "::1"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
}

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
        'DIRS': [BASE_DIR / 'templates'],  # ← Add this
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.i18n',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                #'mybustimes.context_processors.memory_debug',
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

ASYNC_CLOSE_CONNECTIONS = True

def _get_db_thread_pool_size():
    try:
        return max(1, int(os.getenv("DB_THREAD_POOL_SIZE", "4")))
    except (TypeError, ValueError):
        return 4


DB_THREAD_POOL_SIZE = _get_db_thread_pool_size()

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.getenv("REDIS_URL", "redis://localhost:6379/1")],
            "symmetric_encryption_keys": [SECRET_KEY],
            "capacity": 1000,
            "expiry": 60,
        },
    },
}

if os.getenv("USE_IN_MEMORY_CHANNEL_LAYER", "False").lower() in ("true", "1", "yes"):
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        },
    }

SKIP_DB_STATEMENT_TIMEOUT = os.getenv("SKIP_DB_STATEMENT_TIMEOUT", "").lower() in ("true", "1", "yes")

try:
    from .settings_local import *
except ImportError:
    def _is_pgbouncer_target(host, port):
        """Detect PgBouncer so we can force safe pooling defaults."""
        h = (host or "").lower()
        if any(k in h for k in ("pgbouncer", "proxy", "railway", "rlwy")):
            return True
        # In this project PgBouncer listens on 5433; direct Postgres on 4511/5432.
        if port == 5433:
            return True
        return False

    def _parse_database_url(db_url):
        p = urlparse.urlparse(db_url)
        engine = "django.db.backends.postgresql" if p.scheme and p.scheme.startswith("postgres") else "django.db.backends.sqlite3"
        # Force CONN_MAX_AGE=0 behind PgBouncer (transaction pooling). For
        # direct Postgres prod now uses CONN_MAX_AGE=0 as well; default to 0
        # to avoid the previous 60s default that pinned connections.
        host = p.hostname
        port = p.port
        is_pgbouncer = _is_pgbouncer_target(host, port)
        raw_age = os.getenv("CONN_MAX_AGE")
        if is_pgbouncer:
            conn_max_age = 0
        else:
            # Default 0 (was 60) – persistent connections are incompatible
            # with ASGI thread-pool unless explicitly opted-in.
            conn_max_age = int(raw_age) if raw_age is not None else 0

        # CONN_HEALTH_CHECKS is useful when CONN_MAX_AGE>0; harmless at 0.
        conn_health_checks = os.getenv("CONN_HEALTH_CHECKS", "False").lower() in ("true", "1", "yes")
        # When health checks are enabled with PgBouncer, keep it false (extra SELECT 1 per request).
        if is_pgbouncer:
            conn_health_checks = False

        return {
            "ENGINE": engine,
            "NAME": p.path.lstrip("/"),
            "USER": urlparse.unquote(p.username) if p.username else None,
            "PASSWORD": urlparse.unquote(p.password) if p.password else None,
            "HOST": host,
            "PORT": port,
            "CONN_MAX_AGE": conn_max_age,
            "CONN_HEALTH_CHECKS": conn_health_checks,
            "DISABLE_SERVER_SIDE_CURSORS": True,
        }
    # Require a single DATABASE_URL (and optional DATABASE_REPLICA_URL) in .env
    _database_url = os.getenv("DATABASE_URL")
    if not _database_url:
        raise ImproperlyConfigured("DATABASE_URL must be set in the environment or provided via settings_local.py")

    if os.getenv("DB_REPLICA_HOST") == "True" and os.getenv("DATABASE_REPLICA_URL"):
        DATABASE_ROUTERS = ["mybustimes.db_router.PrimaryReplicaRouter"]
        DATABASES = {
            "default": _parse_database_url(_database_url),
            "replica": _parse_database_url(os.getenv("DATABASE_REPLICA_URL")),
        }
    else:
        DATABASES = {"default": _parse_database_url(_database_url)}

    for db_alias in DATABASES:
        db = DATABASES[db_alias]
        engine = db.get("ENGINE", "")
        host = (db.get("HOST") or "").lower()
        port = db.get("PORT")
        # Only set the statement_timeout startup option for real Postgres
        # servers. pgbouncer rejects startup parameters like this, so
        # skip adding it when the host looks like pgbouncer.
        if engine.startswith("django.db.backends.postgresql") and not SKIP_DB_STATEMENT_TIMEOUT:
            if not _is_pgbouncer_target(host, port):
                opts = db.get("OPTIONS", {})
                opts.update({"options": "-c statement_timeout=30000"})
                db["OPTIONS"] = opts

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
    'main.backends.CustomOIDCAuthenticationBackend',
    'mybustimes.auth_backends.PHPFallbackBackend',
    'django.contrib.auth.backends.ModelBackend',  # fallback to default just in case
]

OIDC_RP_CLIENT_ID = os.environ["OIDC_RP_CLIENT_ID"]
OIDC_RP_CLIENT_SECRET = os.environ["OIDC_RP_CLIENT_SECRET"]
OIDC_OP_AUTHORIZATION_ENDPOINT = "https://secure.mybustimes.cc/authorize"
OIDC_OP_TOKEN_ENDPOINT = "https://secure.mybustimes.cc/api/oidc/token"
OIDC_OP_USER_ENDPOINT = "https://secure.mybustimes.cc/api/oidc/userinfo"
OIDC_OP_JWKS_ENDPOINT = "https://secure.mybustimes.cc/.well-known/jwks.json"
OIDC_OP_ISSUER = "https://secure.mybustimes.cc"
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_SCOPES = "openid email profile"
OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"  # important if not already set
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"  
LOGIN_URL = 'two_factor:login'
LOGIN_REDIRECT_URL = '/'

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
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

SKIP_CAPTCHA = os.getenv("SKIP_CAPTCHA", "False").lower() in ("true", "1", "yes")
DISABLE_JESS = os.getenv("DISABLE_JESS", "False").lower() in ("true", "1", "yes")
DISABLED_ADMIN_2FA_REQUIRED = os.getenv("DISABLED_ADMIN_2FA_REQUIRED", "False").lower() in ("true", "1", "yes")

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
    
AWS_S3_CUSTOM_DOMAIN = "cdn.nextstoplabs.org"
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_S3_REGION_NAME = "garage"

AWS_S3_FILE_OVERWRITE = False
AWS_DEFAULT_ACL = None

AWS_S3_CONFIG = {
    "addressing_style": "path",
    "signature_version": "s3v4",
}

AWS_LOCATION = "mybustimes/staticfiles"
AWS_S3_CHECKSUM = False
AWS_S3_USE_THREADS = False
AWS_S3_CHECKSUM = False

AWS_S3_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=1024 * 1024 * 500,  # 500 MB
    multipart_chunksize=1024 * 1024 * 500,
    max_concurrency=1,
    use_threads=False,
)

if DEBUG:
    # Local file storage so {% static %}/media don't hit the S3/CDN in dev
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
    STATIC_URL = "/static/"
    MEDIA_URL = "/media/"
else:
    STORAGES = {
        "default": {
            "BACKEND": "mybustimes.storages.MediaStorage",
        },
        "staticfiles": {
            "BACKEND": "mybustimes.storages.StaticStorage",
        },
    }
    STATIC_URL = "https://cdn.nextstoplabs.org/mybustimes/mybustimes/staticfiles/"
    MEDIA_URL = "https://cdn.nextstoplabs.org/mybustimes/mybustimes/media/"

MEDIA_ROOT = BASE_DIR / "media"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

#LOGIN_URL = '/account/login/'
#LOGIN_REDIRECT_URL = '/'
#LOGOUT_REDIRECT_URL = '/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


if not DEBUG:
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/1")

    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                #"PARSER_CLASS": "redis.connection.HiredisParser",
                "CONNECTION_POOL_CLASS": "redis.BlockingConnectionPool",
                "CONNECTION_POOL_CLASS_KWARGS": {
                    "max_connections": 100,
                    "timeout": 20,
                },
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            },
            "KEY_PREFIX": "mbt",
        }
    }

    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_TASK_TRACK_STARTED = True
    CELERY_TASK_TIME_LIMIT = 300
    CELERY_TASK_SOFT_TIME_LIMIT = 240
    CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
    CELERY_WORKER_PREFETCH_MULTIPLIER = 4
    CELERY_TASK_ACKS_LATE = True
    CELERY_WORKER_MAX_MEMORY_PER_CHILD = 200000


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
        'level': 'INFO',
    },
    'loggers': {
        'memory_diagnostics': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'mozilla_django_oidc': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }

}

DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * 1024 * 1024  # 100MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 30000

OTP_ADMIN_REVERIFY_SECONDS = 900

CMS_CONFIRM_VERSION4 = True
SITE_ID = 1
CMS_TEMPLATES = (
    ("base.html", _("Standard")),
)
CMS_PERMISSION = True
X_FRAME_OPTIONS = 'SAMEORIGIN'
TEXT_INLINE_EDITING = True
DJANGOCMS_VERSIONING_ALLOW_DELETING_VERSIONS = True

# Sentry / Bugsink error tracking
SENTRY_DSN = os.getenv("SENTRY_DSN")

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
        ],
        send_default_pii=True,
        max_request_body_size="always",
        release=_get_release(),
        environment=os.getenv("SENTRY_ENVIRONMENT", "development" if DEBUG else "production"),
        traces_sample_rate=0,
        send_client_reports=False,
        auto_session_tracking=False,
    )

from . import telemetry