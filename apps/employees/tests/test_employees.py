import pytest

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import CareerHistory, Employee
from apps.employees.tests.factories import (
    CareerHistoryFactory,
    EmployeeFactory,
    PositionFactory,
)
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_create_employee_returns_nested_representation(auth_client):
    root = StructuralUnitFactory(name="HQ")
    unit = StructuralUnitFactory(name="IT", parent=root)
    position = PositionFactory(name="Developer")
    new_user = UserFactory()

    response = auth_client.post(
        "/api/employees/employees/",
        {
            "user_id": new_user.id,
            "structural_unit_id": unit.id,
            "position_id": position.id,
            "date_hired": "2025-03-01",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == new_user.email
    assert body["structural_unit"] == {"id": unit.id, "full_name": "HQ > IT"}
    assert body["position"]["name"] == "Developer"
    assert Employee.objects.filter(user=new_user).exists()


def test_create_employee_with_invalid_data_returns_400(auth_client):
    response = auth_client.post(
        "/api/employees/employees/", {"user_id": 999_999}, format="json"
    )

    assert response.status_code == 400
    assert {"user_id", "structural_unit_id", "position_id"} <= set(response.json())


def test_user_can_have_only_one_employee_profile(auth_client):
    employee = EmployeeFactory()

    response = auth_client.post(
        "/api/employees/employees/",
        {
            "user_id": employee.user.id,
            "structural_unit_id": employee.structural_unit.id,
            "position_id": employee.position.id,
        },
        format="json",
    )

    assert response.status_code == 400
    assert "user_id" in response.json()


def test_employee_list_is_paginated(auth_client):
    EmployeeFactory.create_batch(3)

    response = auth_client.get("/api/employees/employees/?page_size=2")

    body = response.json()
    assert body["count"] == 3
    assert len(body["results"]) == 2
    assert body["next"] is not None


def test_duplicate_position_name_returns_400(auth_client):
    PositionFactory(name="QA")

    response = auth_client.post(
        "/api/employees/positions/", {"name": "QA"}, format="json"
    )

    assert response.status_code == 400


def test_create_career_history_record(auth_client):
    employee = EmployeeFactory()
    position = PositionFactory(name="Senior Developer")

    response = auth_client.post(
        "/api/employees/career-history/",
        {
            "employee": employee.id,
            "date": "2026-01-01",
            "position_id": position.id,
            "salary": "2500.00",
        },
        format="json",
    )

    assert response.status_code == 201
    assert CareerHistory.objects.get(employee=employee).salary == 2500


def test_career_history_filter_by_employee(auth_client):
    record = CareerHistoryFactory()
    CareerHistoryFactory()

    response = auth_client.get(
        f"/api/employees/career-history/?employee={record.employee.id}"
    )

    assert [r["id"] for r in response.json()["results"]] == [record.id]
