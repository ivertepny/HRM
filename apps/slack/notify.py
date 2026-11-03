"""Події системи → особисті повідомлення в Slack.

Отримувачів і тексти рахуємо одразу (тут є БД і транзакція), а самі HTTP-
запити до Slack — після коміту, у фоновому потоці: відповідь користувачу не
чекає на Slack, а відкат транзакції не надсилає повідомлення про те, чого не
сталося. Доставка best-effort: перезапуск процесу може загубити повідомлення.

У повідомлення не потрапляють коментарі й інші вільні тексти — лише хто, що і
коли, плюс посилання на застосунок (Slack — стороння служба).
"""

from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.db import transaction

from apps.access.services import users_with_permission

from . import client

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="slack")


def escape(text):
    """Спецсимволи розмітки Slack (mrkdwn) у даних користувачів."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def link(path, label):
    return f"<{settings.FRONTEND_URL}{path}|{escape(label)}>"


def _deliver(messages):
    for email, text in messages:
        client.send_dm(email, text)


def send(messages):
    """[(email, text), …] — після коміту поточної транзакції."""
    messages = [(email, text) for email, text in messages if email]
    if not messages or not client.enabled():
        return

    def deliver():
        if settings.SLACK_ASYNC:
            _executor.submit(_deliver, messages)
        else:
            _deliver(messages)

    transaction.on_commit(deliver)


# --- відпустки -------------------------------------------------------------------


def _period(vacation):
    if vacation.date_start == vacation.date_end:
        return f"{vacation.date_start:%d.%m.%Y}"
    return f"{vacation.date_start:%d.%m} – {vacation.date_end:%d.%m.%Y}"


def _summary(vacation):
    days = vacation.days
    return (
        f"{escape(vacation.get_vacation_type_display().lower())}, "
        f"{_period(vacation)} ({days} дн.)"
    )


def vacation_submitted(vacation, by):
    """Нова заявка: тим, хто може її розглянути (крім самого працівника);
    працівнику — якщо заявку за нього подав HR."""
    employee = vacation.employee
    approvers = users_with_permission(
        "vacations:manage", employee.structural_unit
    ).exclude(pk=employee.user_id)
    text = (
        f"Нова заявка на розгляд: *{escape(employee)}* — {_summary(vacation)}. "
        f"{link('/vacations/review', 'Розглянути')}"
    )
    messages = [(user.email, text) for user in approvers if user.pk != by.pk]
    if by.pk != employee.user_id:
        messages.append(
            (
                employee.user.email,
                f"HR оформив(-ла) для вас: {_summary(vacation)}. "
                f"{link('/vacations', 'Мої відпустки')}",
            )
        )
    send(messages)


def vacation_decided(vacation):
    verdict = (
        "схвалено ✅" if vacation.status == vacation.Status.APPROVED else "відхилено"
    )
    send(
        [
            (
                vacation.employee.user.email,
                f"Вашу заявку {verdict}: {_summary(vacation)}. "
                f"{link('/vacations', 'Подробиці')}",
            )
        ]
    )


def vacation_cancelled(vacation, by):
    """Працівнику — лише якщо скасував хтось інший (своє скасування він бачить)."""
    if by.pk == vacation.employee.user_id:
        return
    send(
        [
            (
                vacation.employee.user.email,
                f"Вашу заявку скасовано: {_summary(vacation)}. "
                f"{link('/vacations', 'Мої відпустки')}",
            )
        ]
    )


# --- облікові записи -----------------------------------------------------------------


def invite(user, invite_url):
    """Дубль листа-запрошення, якщо людина вже є у Slack-workspace."""
    send(
        [
            (
                user.email,
                "Для вас створено обліковий запис у HR-системі. "
                f"Задайте пароль: <{invite_url}|прийняти запрошення> "
                f"(посилання діє {settings.INVITE_TOKEN_SECONDS // 86400} дн.).",
            )
        ]
    )
