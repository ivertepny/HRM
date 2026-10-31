import pytest

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import Employee
from apps.employees.tests.factories import EmployeeFactory, PositionFactory
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
            "level": "middle",
            "salary": "2000.00",
            "birth_date": "1995-05-20",
            "date_hired": "2025-03-01",
        },
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == new_user.email
    assert body["structural_unit"] == {"id": unit.id, "full_name": "HQ > IT"}
    assert body["position"]["name"] == "Developer"
    assert (body["level"], body["salary"]) == ("middle", "2000.00")
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


@pytest.mark.parametrize(("field", "value"), [("salary", "-1.00"), ("level", "guru")])
def test_invalid_salary_or_level_returns_400(auth_client, field, value):
    employee = EmployeeFactory()

    response = auth_client.patch(
        f"/api/employees/employees/{employee.id}/", {field: value}, format="json"
    )

    assert response.status_code == 400
    assert field in response.json()


def test_cannot_assign_employee_to_inactive_unit(auth_client):
    employee = EmployeeFactory()
    closed = StructuralUnitFactory(is_active=False)

    response = auth_client.patch(
        f"/api/employees/employees/{employee.id}/",
        {"structural_unit_id": closed.id},
        format="json",
    )

    assert response.status_code == 400


def test_employee_list_is_paginated_and_filterable(auth_client):
    EmployeeFactory.create_batch(2, level="junior")
    EmployeeFactory(level="senior")

    page = auth_client.get("/api/employees/employees/?page_size=2").json()
    seniors = auth_client.get("/api/employees/employees/?level=senior").json()

    assert page["count"] == 3
    assert len(page["results"]) == 2
    assert seniors["count"] == 1


def test_duplicate_position_name_returns_400(auth_client):
    PositionFactory(name="QA")

    response = auth_client.post(
        "/api/employees/positions/", {"name": "QA"}, format="json"
    )

    assert response.status_code == 400


def test_position_in_use_cannot_be_deleted(auth_client):
    employee = EmployeeFactory()

    response = auth_client.delete(f"/api/employees/positions/{employee.position.id}/")

    assert response.status_code == 409
    assert Employee.objects.filter(pk=employee.pk).exists()


def test_user_with_employee_profile_cannot_be_deleted(auth_client):
    employee = EmployeeFactory()

    response = auth_client.delete(f"/api/users/profile/{employee.user.id}/")

    assert response.status_code == 409
