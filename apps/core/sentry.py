"""Звіти про помилки в Sentry (лише prod і лише з SENTRY_DSN).

У HR-системі персональні дані майже в кожному запиті: зарплати, документи,
табель, повідомлення AI-асистенту. Тому в Sentry не йдуть ні тіла запитів, ні
локальні змінні, ні дані користувача (email, IP) — лише тип помилки, стек,
URL і метод. Цього досить, щоб знайти баг, і нічого не витікає третій стороні.
"""

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration


def configure_sentry(dsn, environment="production", release=None):
    """Без dsn нічого не робить — Sentry вимкнений чисто, а не наполовину."""
    if not dsn:
        return False
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release or None,
        integrations=[DjangoIntegration()],
        send_default_pii=False,
        max_request_body_size="never",
        include_local_variables=False,
        # Лише помилки, без трасування продуктивності
        traces_sample_rate=0,
    )
    return True
