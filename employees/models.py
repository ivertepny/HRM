from django.db import models

from company.models import StructuralUnit
from users.models import User


class Position(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='employee_profile')
    structural_unit = models.ForeignKey(StructuralUnit, on_delete=models.CASCADE, related_name='employees_su')
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    date_hired = models.DateField(null=True, blank=True)
    date_fired = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.user


class CareerHistory(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='career_history')
    date = models.DateField()
    position = models.ForeignKey(Position, on_delete=models.CASCADE)
    salary = models.DecimalField(max_digits=10, decimal_places=2)

    # history = HistoricalRecords()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee.user} - {self.position} - {self.salary}"
