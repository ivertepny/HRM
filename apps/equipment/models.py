from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.employees.models import Employee
from apps.users.models import User


class Equipment(models.Model):
    """Одиниця обладнання.

    Стан випливає з полів: списано (written_off_at) → у працівника (holder) →
    інакше на складі. holder — денормалізація активного EquipmentAssignment:
    дає фільтр за підрозділом власника без підзапитів. Змінюється лише через
    assign() / return_from_holder(), разом із журналом видач.
    """

    class Category(models.TextChoices):
        LAPTOP = "laptop", "Ноутбук"
        DESKTOP = "desktop", "Комп'ютер"
        MONITOR = "monitor", "Монітор"
        PHONE = "phone", "Телефон"
        PERIPHERAL = "peripheral", "Периферія"
        OTHER = "other", "Інше"

    class State(models.TextChoices):
        IN_STOCK = "in_stock", "На складі"
        ASSIGNED = "assigned", "Видано"
        WRITTEN_OFF = "written_off", "Списано"

    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    serial_number = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    holder = models.ForeignKey(
        Employee,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="equipment",
        editable=False,
    )
    written_off_at = models.DateField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["name", "id"]
        verbose_name_plural = "equipment"
        constraints = [
            models.CheckConstraint(
                condition=Q(holder__isnull=True) | Q(written_off_at__isnull=True),
                name="equipment_written_off_not_held",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.serial_number})"

    @property
    def state(self) -> str:
        if self.written_off_at:
            return self.State.WRITTEN_OFF
        if self.holder_id:
            return self.State.ASSIGNED
        return self.State.IN_STOCK

    @classmethod
    def state_q(cls, state):
        return {
            cls.State.IN_STOCK: Q(holder__isnull=True, written_off_at__isnull=True),
            cls.State.ASSIGNED: Q(holder__isnull=False),
            cls.State.WRITTEN_OFF: Q(written_off_at__isnull=False),
        }[state]

    def _locked(self):
        return Equipment.objects.select_for_update().get(pk=self.pk)

    @staticmethod
    def _check_date(value, field):
        if value > timezone.localdate():
            raise ValidationError({field: "Дата не може бути в майбутньому."})

    # --- операції ----------------------------------------------------------

    def assign(self, employee, date, by=None, note=""):
        """Видати працівнику: лише зі складу і не раніше останнього повернення."""
        self._check_date(date, "date_assigned")
        if employee.date_fired and employee.date_fired <= date:
            raise ValidationError({"employee_id": "Працівник звільнений на цю дату."})
        with transaction.atomic():
            item = self._locked()
            if item.state != self.State.IN_STOCK:
                raise ValidationError("Видати можна лише обладнання, що на складі.")
            last = item.assignments.order_by("-date_returned").first()
            if last and last.date_returned > date:
                raise ValidationError(
                    {
                        "date_assigned": (
                            "Дата видачі раніше за останнє повернення "
                            f"({last.date_returned:%d.%m.%Y})."
                        )
                    }
                )
            assignment = EquipmentAssignment.objects.create(
                equipment=item,
                employee=employee,
                date_assigned=date,
                assigned_by=by,
                note=note,
            )
            item.holder = employee
            item.save(update_fields=["holder"])
        self.refresh_from_db()
        return assignment

    def return_from_holder(self, date, by=None, note=""):
        """Повернути на склад; закриває активну видачу."""
        self._check_date(date, "date_returned")
        with transaction.atomic():
            item = self._locked()
            active = item.assignments.filter(date_returned__isnull=True).first()
            if active is None:
                raise ValidationError("Обладнання зараз нікому не видано.")
            if date < active.date_assigned:
                raise ValidationError(
                    {"date_returned": "Дата повернення раніше за дату видачі."}
                )
            active.date_returned = date
            active.returned_by = by
            if note:
                active.note = f"{active.note}\n{note}".strip()
            active.save(update_fields=["date_returned", "returned_by", "note"])
            item.holder = None
            item.save(update_fields=["holder"])
        self.refresh_from_db()
        return active

    def write_off(self, date):
        """Списати можна лише те, що на складі (спершу — повернути)."""
        self._check_date(date, "date")
        with transaction.atomic():
            item = self._locked()
            if item.state != self.State.IN_STOCK:
                raise ValidationError("Списати можна лише обладнання, що на складі.")
            item.written_off_at = date
            item.save(update_fields=["written_off_at"])
        self.refresh_from_db()

    def delete(self, *args, **kwargs):
        if self.assignments.exists():
            raise ValidationError(
                "Обладнання з історією видач не видаляється — його можна списати."
            )
        return super().delete(*args, **kwargs)


class EquipmentAssignment(models.Model):
    """Журнал видач: без date_returned — обладнання зараз у працівника."""

    equipment = models.ForeignKey(
        Equipment, on_delete=models.CASCADE, related_name="assignments"
    )
    employee = models.ForeignKey(
        Employee, on_delete=models.PROTECT, related_name="equipment_assignments"
    )
    date_assigned = models.DateField()
    date_returned = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=500, blank=True)
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    returned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-date_assigned", "-id"]
        constraints = [
            # Одна одиниця — не більше одного активного призначення
            models.UniqueConstraint(
                fields=["equipment"],
                condition=Q(date_returned__isnull=True),
                name="equipment_single_active_assignment",
            ),
            models.CheckConstraint(
                condition=Q(date_returned__isnull=True)
                | Q(date_returned__gte=F("date_assigned")),
                name="equipment_assignment_dates_ordered",
            ),
        ]

    def __str__(self):
        return f"{self.equipment} → {self.employee}"

    @property
    def is_active(self) -> bool:
        return self.date_returned is None
