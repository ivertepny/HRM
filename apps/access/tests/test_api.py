import datetime

import pytest
from django.utils import timezone

from apps.access.models import Role, UserRole
from apps.company.tests.factories import StructuralUnitFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client(auth_client):
    return auth_client


@pytest.fixture
def role_manager(api_client, grant):
    """Може керувати ролями, але сам має лише employees:read."""
    user = UserFactory()
    grant(user, "roles:read", "roles:manage", "employees:read")
    api_client.force_authenticate(user)
    return api_client


def create_role(client, name, *permissions):
    return client.post(
        "/api/access/roles/",
        {"name": name, "permissions": list(permissions)},
        format="json",
    )


def test_regular_user_cannot_read_roles(client_as, user):
    assert client_as(user).get("/api/access/roles/").status_code == 403


def test_permission_catalog_is_listed_unpaginated(admin_client):
    response = admin_client.get("/api/access/permissions/")

    codenames = [p["codename"] for p in response.json()]
    assert {"*:*", "employees:read", "salary:*"} <= set(codenames)
    assert admin_client.get("/api/access/permissions/salary:read/").status_code == 200


def test_admin_creates_role_with_permissions(admin_client):
    response = create_role(admin_client, "Recruiter", "employees:read", "documents:*")

    assert response.status_code == 201
    role = Role.objects.get(name="Recruiter")
    assert set(role.permissions.values_list("codename", flat=True)) == {
        "employees:read",
        "documents:*",
    }
    assert role.is_system is False


def test_unknown_permission_is_rejected(admin_client):
    response = create_role(admin_client, "Broken", "employees:fly")

    assert response.status_code == 400
    assert "permissions" in response.json()


def test_system_role_cannot_be_deleted_or_renamed(admin_client):
    hr = Role.objects.get(name="HR Manager")

    assert admin_client.delete(f"/api/access/roles/{hr.id}/").status_code == 400
    renamed = admin_client.patch(
        f"/api/access/roles/{hr.id}/", {"name": "HR"}, format="json"
    )
    assert renamed.status_code == 400


def test_role_in_use_cannot_be_deleted(admin_client):
    role_id = create_role(admin_client, "Temp", "employees:read").json()["id"]
    UserRole.objects.create(user=UserFactory(), role_id=role_id)

    assert admin_client.delete(f"/api/access/roles/{role_id}/").status_code == 409


def test_cannot_create_role_with_permissions_you_lack(role_manager):
    allowed = create_role(role_manager, "Viewer", "employees:read")
    escalated = create_role(role_manager, "Payroll", "employees:read", "salary:write")

    assert allowed.status_code == 201
    assert escalated.status_code == 400
    assert "salary:write" in str(escalated.json()["permissions"])


def test_assign_role_records_granter_and_history(admin_client):
    target = UserFactory()
    role = Role.objects.get(name="Employee")

    response = admin_client.post(
        "/api/access/user-roles/", {"user": target.id, "role": role.id}, format="json"
    )

    assert response.status_code == 201
    assignment = UserRole.objects.get(user=target)
    assert assignment.granted_by.is_superuser
    assert assignment.history.first().history_type == "+"


def test_cannot_assign_role_with_permissions_you_lack(role_manager):
    target = UserFactory()
    admin_role = Role.objects.get(name="System Admin")

    response = role_manager.post(
        "/api/access/user-roles/",
        {"user": target.id, "role": admin_role.id},
        format="json",
    )

    assert response.status_code == 400
    assert not UserRole.objects.filter(user=target).exists()


def test_duplicate_assignment_is_rejected(admin_client):
    target = UserFactory()
    role = Role.objects.get(name="Employee")
    payload = {"user": target.id, "role": role.id}

    admin_client.post("/api/access/user-roles/", payload, format="json")
    duplicate = admin_client.post("/api/access/user-roles/", payload, format="json")

    assert duplicate.status_code == 400


def test_same_role_can_be_scoped_to_different_units(admin_client):
    target = UserFactory()
    role = Role.objects.get(name="HR Manager")

    for unit in (StructuralUnitFactory(), StructuralUnitFactory()):
        response = admin_client.post(
            "/api/access/user-roles/",
            {"user": target.id, "role": role.id, "structural_unit": unit.id},
            format="json",
        )
        assert response.status_code == 201


def test_expires_at_must_be_in_future(admin_client):
    response = admin_client.post(
        "/api/access/user-roles/",
        {
            "user": UserFactory().id,
            "role": Role.objects.get(name="Employee").id,
            "expires_at": (timezone.now() - datetime.timedelta(hours=1)).isoformat(),
        },
        format="json",
    )

    assert response.status_code == 400
    assert "expires_at" in response.json()


def test_revoke_role(admin_client):
    assignment = UserRole.objects.create(
        user=UserFactory(), role=Role.objects.get(name="Employee")
    )

    response = admin_client.delete(f"/api/access/user-roles/{assignment.id}/")

    assert response.status_code == 204
    assert not UserRole.objects.filter(pk=assignment.pk).exists()


def test_cannot_revoke_role_with_permissions_you_lack(role_manager):
    assignment = UserRole.objects.create(
        user=UserFactory(), role=Role.objects.get(name="System Admin")
    )

    response = role_manager.delete(f"/api/access/user-roles/{assignment.id}/")

    assert response.status_code == 403
    assert UserRole.objects.filter(pk=assignment.pk).exists()


def test_my_permissions(client_as, user, grant):
    it = StructuralUnitFactory(name="IT")
    grant(user, "employees:read", "ai:use")
    grant(user, "employees:write", unit=it)

    response = client_as(user).get("/api/users/me/permissions/")

    body = response.json()
    assert response.status_code == 200
    assert body["is_superuser"] is False
    assert body["global"] == ["ai:use", "employees:read"]
    assert body["scoped"] == [
        {"unit": {"id": it.id, "name": "IT"}, "permissions": ["employees:write"]}
    ]
    assert len(body["roles"]) == 2


def test_my_permissions_requires_authentication(api_client):
    assert api_client.get("/api/users/me/permissions/").status_code == 401
