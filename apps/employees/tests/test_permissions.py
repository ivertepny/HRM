import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import EmployeeDocument
from apps.employees.tests.factories import EmployeeFactory, PositionFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def units():
    company = StructuralUnitFactory(name="Company")
    return {
        "company": company,
        "it": StructuralUnitFactory(name="IT", parent=company),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


@pytest.fixture
def me(units):
    """Працівник IT із зарплатою; його user — без ролей."""
    return EmployeeFactory(structural_unit=units["it"], salary="1000.00")


def employee_url(employee):
    return f"/api/employees/employees/{employee.id}/"


# --- перегляд ----------------------------------------------------------------


def test_without_roles_only_own_profile_is_visible(client_as, me, units):
    EmployeeFactory(structural_unit=units["sales"])

    response = client_as(me.user).get("/api/employees/employees/")

    assert [e["id"] for e in response.json()["results"]] == [me.id]


def test_own_salary_is_visible_without_permission(client_as, me):
    response = client_as(me.user).get(employee_url(me))

    assert response.json()["salary"] == "1000.00"


def test_directory_hides_other_salaries(client_as, me, grant, units):
    colleague = EmployeeFactory(structural_unit=units["it"], salary="5000.00")
    grant(me.user, "employees:read")

    body = client_as(me.user).get(employee_url(colleague)).json()

    assert body["id"] == colleague.id
    assert "salary" not in body


def test_salary_read_reveals_salaries(client_as, user, grant, me):
    grant(user, "employees:read", "salary:read")

    assert client_as(user).get(employee_url(me)).json()["salary"] == "1000.00"


def test_scoped_role_limits_employee_list_to_subtree(client_as, user, grant, units):
    backend = StructuralUnitFactory(name="Backend", parent=units["it"])
    in_it = EmployeeFactory(structural_unit=units["it"])
    in_backend = EmployeeFactory(structural_unit=backend)
    in_sales = EmployeeFactory(structural_unit=units["sales"])
    grant(user, "employees:read", unit=units["it"])
    client = client_as(user)

    ids = {e["id"] for e in client.get("/api/employees/employees/").json()["results"]}

    assert ids == {in_it.id, in_backend.id}
    assert client.get(employee_url(in_sales)).status_code == 404


def test_scoped_salary_read_applies_only_inside_scope(client_as, user, grant, units):
    in_it = EmployeeFactory(structural_unit=units["it"], salary="1.00")
    in_sales = EmployeeFactory(structural_unit=units["sales"], salary="2.00")
    grant(user, "employees:read")
    grant(user, "salary:read", unit=units["it"])
    client = client_as(user)

    assert "salary" in client.get(employee_url(in_it)).json()
    assert "salary" not in client.get(employee_url(in_sales)).json()


def test_career_history_hides_salary_of_others(client_as, me, grant, units):
    colleague = EmployeeFactory(structural_unit=units["it"], salary="5000.00")
    grant(me.user, "employees:read")
    client = client_as(me.user)

    own = client.get(f"/api/employees/career-history/?employee={me.id}").json()
    other = client.get(f"/api/employees/career-history/?employee={colleague.id}").json()

    assert own["results"][0]["salary"] == "1000.00"
    assert "salary" not in other["results"][0]


def test_own_career_history_visible_without_roles(client_as, me):
    EmployeeFactory()

    response = client_as(me.user).get("/api/employees/career-history/")

    assert [r["employee"] for r in response.json()["results"]] == [me.id]


# --- зміни -------------------------------------------------------------------


def test_employee_cannot_edit_own_profile(client_as, me):
    response = client_as(me.user).patch(
        employee_url(me), {"level": "senior"}, format="json"
    )

    assert response.status_code == 403


def test_employees_write_cannot_change_salary(client_as, user, grant, me):
    grant(user, "employees:read", "employees:write")
    client = client_as(user)

    assert (
        client.patch(employee_url(me), {"level": "senior"}, format="json").status_code
        == 200
    )
    salary = client.patch(employee_url(me), {"salary": "9999.00"}, format="json")
    assert salary.status_code == 403
    me.refresh_from_db()
    assert me.salary == 1000


def test_salary_write_allows_salary_change(client_as, user, grant, me):
    grant(user, "employees:read", "employees:write", "salary:write")

    response = client_as(user).patch(
        employee_url(me), {"salary": "1200.00"}, format="json"
    )

    assert response.status_code == 200
    me.refresh_from_db()
    assert me.salary == 1200


def test_scoped_hr_cannot_hire_into_foreign_unit(client_as, user, grant, units):
    grant(user, "employees:read", "employees:write", unit=units["it"])
    payload = {
        "user_id": UserFactory().id,
        "position_id": PositionFactory().id,
    }
    client = client_as(user)

    inside = client.post(
        "/api/employees/employees/",
        {**payload, "structural_unit_id": units["it"].id},
        format="json",
    )
    outside = client.post(
        "/api/employees/employees/",
        {
            "user_id": UserFactory().id,
            "position_id": payload["position_id"],
            "structural_unit_id": units["sales"].id,
        },
        format="json",
    )

    assert inside.status_code == 201
    assert outside.status_code == 403


def test_scoped_hr_cannot_transfer_out_of_scope(client_as, user, grant, units, me):
    grant(user, "employees:read", "employees:write", unit=units["it"])

    response = client_as(user).patch(
        employee_url(me), {"structural_unit_id": units["sales"].id}, format="json"
    )

    assert response.status_code == 403


def test_delete_requires_employees_delete(client_as, user, grant, me):
    grant(user, "employees:read", "employees:write")

    assert client_as(user).delete(employee_url(me)).status_code == 403


def test_positions_require_permissions(client_as, user, grant):
    client = client_as(user)
    assert client.get("/api/employees/positions/").status_code == 403

    grant(user, "employees:read")
    client = client_as(user)
    assert client.get("/api/employees/positions/").status_code == 200
    assert (
        client.post(
            "/api/employees/positions/", {"name": "X"}, format="json"
        ).status_code
        == 403
    )


# --- документи ---------------------------------------------------------------


def upload(client, employee):
    return client.post(
        "/api/employees/documents/",
        {
            "employee": employee.id,
            "document_type": "cv",
            "file": SimpleUploadedFile("cv.pdf", b"%PDF-1.4"),
        },
        format="multipart",
    )


def test_own_documents_are_readable_but_not_uploadable(client_as, auth_client, me):
    upload(auth_client, me)
    upload(auth_client, EmployeeFactory())
    client = client_as(me.user)

    listed = client.get("/api/employees/documents/").json()["results"]

    assert [d["employee"] for d in listed] == [me.id]
    assert upload(client, me).status_code == 403


def test_scoped_documents_write(client_as, user, grant, units):
    grant(user, "documents:read", "documents:write", unit=units["it"])
    client = client_as(user)

    assert (
        upload(client, EmployeeFactory(structural_unit=units["it"])).status_code == 201
    )
    assert (
        upload(client, EmployeeFactory(structural_unit=units["sales"])).status_code
        == 403
    )


def test_document_delete_requires_permission(client_as, auth_client, user, grant, me):
    document_id = upload(auth_client, me).json()["id"]
    grant(user, "documents:read", "documents:write")

    response = client_as(user).delete(f"/api/employees/documents/{document_id}/")

    assert response.status_code == 403
    assert EmployeeDocument.objects.filter(pk=document_id).exists()
