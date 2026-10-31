from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateRangeField, RangeBoundary, RangeOperators
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.employees.models import Employee
from apps.users.models import User


class DateRange(models.Func):
    function = "daterange"
    output_field = DateRangeField()


class VacationRequest(models.Model):
    class Type(models.TextChoices):
        ANNUAL = "annual", "Щорічна відпустка"
        SICK = "sick", "Лікарняний"
        UNPAID = "unpaid", "За власний рахунок"
        OTHER = "other", "Інше"

    class Status(models.TextChoices):
        PENDING = "pending", "Очікує розгляду"
        APPROVED = "approved", "Схвалено"
        REJECTED = "rejected", "Відхилено"
        CANCELLED = "cancelled", "Скасовано"

    # Заявки цих статусів займають дати — нова не може з ними перетинатись
    ACTIVE_STATUSES = (Status.PENDING, Status.APPROVED)
    # Ці типи плануються наперед — не можуть починатись у минулому
    PLANNED_TYPES = (Type.ANNUAL, Type.UNPAID)

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="vacation_requests"
    )
    vacation_type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.ANNUAL
    )
    date_start = models.DateField()
    date_end = models.DateField()
    comment = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    decision_comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["-date_start", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(date_end__gte=F("date_start")),
                name="vacation_dates_ordered",
            ),
            # Останній рубіж проти гонок: схвалені періоди одного працівника
            # не перетинаються (потребує btree_gist)
            ExclusionConstraint(
                name="vacation_no_overlapping_approved",
                expressions=[
                    ("employee", RangeOperators.EQUAL),
                    (
                        DateRange(
                            "date_start",
                            "date_end",
                            RangeBoundary(inclusive_lower=True, inclusive_upper=True),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(status="approved"),
            ),
        ]

    def __str__(self):
        return f"{self.employee} — {self.get_vacation_type_display()} {self.date_start}…{self.date_end}"

    @property
    def days(self):
        """Календарні дні включно з обома межами."""
        return (self.date_end - self.date_start).days + 1

    def overlapping(self, statuses):
        qs = VacationRequest.objects.filter(
            employee_id=self.employee_id,
            status__in=statuses,
            date_start__lte=self.date_end,
            date_end__gte=self.date_start,
        )
        return qs.exclude(pk=self.pk) if self.pk else qs

    def clean(self):
        super().clean()
        if not (self.date_start and self.date_end and self.employee_id):
            return
        if self.date_end < self.date_start:
            raise ValidationError(
                {"date_end": "Дата закінчення не може бути раніше дати початку."}
            )
        if self._state.adding:
            if self.vacation_type in self.PLANNED_TYPES and (
                self.date_start < timezone.localdate()
            ):
                raise ValidationError(
                    {"date_start": "Цей тип відпустки не можна почати в минулому."}
                )
            fired = self.employee.date_fired
            if fired and fired <= self.date_start:
                raise ValidationError({"employee": "Працівник звільнений на ці дати."})
        if self.overlapping(self.ACTIVE_STATUSES).exists():
            raise ValidationError(
                "Перетин з іншою заявкою, що очікує розгляду або вже схвалена."
            )

    # --- переходи статусу -------------------------------------------------

    def _review(self, status, reviewer, comment):
        with transaction.atomic():
            locked = VacationRequest.objects.select_for_update().get(pk=self.pk)
            if locked.status != self.Status.PENDING:
                raise ValidationError(
                    "Розглянути можна лише заявку, що очікує розгляду."
                )
            if reviewer.pk == locked.employee.user_id:
                raise ValidationError("Не можна розглядати власну заявку.")
            locked.status = status
            locked.reviewed_by = reviewer
            locked.reviewed_at = timezone.now()
            locked.decision_comment = comment
            locked.save()
        self.refresh_from_db()

    def approve(self, reviewer, comment=""):
        self._review(self.Status.APPROVED, reviewer, comment)

    def reject(self, reviewer, comment=""):
        self._review(self.Status.REJECTED, reviewer, comment)

    def cancel(self):
        """Скасувати можна заявку на розгляді або схвалену, що ще не почалась."""
        cancellable = self.status == self.Status.PENDING or (
            self.status == self.Status.APPROVED
            and self.date_start > timezone.localdate()
        )
        if not cancellable:
            raise ValidationError(
                "Скасувати можна заявку на розгляді або схвалену відпустку, "
                "що ще не почалась."
            )
        self.status = self.Status.CANCELLED
        self.save(update_fields=["status"])
