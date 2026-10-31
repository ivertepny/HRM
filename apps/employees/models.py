from django.db import models
from simple_history.models import HistoricalRecords

from apps.company.models import StructuralUnit
from apps.users.models import User


class Position(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="employee_profile"
    )
    structural_unit = models.ForeignKey(
        StructuralUnit, on_delete=models.CASCADE, related_name="employees_su"
    )
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    date_hired = models.DateField(null=True, blank=True)
    date_fired = models.DateField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["user__last_name"]

    def __str__(self):
        return f"{self.user.last_name} {self.user.first_name}"


class CareerHistory(models.Model):
    employee = models.ForeignKey(
        Employee, on_delete=models.CASCADE, related_name="career_history"
    )
    date = models.DateField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    structural_unit = models.ForeignKey(
        StructuralUnit, on_delete=models.SET_NULL, null=True, blank=True
    )
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} — {self.position} — {self.salary}"
