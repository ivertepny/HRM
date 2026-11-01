import pytest

from apps.access.models import Role, UserRole
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory

pytestmark = pytest.mark.django_db


def login(client, user):
    return client.post(
        "/api/users/login/",
        {"email": user.email, "password": DEFAULT_PASSWORD},
        format="json",
    )


# --- статус акаунта --------------------------------------------------------------


def test_status_drives_is_active():
    user = UserFactory()

    user.status = "inactive"
    user.save(update_fields=["status"])
    user.refresh_from_db()

    assert user.is_active is False


def test_deactivated_account_cannot_log_in(auth_client, api_client):
    user = UserFactory()

    auth_client.patch(
        f"/api/users/profile/{user.id}/", {"status": "inactive"}, format="json"
    )

    assert login(api_client, user).status_code == 400


def test_deactivation_revokes_existing_access_token(auth_client, client_as):
    from rest_framework.test import APIClient

    user = UserFactory()
    client = APIClient()
    access = login(client, user).json()["token"]["access"]
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    assert client.get("/api/users/me/").status_code == 200

    auth_client.patch(
        f"/api/users/profile/{user.id}/", {"status": "inactive"}, format="json"
    )

    assert client.get("/api/users/me/").status_code == 401


def test_admin_cannot_change_own_status(auth_client, admin_user):
    response = auth_client.patch(
        f"/api/users/profile/{admin_user.id}/", {"status": "inactive"}, format="json"
    )

    assert response.status_code == 400
    assert "status" in response.json()


# --- список акаунтів --------------------------------------------------------------


def test_user_list_search_and_filters(auth_client, admin_user):
    hired = EmployeeFactory(user=UserFactory(first_name="Олена", last_name="Коваль"))
    candidate = UserFactory(first_name="Петро", last_name="Шевчук")
    blocked = UserFactory(status="inactive")

    def ids(**params):
        results = auth_client.get("/api/users/profile/", params).json()["results"]
        return {u["id"] for u in results}

    assert ids(search="коваль") == {hired.user.id}
    assert ids(status="inactive") == {blocked.id}
    assert ids(has_employee="true") == {hired.user.id}
    assert candidate.id in ids(has_employee="false")
    assert hired.user.id not in ids(has_employee="false")


def test_user_shows_employee_profile_id(auth_client):
    employee = EmployeeFactory()

    body = auth_client.get(f"/api/users/profile/{employee.user.id}/").json()

    assert body["employee"] == employee.id
    assert (
        auth_client.get(f"/api/users/profile/{UserFactory().id}/").json()["employee"]
        is None
    )


# --- ролі -------------------------------------------------------------------------


def test_roles_show_active_holder_count(auth_client, catalog):
    import datetime

    from django.utils import timezone

    role = Role.objects.get(name="Employee")
    UserRole.objects.create(user=UserFactory(), role=role)
    UserRole.objects.create(
        user=UserFactory(), role=role, structural_unit=StructuralUnitFactory()
    )
    UserRole.objects.create(
        user=UserFactory(),
        role=role,
        expires_at=timezone.now() + datetime.timedelta(days=1),
    )
    UserRole.objects.create(user=UserFactory(status="inactive"), role=role)
    expired = UserRole.objects.create(user=UserFactory(), role=role)
    UserRole.objects.filter(pk=expired.pk).update(
        expires_at=timezone.now() - datetime.timedelta(days=1)
    )

    roles = {
        r["name"]: r for r in auth_client.get("/api/access/roles/").json()["results"]
    }

    assert roles["Employee"]["users_count"] == 3


def test_user_roles_include_unit_name(auth_client, catalog):
    unit = StructuralUnitFactory(name="IT")
    assignment = UserRole.objects.create(
        user=UserFactory(),
        role=Role.objects.get(name="HR Manager"),
        structural_unit=unit,
    )

    body = auth_client.get(f"/api/access/user-roles/{assignment.id}/").json()

    assert body["structural_unit_name"] == "IT"
