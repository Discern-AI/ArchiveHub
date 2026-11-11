"""ArchiveHub settings. All environment-specific values come from env vars or a local .env."""

import sys
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent.parent

env = environ.Env()
for candidate in (BASE_DIR / ".env", REPO_ROOT / ".env"):
    if candidate.exists():
        env.read_env(candidate)
        break

TESTING = "pytest" in sys.modules
DEBUG = env.bool("DJANGO_DEBUG", default=False)
SECRET_KEY = env("DJANGO_SECRET_KEY", default="") or (
    "dev-only-insecure-key" if DEBUG or TESTING else ""
)
if not SECRET_KEY:
    raise RuntimeError("Set DJANGO_SECRET_KEY (or DJANGO_DEBUG=true for local development).")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list(
    "DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173", "http://127.0.0.1:5173"]
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "allauth",
    "allauth.account",
    "allauth.headless",
    "core",
    "accounts",
    "projects",
    "history",
    "connectors",
    "explorer",
    "archive",
    "genealogy",
    "assistant",
    "interviews",
    "timemap",
    "lineages",
    "culture",
    "publishing",
    "search",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "archivehub.urls"
ASGI_APPLICATION = "archivehub.asgi.application"
WSGI_APPLICATION = "archivehub.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# SQLite by default so the project runs with no setup; set DATABASE_URL for Postgres.
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# allauth: headless (API-only) mode for the React app, email login, no usernames.
HEADLESS_ONLY = True
HEADLESS_CLIENTS = ("browser",)
HEADLESS_FRONTEND_URLS = {
    "account_confirm_email": "/account/verify-email/{key}",
    "account_reset_password_from_key": "/account/password/reset/{key}",
    "account_signup": "/account/signup",
}
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="none")
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "Europe/London"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# The Archive. Local files in development; R2 via django-storages in production.
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "var" / "media"))
MEDIA_URL = "/media-not-served/"  # originals are only ever served through permission checks
ARCHIVE_MAX_UPLOAD_MB = env.int("ARCHIVE_MAX_UPLOAD_MB", default=50)
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
# Background jobs: "thread" (local, no Redis), "sync" (tests), "rq" (production, Redis).
JOBS_BACKEND = env("JOBS_BACKEND", default="thread")
HANDWRITING_CREDITS_PER_PAGE = env.int("HANDWRITING_CREDITS_PER_PAGE", default=2)
OCR_CREDITS_PER_PAGE = env.int("OCR_CREDITS_PER_PAGE", default=1)

# Assistant (see assistant/providers.py). "fake" needs no API key and is used in tests.
ASSISTANT_PROVIDER = env("ASSISTANT_PROVIDER", default="anthropic")
ANTHROPIC_MODEL = env("ANTHROPIC_MODEL", default="claude-opus-5-5")
ANTHROPIC_EFFORT = env("ANTHROPIC_EFFORT", default="medium")
ANTHROPIC_MAX_TOKENS = env.int("ANTHROPIC_MAX_TOKENS", default=64000)
# Seconds between words from the fake provider, to see streaming work offline.
ASSISTANT_FAKE_DELAY = env.float("ASSISTANT_FAKE_DELAY", default=0.0)

# Live interviews (WP5, ADR-028). "whisper" runs faster-whisper on this server
# (pip install -r requirements-speech.txt); "fake" needs nothing and is used in tests.
SPEECH_PROVIDER = env("SPEECH_PROVIDER", default="whisper")
SPEECH_MODEL = env("SPEECH_MODEL", default="small.en")  # finished lines
SPEECH_LIVE_MODEL = env("SPEECH_LIVE_MODEL", default="base.en")  # provisional live words
SPEECH_DEVICE = env("SPEECH_DEVICE", default="cpu")
SPEECH_COMPUTE_TYPE = env("SPEECH_COMPUTE_TYPE", default="int8")
INTERVIEW_MODEL = env("INTERVIEW_MODEL", default=ANTHROPIC_MODEL)
INTERVIEW_MAX_MINUTES = env.int("INTERVIEW_MAX_MINUTES", default=120)

# Time map (WP6, ADR-031). The modern map is OpenFreeMap (no key). Historic OS maps from
# the National Library of Scotland come through MapTiler and need a key; MapTiler keys
# are sent to the browser by design, so restrict yours to your own sites in MapTiler.
MAP_STYLE_URL = env("MAP_STYLE_URL", default="https://tiles.openfreemap.org/styles/liberty")
MAPTILER_KEY = env("MAPTILER_KEY", default="")

# Live sources that need a key or registered access (ADR-034). Each stays listed as
# "not set up on this server yet" until its key is set. Never commit real keys.
EUROPEANA_API_KEY = env("EUROPEANA_API_KEY", default="")
TROVE_API_KEY = env("TROVE_API_KEY", default="")
DIGITALNZ_API_KEY = env("DIGITALNZ_API_KEY", default="")
DPLA_API_KEY = env("DPLA_API_KEY", default="")
GEOGRAPH_API_KEY = env("GEOGRAPH_API_KEY", default="")
OS_DATA_HUB_KEY = env("OS_DATA_HUB_KEY", default="")
GEONAMES_USERNAME = env("GEONAMES_USERNAME", default="")
# Optional: OpenAlex works without a key, but a free key raises the shared daily budget.
OPENALEX_API_KEY = env("OPENALEX_API_KEY", default="")
# The National Archives registers access by the server's IP address, not by key.
TNA_DISCOVERY_ENABLED = env.bool("TNA_DISCOVERY_ENABLED", default=False)

SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk

    sentry_sdk.init(dsn=SENTRY_DSN, send_default_pii=False, traces_sample_rate=0.0)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
