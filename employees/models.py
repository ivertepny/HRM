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

    # def __str__(self):
    #     return f"{self.first_name} {self.last_name}"


# class SalaryHistory(models.Model):
#     employee = models.ForeignKey(Employee, related_name='salary_history', on_delete=models.CASCADE)
#     salary = models.DecimalField(max_digits=10, decimal_places=2)
#     start_date = models.DateField()
#     end_date = models.DateField(null=True, blank=True)  # В случае текущей зарплаты, end_date может быть пустым.
#
#     def __str__(self):
#         return f"{self.employee.first_name} {self.employee.last_name} - {self.salary} ({self.start_date} to {self.end_date if self.end_date else 'present'})"
