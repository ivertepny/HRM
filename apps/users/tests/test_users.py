import pytest

from apps.access.models import UserRole
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.users.models import User
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

NEW_USER = {
    "email": "new@example.com",
    "first_name": "Ivan",
    "last_name": "Petrenko",
}


def register(client, password, **overrides):
    return client.post(
        "/api/users/register/",
        {**NEW_USER, "password": password, **overrides},
        format="json",
    )


# --- створення облікових записів -------------------------------------------


def test_anonymous_cannot_register(api_client, password):
    assert register(api_client, password).status_code == 401


def test_user_without_permission_cannot_create_accounts(client_as, user, password):
    assert register(client_as(user), password).status_code == 403


def test_hr_creates_account_with_default_role(client_as, user, grant, password):
    grant(user, "users:write")

    response = register(client_as(user), password)

    assert response.status_code == 201
    created = User.objects.get(email="new@example.com")
    assert created.check_password(password)
    assert "password" not in response.json()
    assignment = UserRole.objects.get(user=created)
    assert assignment.role.name == "Employee"
    assert assignment.granted_by == user


@pytest.mark.parametrize("weak", ["123", "password", "new@example.com"])
def test_weak_password_is_rejected(auth_client, weak):
    response = register(auth_client, weak)

    assert response.status_code == 400
    assert "password" in response.json()


def test_duplicate_email_is_rejected(auth_client, user, password):
    response = register(auth_client, password, email=user.email)

    assert response.status_code == 400
    assert "email" in response.json()


# --- перегляд і редагування --------------------------------------------------


def test_user_without_roles_sees_only_self(client_as, user):
    UserFactory.create_batch(2)

    response = client_as(user).get("/api/users/profile/")

    assert [u["id"] for u in response.json()["results"]] == [user.id]


def test_users_read_shows_everyone(client_as, user, grant):
    UserFactory.create_batch(2)
    grant(user, "users:read")

    response = client_as(user).get("/api/users/profile/")

    assert response.json()["count"] == 3


def test_scoped_users_read_shows_only_unit_members(client_as, user, grant):
    it = StructuralUnitFactory(name="IT")
    colleague = EmployeeFactory(structural_unit=it).user
    EmployeeFactory(structural_unit=StructuralUnitFactory(name="Sales"))
    grant(user, "users:read", unit=it)

    response = client_as(user).get("/api/users/profile/")

    assert {u["id"] for u in response.json()["results"]} == {user.id, colleague.id}


def test_user_can_edit_own_name_but_not_status_or_email(client_as, user):
    response = client_as(user).patch(
        f"/api/users/profile/{user.id}/",
        {"first_name": "Олена", "status": "inactive", "email": "hack@example.com"},
        format="json",
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.first_name == "Олена"
    assert (user.status, user.email) == ("active", user.email)
    assert user.email != "hack@example.com"


def test_user_cannot_edit_or_see_others(client_as, user):
    other = UserFactory()
    client = client_as(user)

    assert client.get(f"/api/users/profile/{other.id}/").status_code == 404
    assert (
        client.patch(
            f"/api/users/profile/{other.id}/", {"first_name": "X"}, format="json"
        ).status_code
        == 404
    )


def test_users_write_can_change_status(client_as, user, grant):
    other = UserFactory()
    grant(user, "users:read", "users:write")

    response = client_as(user).patch(
        f"/api/users/profile/{other.id}/", {"status": "inactive"}, format="json"
    )

    assert response.status_code == 200
    other.refresh_from_db()
    assert other.status == "inactive"


def test_read_only_user_cannot_edit_others(client_as, user, grant):
    other = UserFactory()
    grant(user, "users:read")

    response = client_as(user).patch(
        f"/api/users/profile/{other.id}/", {"first_name": "X"}, format="json"
    )

    assert response.status_code == 403


def test_user_cannot_delete_own_account(client_as, user, grant):
    grant(user, "users:read", "users:delete")

    response = client_as(user).delete(f"/api/users/profile/{user.id}/")

    assert response.status_code == 400
    assert User.objects.filter(pk=user.pk).exists()


def test_delete_requires_users_delete(client_as, user, grant):
    other = UserFactory()
    grant(user, "users:read", "users:write")
    client = client_as(user)

    assert client.delete(f"/api/users/profile/{other.id}/").status_code == 403

    grant(user, "users:delete")
    assert client_as(user).delete(f"/api/users/profile/{other.id}/").status_code == 204


def test_me_endpoint(client_as, user):
    client = client_as(user)

    assert client.get("/api/users/me/").json()["email"] == user.email
    response = client.patch("/api/users/me/", {"last_name": "Коваль"}, format="json")
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.last_name == "Коваль"
