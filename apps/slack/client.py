"""Особисті повідомлення в Slack від імені бота (Slack Web API).

Людину в Slack знаходимо за робочим email (users.lookupByEmail), тож окремо
нічого зв'язувати не треба. Без SLACK_BOT_TOKEN модуль нічого не робить.

Потрібні scopes бота: chat:write, users:read, users:read.email.
Лише вихідні запити: Slack до нашого сервера не звертається.
"""

import logging

import httpx
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

API = "https://slack.com/api/"
# Slack ID людини змінюється рідко; «не знайдено» — перевіряємо частіше:
# людину могли щойно додати у workspace
FOUND_TTL = 24 * 3600
NOT_FOUND_TTL = 3600


class SlackError(Exception):
    """Slack відповів ok=false (напр. ratelimited, invalid_auth)."""


def enabled():
    return bool(settings.SLACK_BOT_TOKEN)


def _call(method, *, json=None, data=None):
    response = httpx.post(
        API + method,
        headers={"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"},
        json=json,
        data=data,
        timeout=settings.SLACK_TIMEOUT,
    )
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        raise SlackError(body.get("error", "unknown_error"))
    return body


def user_id_for(email):
    """Slack ID за email або None, якщо такої людини у workspace немає."""
    key = f"slack:uid:{email.strip().lower()}"
    cached = cache.get(key)
    if cached is not None:
        return cached or None
    try:
        body = _call("users.lookupByEmail", data={"email": email})
    except SlackError as exc:
        if str(exc) != "users_not_found":
            raise
        cache.set(key, "", NOT_FOUND_TTL)
        return None
    user_id = body["user"]["id"]
    cache.set(key, user_id, FOUND_TTL)
    return user_id


def send_dm(email, text):
    """Повідомлення людині. True — надіслано; збій лише пишеться в лог:
    сповіщення не повинні ламати кадрові дії."""
    if not enabled():
        return False
    try:
        user_id = user_id_for(email)
        if user_id is None:
            return False
        _call(
            "chat.postMessage",
            json={"channel": user_id, "text": text, "unfurl_links": False},
        )
    except httpx.HTTPError, SlackError, KeyError, ValueError:
        logger.warning("Slack: не вдалося надіслати повідомлення", exc_info=True)
        return False
    return True
