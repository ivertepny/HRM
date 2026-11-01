import pytest
from django.core.management import CommandError, call_command

from apps.access.services import UserAccess
from apps.employees.models import Employee
from apps.equipment.models import Equipment, EquipmentAssignment
from apps.users.models import User
from apps.vacations.models import VacationRequest

pytestmark = pytest.mark.django_db


def test_seed_demo_is_idempotent(settings):
    settings.DEBUG = True
    call_command("seed_demo", verbosity=0)
    call_command("seed_demo", verbosity=0)

    assert User.objects.filter(email__endswith="@example.com").count() == 5
    assert Employee.objects.count() == 4
    assert VacationRequest.objects.count() == 2
    assert Equipment.objects.count() == 6
    assert EquipmentAssignment.objects.filter(date_returned__isnull=True).count() == 3


def test_seed_demo_users_can_log_in_with_given_password(settings, api_client):
    settings.DEBUG = True
    call_command("seed_demo", "--password", "Other-pass-2026", verbosity=0)

    response = api_client.post(
        "/api/users/login/",
        {"email": "hr@example.com", "password": "Other-pass-2026"},
        format="json",
    )

    assert response.status_code == 200
    assert UserAccess(User.objects.get(email="hr@example.com")).has("vacations:manage")


def test_seed_demo_refuses_without_debug(settings):
    settings.DEBUG = False

    with pytest.raises(CommandError):
        call_command("seed_demo", verbosity=0)
