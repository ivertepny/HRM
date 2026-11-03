"""Щоденні нагадування в Slack (запускає cron: manage.py slack_reminders).

Кожне нагадування — не частіше разу на день для людини: повторний запуск
cron того ж дня нічого не дублює (позначка в кеші до кінця доби).
"""

from django.core.cache import cache
from django.db.models import Q
from django.utils import timezone

from apps.access.services import UserAccess, scope_for_access, users_with_permission
from apps.attendance.models import AttendanceRecord, Holiday
from apps.employees.models import Employee
from apps.vacations.models import VacationRequest

from . import client
from .notify import link


def _once_today(kind, user_id, today):
    """True лише для першого виклику за добу (cache.add атомарний)."""
    return cache.add(f"slack:reminder:{kind}:{today:%Y-%m-%d}:{user_id}", 1, 86400)


def is_working_day(day):
    return day.weekday() < 5 and not Holiday.objects.filter(date=day).exists()


def attendance_recipients(today):
    """Працівники, що мали б сьогодні відмітитись, але ще ні: працюють (прийняті
    і не звільнені), не у схваленій відпустці, без відмітки за сьогодні."""
    on_vacation = VacationRequest.objects.filter(
        status=VacationRequest.Status.APPROVED,
        date_start__lte=today,
        date_end__gte=today,
    ).values("employee_id")
    marked = AttendanceRecord.objects.filter(date=today).values("employee_id")
    return (
        Employee.objects.filter(user__is_active=True)
        .filter(Q(date_hired__isnull=True) | Q(date_hired__lte=today))
        .filter(Q(date_fired__isnull=True) | Q(date_fired__gte=today))
        .exclude(pk__in=on_vacation)
        .exclude(pk__in=marked)
        .select_related("user")
    )


def remind_attendance(today=None):
    today = today or timezone.localdate()
    if not is_working_day(today):
        return 0
    sent = 0
    for employee in attendance_recipients(today):
        if not _once_today("attendance", employee.user_id, today):
            continue
        text = (
            "Ви ще не відмітились у табелі сьогодні. "
            f"{link('/attendance', 'Відмітитись')}"
        )
        sent += client.send_dm(employee.user.email, text)
    return sent


def pending_for(user):
    """Заявки на розгляді, які людина може розглянути (без власних)."""
    return scope_for_access(
        UserAccess(user),
        VacationRequest.objects.filter(status=VacationRequest.Status.PENDING),
        "vacations:manage",
        unit_field="employee__structural_unit",
    ).exclude(employee__user=user)


def remind_pending_vacations(today=None):
    today = today or timezone.localdate()
    sent = 0
    for user in users_with_permission("vacations:manage", anywhere=True):
        count = pending_for(user).count()
        if not count or not _once_today("vacations", user.pk, today):
            continue
        text = (
            f"На розгляді заявок на відпустку: *{count}*. "
            f"{link('/vacations/review', 'Розглянути')}"
        )
        sent += client.send_dm(user.email, text)
    return sent
