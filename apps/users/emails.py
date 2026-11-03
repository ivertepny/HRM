"""Листи користувачам: запрошення і скидання пароля.

Посилання ведуть на сторінки фронту (FRONTEND_URL), а не на Django: браузер
говорить лише з Next.js. Листи — простий текст українською.
"""

import logging
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

from .tokens import encode_uid, invite_token, password_reset_token

logger = logging.getLogger(__name__)


def _link(path, user, generator):
    query = urlencode({"uid": encode_uid(user), "token": generator.make_token(user)})
    return f"{settings.FRONTEND_URL}{path}?{query}"


def _send(user, subject, template, context):
    body = render_to_string(
        f"users/emails/{template}.txt",
        {"user": user, "site_url": settings.FRONTEND_URL, **context},
    )
    send_mail(subject, body, None, [user.email])


def invite_link(user):
    return _link("/invite", user, invite_token)


def send_invite(user, invited_by=None):
    """Запрошення: посилання, щоб самому задати пароль (діє INVITE_TOKEN_SECONDS)."""
    _send(
        user,
        "Запрошення до HR-системи",
        "invite",
        {
            "link": invite_link(user),
            "days": settings.INVITE_TOKEN_SECONDS // 86400,
            "invited_by": invited_by,
        },
    )


def send_password_reset(user):
    """Посилання на новий пароль (діє PASSWORD_RESET_TOKEN_SECONDS)."""
    _send(
        user,
        "Скидання пароля",
        "password_reset",
        {
            "link": _link("/reset-password", user, password_reset_token),
            "hours": settings.PASSWORD_RESET_TOKEN_SECONDS // 3600,
        },
    )


def try_send(send, user, **kwargs):
    """Лист, збій якого не ламає запит: True — надіслано. Помилку — в лог (Sentry)."""
    try:
        send(user, **kwargs)
    except Exception:
        logger.exception("Не вдалося надіслати лист користувачу id=%s", user.pk)
        return False
    return True
