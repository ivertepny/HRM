import uuid
from pathlib import Path

from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.company.models import StructuralUnit
from apps.core.validators import validate_file_size
from apps.users.models import User


def employee_photo_path(instance, filename):
    # UUID замість оригінальної назви: без колізій і без вгадуваних URL
    return f"employees/photos/{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


def employee_document_path(instance, filename):
    return (
        f"employees/{instance.employee_id}/documents/"
        f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"
    )


def current_request_user():
    """Автор зміни з HistoryRequestMiddleware (None поза HTTP-запитом)."""
    request = getattr(HistoricalRecords.context, "request", None)
    user = getattr(request, "user", None)
    return user if user is not None and user.is_authenticated else None


class Position(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Level(models.TextChoices):
    TRAINEE = "trainee", "Trainee"
    JUNIOR = "junior", "Junior"
    MIDDLE = "middle", "Middle"
    SENIOR = "senior", "Senior"


class Employee(models.Model):
    """Поточний стан працівника.

    Кожна зміна кадрових полів (TRACKED_FIELDS) або звільнення автоматично
    додає запис у CareerHistory. Причину і дату зміни можна передати через
    атрибути `_change_reason` / `_change_date` перед save().
    """

    TRACKED_FIELDS = ("position_id", "structural_unit_id", "level", "salary")

    user = models.OneToOneField(
        User, on_delete=models.PROTECT, related_name="employee_profile"
    )
    structural_unit = models.ForeignKey(
        StructuralUnit, on_delete=models.PROTECT, related_name="employees_su"
    )
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    level = models.CharField(max_length=20, choices=Level.choices, blank=True)
    salary = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    birth_date = models.DateField(null=True, blank=True)
    photo = models.ImageField(
        upload_to=employee_photo_path,
        blank=True,
        validators=[validate_file_size],
    )
    date_hired = models.DateField(null=True, blank=True)
    date_fired = models.DateField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["user__last_name", "id"]

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._career_snapshot = instance._career_state()
        return instance

    def _career_state(self):
        state = {field: getattr(self, field) for field in self.TRACKED_FIELDS}
        state["date_fired"] = self.date_fired
        return state

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        previous = getattr(self, "_career_snapshot", None)
        # Читаємо до super().save(): simple_history теж використовує _change_reason
        reason = getattr(self, "_change_reason", "") or ""
        change_date = getattr(self, "_change_date", None)

        with transaction.atomic():
            super().save(*args, **kwargs)
            event = self._detect_career_event(is_new, previous)
            if event:
                self._log_career_event(event, reason, change_date)

        self._career_snapshot = self._career_state()

    def _detect_career_event(self, is_new, previous):
        if is_new:
            return CareerHistory.Event.HIRED
        if previous is None:
            return None
        if previous["date_fired"] is None and self.date_fired:
            return CareerHistory.Event.FIRED
        if any(previous[f] != getattr(self, f) for f in self.TRACKED_FIELDS):
            return CareerHistory.Event.CHANGED
        return None

    def _log_career_event(self, event, reason, change_date):
        default_date = {
            CareerHistory.Event.HIRED: self.date_hired,
            CareerHistory.Event.FIRED: self.date_fired,
        }.get(event)
        CareerHistory.objects.create(
            employee=self,
            event=event,
            date=change_date or default_date or timezone.localdate(),
            position=self.position,
            structural_unit=self.structural_unit,
            level=self.level,
            salary=self.salary,
            reason=reason,
            changed_by=current_request_user(),
        )


class CareerHistory(models.Model):
    """Журнал кадрових подій. Створюється автоматично з Employee.save()."""

    class Event(models.TextChoices):
        HIRED = "hired", "Прийом"
        CHANGED = "changed", "Зміна"
        FIRED = "fired", "Звільнення"

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="career_history"
    )
    event = models.CharField(
        max_length=20, choices=Event.choices, default=Event.CHANGED
    )
    date = models.DateField(help_text="Дата, з якої зміна діє")
    # Знімок стану працівника після події
    position = models.ForeignKey(Position, on_delete=models.PROTECT)
    structural_unit = models.ForeignKey(
        StructuralUnit, on_delete=models.PROTECT, null=True, blank=True
    )
    level = models.CharField(max_length=20, choices=Level.choices, blank=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    changed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.employee} — {self.get_event_display()} — {self.date}"


class EmployeeDocument(models.Model):
    class DocumentType(models.TextChoices):
        CV = "cv", "CV"
        NDA = "nda", "NDA"
        CONTRACT = "contract", "Договір"
        OTHER = "other", "Інше"

    ALLOWED_EXTENSIONS = ["pdf", "doc", "docx", "odt", "jpg", "jpeg", "png"]

    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="documents"
    )
    document_type = models.CharField(
        max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER
    )
    title = models.CharField(max_length=255, blank=True)
    file = models.FileField(
        upload_to=employee_document_path,
        validators=[
            FileExtensionValidator(ALLOWED_EXTENSIONS),
            validate_file_size,
        ],
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at", "-id"]

    def __str__(self):
        return self.title or f"{self.get_document_type_display()} — {self.employee}"
