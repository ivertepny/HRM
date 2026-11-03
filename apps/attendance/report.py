"""Місячний звіт табеля: по працівнику — дні за статусами, відпустка, пропуски, години.

Робочі дні — понеділок…п'ятниця, крім святкових днів компанії (Holiday).
"""

import calendar
import datetime
from collections import defaultdict

from django.db.models import Q
from django.utils import timezone

from apps.vacations.models import VacationRequest

from .models import AttendanceRecord, Holiday


def parse_month(value):
    """«2026-11» → date(2026, 11, 1); без значення — поточний місяць."""
    if not value:
        return timezone.localdate().replace(day=1)
    return datetime.datetime.strptime(value, "%Y-%m").date()


def month_bounds(first):
    last_day = calendar.monthrange(first.year, first.month)[1]
    return first, first.replace(day=last_day)


def weekdays(start, end, holidays=frozenset()):
    """Робочі дні періоду: пн–пт, крім святкових."""
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in holidays:
            yield day
        day += datetime.timedelta(days=1)


def employees_in_month(queryset, first, last):
    return queryset.filter(
        Q(date_hired__isnull=True) | Q(date_hired__lte=last),
        Q(date_fired__isnull=True) | Q(date_fired__gte=first),
    )


def build_report(employees, first, today=None):
    today = today or timezone.localdate()
    first, last = month_bounds(first)
    employees = list(employees.select_related("user", "structural_unit"))
    ids = [e.pk for e in employees]
    month_holidays = list(Holiday.objects.filter(date__range=(first, last)))
    holidays = frozenset(h.date for h in month_holidays)

    records = defaultdict(list)
    for record in AttendanceRecord.objects.filter(
        employee_id__in=ids, date__range=(first, last)
    ):
        records[record.employee_id].append(record)

    vacation_days = defaultdict(set)
    for vacation in VacationRequest.objects.filter(
        employee_id__in=ids,
        status=VacationRequest.Status.APPROVED,
        date_start__lte=last,
        date_end__gte=first,
    ):
        start, end = max(vacation.date_start, first), min(vacation.date_end, last)
        vacation_days[vacation.employee_id].update(weekdays(start, end, holidays))

    rows = []
    for employee in employees:
        own = records[employee.pk]
        marked = {r.date for r in own}
        on_vacation = vacation_days[employee.pk]
        # Пропуски рахуємо лише в межах роботи і не далі сьогодні
        span_start = max(first, employee.date_hired or first)
        span_end = min(last, today, employee.date_fired or last)
        missing = sum(
            1
            for day in weekdays(span_start, span_end, holidays)
            if day not in marked and day not in on_vacation
        )
        by_status = defaultdict(int)
        for record in own:
            by_status[record.status] += 1
        rows.append(
            {
                "employee": employee,
                "unit": employee.structural_unit.name,
                "office": by_status[AttendanceRecord.Status.OFFICE],
                "remote": by_status[AttendanceRecord.Status.REMOTE],
                "off": by_status[AttendanceRecord.Status.OFF],
                "vacation": len(on_vacation),
                "missing": missing,
                "hours": round(sum(r.hours or 0 for r in own), 2),
            }
        )

    return {
        "month": first.strftime("%Y-%m"),
        "working_days": sum(1 for _ in weekdays(first, last, holidays)),
        "holidays": month_holidays,
        "rows": rows,
    }
