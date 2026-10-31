import datetime

import factory

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import Employee, Position
from apps.users.tests.factories import UserFactory


class PositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Position
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Position {n}")


class EmployeeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Employee

    user = factory.SubFactory(UserFactory)
    structural_unit = factory.SubFactory(StructuralUnitFactory)
    position = factory.SubFactory(PositionFactory)
    date_hired = datetime.date(2025, 1, 15)
