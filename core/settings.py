from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(encoding="utf-8")


def csv_env(name, default=""):
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


SECRET_KEY = os.getenv("SECRET_KEY", "dev-insecure-key")
DEBUG = int(os.getenv("DEBUG", 1))

# Backend public host including scheme for CSRF (e.g., https://apiewa.divspan.uz)
BACKEND_ORIGIN = os.getenv("BACKEND_ORIGIN", "http://127.0.0.1:8000")

# Comma-separated list of frontend origins (schemes required)
CORS_ALLOWED_ORIGINS = csv_env("CORS_ALLOWED_ORIGINS", "http://localhost:3000")

# Hosts without scheme
ALLOWED_HOSTS = csv_env("ALLOWED_HOSTS", "127.0.0.1,localhost")

CSRF_TRUSTED_ORIGINS = csv_env(
    "CSRF_TRUSTED_ORIGINS", BACKEND_ORIGIN  # ensure this includes scheme
)

CORS_ALLOW_CREDENTIALS = True

DEFAULT_APPS = [
    "daphne",
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]


THIRD_PART_APPS = [
    "rest_framework",
    "nested_inline",
    "channels",
]

MY_APPS = ["telegram", "rag_system", "telegram_client", "miniapp"]


INSTALLED_APPS = DEFAULT_APPS + THIRD_PART_APPS + MY_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

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

# WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"


# Asgi settings

REDIS_HOST = os.getenv("REDIS_HOST", "redis")  # docker service name
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [(REDIS_HOST, REDIS_PORT)]},
    }
}


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST", "db"),  # docker service name
        # "HOST": "localhost",
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Ensure logs/ exists
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d %(message)s"
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
        "rotating_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.rot.log"),
            "maxBytes": 5_000_000,
            "backupCount": 5,
            "formatter": "standard",
        },
    },
    "root": {"handlers": ["console", "rotating_file"], "level": "INFO"},
}

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_HOST = os.getenv("BOT_HOST", BACKEND_ORIGIN)  # e.g., https://apiewa.divspan.uz
BOT_WEBHOOK_URL = f"{BOT_HOST}/telegram/webhook/{BOT_TOKEN.split(':', 1)[0]}/updates/"

# GPT config
GPT_TOKEN = os.getenv("gpt_token", "")


# celery settings
# Broker/backend
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/1"

# Serialization
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Performance / robustness
CELERY_TASK_ACKS_LATE = True  # re-queue if worker dies mid-task
CELERY_WORKER_PREFETCH_MULTIPLIER = 1  # fairer distribution, lower latency
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_TASK_TIME_LIMIT = 120  # hard kill runaway tasks
CELERY_TASK_SOFT_TIME_LIMIT = 110
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000  # curb leaks
CELERY_WORKER_DISABLE_RATE_LIMITS = True  # minor overhead reduction

# Results: avoid writing unless you need them
CELERY_TASK_IGNORE_RESULT = True  # global default; override per-task if needed
CELERY_RESULT_EXPIRES = 3600  # 1h if you do keep results

# Routing & queues
CELERY_TASK_QUEUES = {
    "default": {},
    "fast": {},
    "slow": {},
}

CELERY_TASK_ROUTES = {
    # Quick, latency-sensitive jobs
    "rag_system.tasks.answer_question": {"queue": "fast"},
}
