"""Продакшн (docker-compose.server.yml на VPS).

Django в інтернет не виходить: браузер говорить лише з Next.js (BFF), а той —
з Django всередині мережі compose (http://api:8000). TLS завершує nginx хоста.
"""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import env

DEBUG = False
# Ім'я сервісу в compose ("api"): домен до Django не доходить
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

# nginx хоста ставить X-Forwarded-Proto, Next пересилає його далі
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Те саме значення, що в nginx/nginx.conf (саме звідти заголовок іде в браузер).
# Почати з 3600; коли HTTPS кілька днів працює — 31536000.
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

SILENCED_SYSTEM_CHECKS = [
    # SECURE_SSL_REDIRECT: HTTPS форсує nginx хоста; Next і healthcheck ходять
    # у Django по http усередині мережі compose — редирект їх зламав би.
    "security.W008",
    # HSTS preload — фактично незворотне рішення для домену; не за замовчуванням
    "security.W021",
]

# Файли працівників — FileSystemStorage з base.py, у volume `media`.
# Віддає їх MediaView з перевіркою доступу (через Next, не напряму).

# Статичні AWS-ключі заборонені (лише IAM-ролі). На Hetzner AWS не
# використовується, тож їх тут не має бути взагалі — падаємо при старті.
_static_aws_keys = [
    name
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
    if os.environ.get(name)
]
if _static_aws_keys:
    raise ImproperlyConfigured(
        f"Статичні AWS-ключі заборонені ({', '.join(_static_aws_keys)}); "
        "використовуйте IAM-роль."
    )

# Логи — у stdout контейнера (docker logs); без цього помилки 500 зникали б
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
