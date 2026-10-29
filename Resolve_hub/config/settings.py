"""
Django settings for Resolve_Hub (config project).
Phase 1 (DB), Phase 2 (custom user), Phase 15 (hardening) are all
driven from environment variables so the same code runs in local
dev (SQLite) and production (Supabase PostgreSQL) without changes.
"""
from pathlib import Path
import sys
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    SECURE_SSL_REDIRECT=(bool, False),
    SESSION_COOKIE_SECURE=(bool, False),
    CSRF_COOKIE_SECURE=(bool, False),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-change-me")
DEBUG = env("DJANGO_DEBUG")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["127.0.0.1", "localhost"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Local apps
    "apps.accounts",
    "apps.institutions",
    "apps.complaints",
    "apps.officer_portal",
    "apps.command_centre",
    "apps.triage",
    "apps.director_portal",
    "apps.hod_portal",
    "apps.spam_detection",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Phase 1: Database. DB_ENGINE switches between local SQLite (dev/tests) and
# Supabase-hosted PostgreSQL (staging/production). No code changes needed to
# move environments -- only .env changes.
# ---------------------------------------------------------------------------
if env("DB_ENGINE", default="sqlite") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("DB_NAME"),
            "USER": env("DB_USER"),
            "PASSWORD": env("DB_PASSWORD"),
            "HOST": env("DB_HOST"),
            "PORT": env("DB_PORT", default="5432"),
            "OPTIONS": {"sslmode": env("DB_SSLMODE", default="require")},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Phase 2: custom user model, set before first migration.
AUTH_USER_MODEL = "accounts.User"

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:post_login_redirect"
LOGOUT_REDIRECT_URL = "accounts:login"

LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("en", "English"),
    ("hi", "हिन्दी"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

# SLA and AI Triage settings
DEFAULT_SLA_HOURS = env.int("DEFAULT_SLA_HOURS", default=168)
TRIAGE_CONFIDENCE_THRESHOLD = env.float("TRIAGE_CONFIDENCE_THRESHOLD", default=0.45)
DUPLICATE_LINK_THRESHOLD = env.float("DUPLICATE_LINK_THRESHOLD", default=0.80)

# Optional IMAP ingestion
IMAP_HOST = env("IMAP_HOST", default="")
IMAP_USER = env("IMAP_USER", default="")
IMAP_PASSWORD = env("IMAP_PASSWORD", default="")
IMAP_FOLDER = env("IMAP_FOLDER", default="INBOX")

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Phase 9: Supabase Storage (private bucket). Backend-only credentials --
# never referenced from templates/JS. Local dev falls back to filesystem
# storage under media/ when SUPABASE_URL isn't set, so the app stays runnable
# without live Supabase network access.
# ---------------------------------------------------------------------------
SUPABASE_URL = env("SUPABASE_URL", default="")
SUPABASE_SERVICE_ROLE_KEY = env("SUPABASE_SERVICE_ROLE_KEY", default="")
SUPABASE_STORAGE_BUCKET = env("SUPABASE_STORAGE_BUCKET", default="complaint-attachments")
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

MAX_ATTACHMENT_SIZE_MB = env.int("MAX_ATTACHMENT_SIZE_MB", default=8)
ALLOWED_ATTACHMENT_TYPES = env.list(
    "ALLOWED_ATTACHMENT_TYPES", default=["application/pdf", "image/png", "image/jpeg"]
)

# Phase 6: spam engine rate-limit config.
SPAM_SUBMISSIONS_PER_HOUR = env.int("SPAM_SUBMISSIONS_PER_HOUR", default=3)
SPAM_SUBMISSIONS_PER_DAY = env.int("SPAM_SUBMISSIONS_PER_DAY", default=8)

# ---------------------------------------------------------------------------
# Phase 13: Student OTP - used both at login and to verify a new account at
# registration (see apps/accounts/otp.py).
#
# Email: console backend by default, which prints the message to the
# terminal running runserver, so the whole flow works out of the box with
# zero third-party setup. Set EMAIL_BACKEND to
# django.core.mail.backends.smtp.EmailBackend plus the EMAIL_HOST_* vars for
# real delivery (e.g. a Gmail App Password).
#
# SMS: optional, via Twilio. Leave the TWILIO_* vars blank and the SMS
# option simply never appears; fill in all three and it turns on
# automatically - there's no separate on/off flag to forget to flip.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@resolvehub.local")

TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_FROM_NUMBER = env("TWILIO_FROM_NUMBER", default="")
SMS_OTP_ENABLED = bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and TWILIO_FROM_NUMBER)

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = env.int("OTP_EXPIRY_MINUTES", default=5)
OTP_MAX_ATTEMPTS = env.int("OTP_MAX_ATTEMPTS", default=5)
OTP_RESEND_COOLDOWN_SECONDS = env.int("OTP_RESEND_COOLDOWN_SECONDS", default=30)

# How long an unverified registration survives before a fresh signup may
# take over its email/roll number (see StudentRegistrationForm).
REGISTRATION_UNVERIFIED_TTL_HOURS = env.int("REGISTRATION_UNVERIFIED_TTL_HOURS", default=24)

# ---------------------------------------------------------------------------
# Phase 15: production hardening. All default to safe-for-local-dev values;
# flip to True via .env only when served over HTTPS.
# ---------------------------------------------------------------------------
SECURE_SSL_REDIRECT = env("SECURE_SSL_REDIRECT")
SESSION_COOKIE_SECURE = env("SESSION_COOKIE_SECURE")
CSRF_COOKIE_SECURE = env("CSRF_COOKIE_SECURE")
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django needs JS-readable CSRF cookie for the vanilla-JS fetch calls
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Google Gemini AI Configuration & Model Fallback Chain
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_PRIMARY_MODEL = env("GEMINI_PRIMARY_MODEL", default="gemini-2.5-flash")
GEMINI_FALLBACK_MODELS = env.list("GEMINI_FALLBACK_MODELS", default=["gemini-2.5-flash-lite", "gemini-1.5-flash"])

# Never log PII, complaint contents, passwords, OTPs, or credentials.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
