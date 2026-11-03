"""Тести (pytest). БД — PostgreSQL з тими ж POSTGRES_* змінними; pytest-django створює test_<db>."""

import os

# Тестам не потрібен справжній ключ; має бути задано до імпорту base
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
# Ліміти запитів не заважають тестам; перевіряє їх фікстура throttle_rates
os.environ.setdefault("LOGIN_RATE", "10000/min")
os.environ.setdefault("PASSWORD_RESET_RATE", "10000/min")
os.environ.setdefault("AI_CHAT_RATE", "10000/min")
os.environ.setdefault("AI_CHAT_DAILY_RATE", "10000/day")

from .base import *  # noqa: E402, F403

DEBUG = False

# Швидкий хешер — суттєво пришвидшує тести з логіном/реєстрацією
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Тести не залежать від Redis; кеш очищується перед кожним тестом (conftest)
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# Slack у тестах — синхронно і без справжнього токена (мокається)
SLACK_BOT_TOKEN = ""
SLACK_ASYNC = False

# OpenAI у тестах завжди мокається
OPENAI_API_KEY = "test-key"
