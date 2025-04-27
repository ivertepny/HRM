from django.db import models


class Department(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Position(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    user = models.OneToOneField('users.User', on_delete=models.CASCADE, related_name='employee_profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
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
