import datetime

import pytest

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import CareerHistory
from apps.employees.tests.factories import EmployeeFactory, PositionFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def patch_employee(client, employee, data):
    return client.patch(f"/api/employees/employees/{employee.id}/", data, format="json")


def test_hiring_creates_hired_record_with_author(auth_client, admin_user):
    response = auth_client.post(
        "/api/employees/employees/",
        {
            "user_id": UserFactory().id,
            "structural_unit_id": StructuralUnitFactory().id,
            "position_id": PositionFactory().id,
            "salary": "1500.00",
            "date_hired": "2025-02-01",
            "change_reason": "Оффер прийнято",
        },
        format="json",
    )

    record = CareerHistory.objects.get(employee_id=response.json()["id"])
    assert record.event == CareerHistory.Event.HIRED
    assert record.date == datetime.date(2025, 2, 1)
    assert record.salary == 1500
    assert record.reason == "Оффер прийнято"
    assert record.changed_by == admin_user


def test_salary_change_is_logged_with_reason_and_effective_date(auth_client):
    employee = EmployeeFactory(salary="1000.00")

    response = patch_employee(
        auth_client,
        employee,
        {
            "salary": "1300.00",
            "change_reason": "Перегляд зарплати",
            "effective_date": "2026-01-01",
        },
    )

    assert response.status_code == 200
    latest = employee.career_history.first()
    assert latest.event == CareerHistory.Event.CHANGED
    assert latest.salary == 1300
    assert latest.reason == "Перегляд зарплати"
    assert latest.date == datetime.date(2026, 1, 1)
    assert employee.career_history.count() == 2  # hired + changed


def test_promotion_snapshot_contains_full_new_state(auth_client):
    employee = EmployeeFactory(level="junior", salary="1000.00")
    new_unit = StructuralUnitFactory(name="Platform")
    new_position = PositionFactory(name="Tech Lead")

    patch_employee(
        auth_client,
        employee,
        {
            "level": "senior",
            "position_id": new_position.id,
            "structural_unit_id": new_unit.id,
        },
    )

    latest = employee.career_history.first()
    assert (latest.level, latest.position, latest.structural_unit) == (
        "senior",
        new_position,
        new_unit,
    )
    assert latest.salary == 1000  # незмінні поля теж у знімку


def test_non_career_fields_do_not_create_records(auth_client):
    employee = EmployeeFactory()

    patch_employee(auth_client, employee, {"birth_date": "1990-01-01"})
    patch_employee(auth_client, employee, {"level": employee.level})

    assert employee.career_history.count() == 1  # тільки hired


def test_firing_creates_fired_record_dated_by_date_fired(auth_client):
    employee = EmployeeFactory()

    patch_employee(auth_client, employee, {"date_fired": "2026-06-30"})

    latest = employee.career_history.first()
    assert latest.event == CareerHistory.Event.FIRED
    assert latest.date == datetime.date(2026, 6, 30)


def test_career_history_is_read_only(auth_client):
    employee = EmployeeFactory()

    response = auth_client.post(
        "/api/employees/career-history/",
        {"employee": employee.id, "date": "2026-01-01"},
        format="json",
    )

    assert response.status_code == 405


def test_career_history_filter_by_employee(auth_client):
    employee = EmployeeFactory()
    EmployeeFactory()

    response = auth_client.get(f"/api/employees/career-history/?employee={employee.id}")

    results = response.json()["results"]
    assert [r["employee"] for r in results] == [employee.id]
    assert results[0]["event"] == "hired"
    assert results[0]["structural_unit"]["id"] == employee.structural_unit.id
