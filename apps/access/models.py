from django.db import models
from django.db.models import Q
from django.utils import timezone
from simple_history.models import HistoricalRecords

from apps.company.models import StructuralUnit
from apps.users.models import User


class Permission(models.Model):
    """Дозвіл `resource:action`. Набір синхронізується з catalog.py командою seed_roles."""

    codename = models.CharField(max_length=100, unique=True, editable=False)
    resource = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["resource", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["resource", "action"], name="access_permission_unique"
            )
        ]

    def save(self, *args, **kwargs):
        self.codename = f"{self.resource}:{self.action}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codename


class Role(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)
    permissions = models.ManyToManyField(Permission, related_name="roles", blank=True)
    # Системні ролі створює seed_roles; їх не можна видалити чи перейменувати
    is_system = models.BooleanField(default=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserRoleQuerySet(models.QuerySet):
    def active(self):
        return self.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )


class UserRole(models.Model):
    """Призначення ролі користувачу.

    Без structural_unit роль діє глобально; з ним — лише в межах підрозділу
    та всіх його нащадків. expires_at — для тимчасових ролей.
    """

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="role_assignments"
    )
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="assignments")
    structural_unit = models.ForeignKey(
        StructuralUnit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="role_assignments",
    )
    granted_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Аудит: хто, кому і коли видав або відкликав роль
    history = HistoricalRecords()

    objects = UserRoleQuerySet.as_manager()

    class Meta:
        ordering = ["-granted_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "structural_unit"],
                nulls_distinct=False,
                name="access_userrole_unique",
            )
        ]

    def __str__(self):
        scope = f" @ {self.structural_unit}" if self.structural_unit_id else ""
        return f"{self.user} — {self.role}{scope}"
