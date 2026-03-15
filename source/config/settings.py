import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    value = env(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    value = env(key)
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def env_list(key: str, default: list[str]) -> list[str]:
    value = env(key)
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


_load_env_file(BASE_DIR / ".env")


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-secret-key")
if not DEBUG and SECRET_KEY == "dev-secret-key":
    raise RuntimeError("Set DJANGO_SECRET_KEY in source/.env before production deploy.")

_allowed_hosts_default = [
    "127.0.0.1",
    "localhost",
    "ala-event.kz",
    "www.ala-event.kz",
    "194.32.141.184",
]
if DEBUG:
    # ngrok и другие тоннели — удобно при локальной разработке
    _allowed_hosts_default += [
        ".ngrok-free.dev",
        ".ngrok-free.app",
        ".ngrok.io",
        ".loca.lt",
    ]

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", _allowed_hosts_default)

default_csrf_trusted_origins = [
    "https://ala-event.kz",
    "https://www.ala-event.kz",
]
if DEBUG:
    default_csrf_trusted_origins.extend(
        [
            "http://127.0.0.1",
            "http://localhost",
            "http://127.0.0.1:8000",
            "http://localhost:8000",
            "https://*.ngrok-free.dev",
            "https://*.ngrok-free.app",
            "https://*.ngrok.io",
        ]
    )

CSRF_TRUSTED_ORIGINS = env_list(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    default_csrf_trusted_origins,
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rosetta",
    "accounts",
    "catalog",
    "kp",
    "crm",
    "main",
    "portfolio",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
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
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "main.context_processors.nav_services_url",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

sqlite_name = env("DJANGO_SQLITE_NAME", "db.sqlite3")
sqlite_path = Path(sqlite_name)
if not sqlite_path.is_absolute():
    sqlite_path = BASE_DIR / sqlite_path

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": sqlite_path,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOCALE_PATHS = [BASE_DIR / "locale"]
LANGUAGE_COOKIE_NAME = "django_language"
LANGUAGE_CODE = "ru"
LANGUAGES = [
    ("ru", "Russian"),
    ("kk", "Kazakh"),
    ("en", "English"),
]

TIME_ZONE = "Asia/Almaty"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

KP_PERFORMER_NAME = env("KP_PERFORMER_NAME", "ИП Ala Event")
KP_PERFORMER_PHONE = env("KP_PERFORMER_PHONE", "+77075822357")
KP_PERFORMER_EMAIL = env("KP_PERFORMER_EMAIL", "abdildaajzada@gmail.com")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("DJANGO_SESSION_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("DJANGO_CSRF_COOKIE_SECURE", not DEBUG)
SECURE_HSTS_SECONDS = env_int("DJANGO_SECURE_HSTS_SECONDS", 31536000 if not DEBUG else 0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    not DEBUG,
)
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
