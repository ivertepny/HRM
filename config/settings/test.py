"""Тести (pytest). БД — PostgreSQL з тими ж POSTGRES_* змінними; pytest-django створює test_<db>."""

import os

# Тестам не потрібен справжній ключ; має бути задано до імпорту base
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from .base import *  # noqa: E402, F403

DEBUG = False

# Швидкий хешер — суттєво пришвидшує тести з логіном/реєстрацією
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# OpenAI у тестах завжди мокається
OPENAI_API_KEY = "test-key"
