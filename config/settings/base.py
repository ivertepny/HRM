"""Спільні налаштування для всіх оточень. Оточення-специфічне — у dev.py / prod.py."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()
# Змінні оточення процесу мають пріоритет над .env (не перезаписуються)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])

# Application definition

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.admin",
    "django.contrib.postgres",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",
    "mptt",
    "simple_history",
    # my apps
    "apps.core",
    "apps.users",
    "apps.employees",
    "apps.company",
    "apps.ai_assistant",
    "apps.access",
    "apps.vacations",
    "apps.equipment",
    "apps.attendance",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Записує автора змін у HistoricalRecords (DRF прокидає JWT-юзера в request)
    "simple_history.middleware.HistoryRequestMiddleware",
]

# Origins фронтенду (React / Flutter Web), через кому
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        # Локально — localhost; у docker-compose перевизначається на "db"
        "HOST": env("POSTGRES_HOST", default="localhost"),
        "PORT": env("POSTGRES_PORT", default="5432"),
        # psycopg3 без таймауту може довго чекати на недоступний хост
        "OPTIONS": {"connect_timeout": env.int("POSTGRES_CONNECT_TIMEOUT", default=5)},
    },
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "uk"

# «Сьогодні» для відпусток і табеля рахується в часовому поясі компанії
TIME_ZONE = env("TIME_ZONE", default="Europe/Kyiv")

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Завантажені файли (фото, документи працівників). У prod — S3, див. prod.py
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
MAX_UPLOAD_SIZE_MB = 10

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# Cache: Redis, якщо задано REDIS_URL; інакше — пам'ять процесу (локальна розробка)
REDIS_URL = env("REDIS_URL", default="")
CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "hrm",
            "TIMEOUT": 300,
        }
        if REDIS_URL
        else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    )
}
# Скільки секунд тримати в кеші обчислені права користувача
ACCESS_CACHE_TIMEOUT = 300

# Пошта. У dev листи друкуються в консоль; у prod — SMTP (prod.py).
# Підійде будь-який SMTP-провайдер: Brevo, Mailgun, Postmark, Resend тощо.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_TIMEOUT = 10  # секунд: недоступний SMTP не вішає запит
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="HRM <noreply@localhost>")
# Для filebased-бекенду (e2e-стенд читає з файлів посилання з листів)
EMAIL_FILE_PATH = env("EMAIL_FILE_PATH", default=None)

# Адреса веб-клієнта — для посилань у листах (без "/" в кінці)
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000").rstrip("/")

# Скільки діють посилання з листів (apps/users/tokens.py)
PASSWORD_RESET_TOKEN_SECONDS = 2 * 3600
INVITE_TOKEN_SECONDS = env.int("INVITE_DAYS", default=7) * 86400
# Глобальний ліміт Django — найдовший з термінів; коротші перевіряє tokens.py
PASSWORD_RESET_TIMEOUT = max(PASSWORD_RESET_TOKEN_SECONDS, INVITE_TOKEN_SECONDS)

# Скільки днів назад працівник може виправляти свій табель
ATTENDANCE_EDIT_DAYS = env.int("ATTENDANCE_EDIT_DAYS", default=7)

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.DefaultPagination",
    "EXCEPTION_HANDLER": "apps.core.exceptions.exception_handler",
    # Ліміти (apps/core/throttling.py); за адресою клієнта обмежує nginx
    "DEFAULT_THROTTLE_CLASSES": ["apps.core.throttling.AuthenticatedUserThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "user": "600/min",  # з запасом для пошуку під час набору і дашбордів
        # На один email; вдалі спроби теж рахуються
        "login": env("LOGIN_RATE", default="10/hour"),
        # Листів зі скиданням пароля на одну адресу
        "password_reset": env("PASSWORD_RESET_RATE", default="5/hour"),
        "ai_chat": env("AI_CHAT_RATE", default="10/min"),
        "ai_chat_daily": env("AI_CHAT_DAILY_RATE", default="200/day"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "HRM API",
    "DESCRIPTION": "HR Management System",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_SETTINGS": {
        "filter": True,
        "persistAuthorization": True,
    },
    "COMPONENT_SPLIT_REQUEST": True,
    "COMPONENT_NO_READ_ONLY_REQUIRED": True,
    "SCHEMA_COERCE_PATH_PK": True,
    "SCHEMA_PATH_PREFIX": r"/api/",
    "ENUM_NAME_OVERRIDES": {
        # Поле status є в кількох моделях — даємо enum-ам стабільні назви
        "UserStatusEnum": "apps.users.models.User.STATUS_CHOICES",
        "VacationStatusEnum": "apps.vacations.models.VacationRequest.Status",
        "EquipmentStateEnum": "apps.equipment.models.Equipment.State",
        "EquipmentCategoryEnum": "apps.equipment.models.Equipment.Category",
        "AttendanceStatusEnum": "apps.attendance.models.AttendanceRecord.Status",
        "CustomTypeEnum": [
            ("OFFICE", "Центральний офіс"),
            ("DEPARTMENT", "Департамент"),
        ],
    },
}

# Custom user model
AUTH_USER_MODEL = "users.User"
SITE_ID = 1

CSRF_COOKIE_HTTPONLY = True

# Тільки відмінні від дефолтів simplejwt значення
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Для генерації графів (Linux)
GRAPHVIZ_BIN = "/usr/bin/dot"

# Максимальна глибина ієрархії підрозділів
MAX_STRUCTURAL_UNIT_DEPTH = 1000

# AI асистент
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
MODEL_NAME_AI = "gpt-4o-mini"  # Назва моделі OpenAI
MAX_TOKENS_INPUT_AI = 1000  # Ліміт токенів у повідомленні користувача
MAX_TOKENS_OUTPUT_AI = 1000  # Ліміт токенів у відповіді моделі
MAX_HISTORY_AI = 20  # Скільки останніх обмінів сесії передавати моделі
OPENAI_TIMEOUT_AI = 30  # Секунд на запит до OpenAI
AI_RECURSION_LIMIT = (
    8  # Макс. кроків графа агента (захист від зациклення на інструментах)
)
