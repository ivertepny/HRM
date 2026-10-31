"""Продакшн. ALLOWED_HOSTS обов'язковий; очікується HTTPS за reverse proxy (Nginx)."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import STORAGES, env

DEBUG = False
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Файли працівників — у приватному S3-бакеті, доступ лише через підписані URL.
# Облікові дані boto3 бере з IAM-ролі (instance profile / ECS task role / IRSA).
# Статичні ключі заборонені: якщо вони є в оточенні, boto3 віддав би їм
# пріоритет над роллю — тому падаємо при старті.
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

STORAGES["default"] = {
    "BACKEND": "storages.backends.s3.S3Storage",
    "OPTIONS": {
        "bucket_name": env("AWS_STORAGE_BUCKET_NAME"),
        "region_name": env("AWS_S3_REGION_NAME"),
        "file_overwrite": False,
        "querystring_auth": True,
        "querystring_expire": 3600,
    },
}
