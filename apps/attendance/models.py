import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.employees.models import Employee


class AttendanceRecord(models.Model):
    """Відмітка присутності працівника за день (одна на день)."""

    class Status(models.TextChoices):
        OFFICE = "office", "В офісі"
        REMOTE = "remote", "Віддалено"
        OFF = "off", "Не працює"

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)
    time_start = models.TimeField(null=True, blank=True)
    time_end = models.TimeField(null=True, blank=True)
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "date"], name="attendance_one_record_per_day"
            ),
            models.CheckConstraint(
                condition=Q(time_start__isnull=True)
                | Q(time_end__isnull=True)
                | Q(time_end__gt=F("time_start")),
                name="attendance_times_ordered",
            ),
        ]

    def __str__(self):
        return f"{self.employee} — {self.date} ({self.get_status_display()})"

    @property
    def hours(self) -> float | None:
        """Тривалість у годинах, якщо відмічено і початок, і кінець."""
        if not (self.time_start and self.time_end):
            return None
        start = datetime.datetime.combine(self.date, self.time_start)
        end = datetime.datetime.combine(self.date, self.time_end)
        return round((end - start).total_seconds() / 3600, 2)

    @staticmethod
    def editable_since(today=None):
        today = today or timezone.localdate()
        return today - datetime.timedelta(days=settings.ATTENDANCE_EDIT_DAYS)

    def is_editable(self, today=None) -> bool:
        return self.date >= self.editable_since(today)

    def clean(self):
        super().clean()
        if not (self.date and self.employee_id):
            return
        today = timezone.localdate()
        if self.date > today:
            raise ValidationError({"date": "Не можна відмітитись наперед."})
        if not self.is_editable(today):
            raise ValidationError(
                {
                    "date": f"Табель старший за {settings.ATTENDANCE_EDIT_DAYS} дн. "
                    "закрито для змін."
                }
            )
        employee = self.employee
        if employee.date_hired and self.date < employee.date_hired:
            raise ValidationError({"date": "Дата раніше за дату прийому."})
        if employee.date_fired and self.date > employee.date_fired:
            raise ValidationError({"date": "Працівник звільнений на цю дату."})
        if self.status == self.Status.OFF:
            self.time_start = self.time_end = None
        elif self.time_end and not self.time_start:
            raise ValidationError({"time_start": "Вкажіть час початку."})
        if self.time_start and self.time_end and self.time_end <= self.time_start:
            raise ValidationError({"time_end": "Кінець має бути пізніше за початок."})


class Holiday(models.Model):
    """Неробочий день компанії: не рахується робочим у табелі.

    Календар веде HR, а не код: в Україні під час воєнного стану державні
    свята — робочі дні, після нього — знову вихідні; компанія може мати й свої.
    """

    date = models.DateField(unique=True)
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date:%d.%m.%Y} — {self.name}"
