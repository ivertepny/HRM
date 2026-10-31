import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory

pytestmark = pytest.mark.django_db


def employee_url(employee):
    return f"/api/employees/employees/{employee.id}/"


def test_currency_defaults_to_uah(auth_client):
    employee = EmployeeFactory(salary="1000.00")

    body = auth_client.get(employee_url(employee)).json()

    assert (body["salary"], body["salary_currency"]) == ("1000.00", "UAH")


def test_currency_change_is_logged_in_career_history(auth_client):
    employee = EmployeeFactory(salary="1000.00")

    auth_client.patch(employee_url(employee), {"salary_currency": "USD"}, format="json")

    latest = employee.career_history.first()
    assert (latest.event, latest.salary_currency) == ("changed", "USD")


def test_unknown_currency_is_rejected(auth_client):
    employee = EmployeeFactory()

    response = auth_client.patch(
        employee_url(employee), {"salary_currency": "BTC"}, format="json"
    )

    assert response.status_code == 400


def test_currency_hidden_together_with_salary(client_as, user, grant):
    colleague = EmployeeFactory(salary="5000.00", salary_currency="EUR")
    grant(user, "employees:read")

    body = client_as(user).get(employee_url(colleague)).json()

    assert "salary" not in body
    assert "salary_currency" not in body


def test_currency_change_requires_salary_write(client_as, user, grant):
    employee = EmployeeFactory(salary="1000.00")
    grant(user, "employees:read", "employees:write")

    response = client_as(user).patch(
        employee_url(employee), {"salary_currency": "USD"}, format="json"
    )

    assert response.status_code == 403


def test_scoped_salary_visibility_does_not_query_per_row(client_as, user, grant):
    it = StructuralUnitFactory(name="IT")
    grant(user, "employees:read", unit=it)
    grant(user, "salary:read", unit=it)
    client = client_as(user)

    def list_queries():
        with CaptureQueriesContext(connection) as ctx:
            response = client.get("/api/employees/employees/?page_size=100")
        assert all("salary" in e for e in response.json()["results"])
        return len(ctx)

    EmployeeFactory.create_batch(2, structural_unit=it, salary="1.00")
    list_queries()  # прогріває кеш прав, щоб порівнювати однакові умови
    small = list_queries()
    EmployeeFactory.create_batch(8, structural_unit=it, salary="1.00")
    large = list_queries()

    assert large == small
