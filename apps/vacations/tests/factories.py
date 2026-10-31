import datetime

import factory
from django.utils import timezone

from apps.employees.tests.factories import EmployeeFactory
from apps.vacations.models import VacationRequest


def in_days(days):
    return timezone.localdate() + datetime.timedelta(days=days)


class VacationRequestFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = VacationRequest

    employee = factory.SubFactory(EmployeeFactory)
    vacation_type = VacationRequest.Type.ANNUAL
    date_start = factory.LazyFunction(lambda: in_days(10))
    date_end = factory.LazyFunction(lambda: in_days(14))
