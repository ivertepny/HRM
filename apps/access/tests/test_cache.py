import datetime
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.access import cache as access_cache
from apps.access.models import Permission, Role, UserRole
from apps.access.services import UserAccess
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def test_second_lookup_is_served_from_cache(grant, django_assert_num_queries):
    user = UserFactory()
    grant(user, "employees:read")
    UserAccess(user)  # прогріває кеш

    with django_assert_num_queries(0):
        access = UserAccess(user)

    assert access.has("employees:read")


def test_granting_role_invalidates_user_cache(grant):
    user = UserFactory()
    assert not UserAccess(user).has("salary:read")

    grant(user, "salary:read")

    assert UserAccess(user).has("salary:read")


def test_revoking_role_invalidates_user_cache(grant):
    user = UserFactory()
    assignment = grant(user, "salary:read")
    assert UserAccess(user).has("salary:read")

    assignment.delete()

    assert not UserAccess(user).has("salary:read")


def test_changing_role_permissions_invalidates_all_holders(grant):
    first, second = UserFactory(), UserFactory()
    role = grant(first, "employees:read").role
    UserRole.objects.create(user=second, role=role)
    assert not UserAccess(first).has("salary:read")
    assert not UserAccess(second).has("salary:read")

    role.permissions.add(Permission.objects.get(codename="salary:read"))

    assert UserAccess(first).has("salary:read")
    assert UserAccess(second).has("salary:read")


def test_removing_permission_from_role_invalidates_cache(grant):
    user = UserFactory()
    role = grant(user, "employees:read", "salary:read").role
    assert UserAccess(user).has("salary:read")

    role.permissions.remove(Permission.objects.get(codename="salary:read"))

    assert not UserAccess(user).has("salary:read")


def test_other_users_cache_survives_personal_change(grant, django_assert_num_queries):
    bystander, target = UserFactory(), UserFactory()
    grant(bystander, "employees:read")
    UserAccess(bystander)

    # Видача наявної ролі (не зміна її дозволів) — інвалідує лише target
    UserRole.objects.create(user=target, role=Role.objects.get(name="Employee"))

    with django_assert_num_queries(0):
        assert UserAccess(bystander).has("employees:read")


def test_cache_ttl_does_not_outlive_temporary_role(grant, settings):
    settings.ACCESS_CACHE_TIMEOUT = 300
    user = UserFactory()
    grant(
        user, "salary:read", expires_at=timezone.now() + datetime.timedelta(seconds=60)
    )

    with patch.object(access_cache, "store", wraps=access_cache.store) as store:
        UserAccess(user)

    timeout = store.call_args.args[2]
    assert 0 < timeout <= 60


def test_default_ttl_without_temporary_roles(grant, settings):
    settings.ACCESS_CACHE_TIMEOUT = 300
    user = UserFactory()
    grant(user, "salary:read")

    with patch.object(access_cache, "store", wraps=access_cache.store) as store:
        UserAccess(user)

    assert store.call_args.args[2] == 300


def test_cache_outage_falls_back_to_database(grant):
    user = UserFactory()
    grant(user, "employees:read")
    broken = ConnectionError("redis is down")

    with (
        patch.object(access_cache.cache, "get_many", side_effect=broken),
        patch.object(access_cache.cache, "incr", side_effect=broken),
    ):
        assert UserAccess(user).has("employees:read")
        grant(user, "salary:read")  # інвалідація теж не падає
        assert UserAccess(user).has("salary:read")


def test_permission_changes_visible_via_api_immediately(client_as, auth_client, user):
    client = client_as(user)
    assert client.get("/api/users/me/permissions/").json()["global"] == []

    role = Role.objects.get(name="Employee")
    auth_client.post(
        "/api/access/user-roles/", {"user": user.id, "role": role.id}, format="json"
    )

    assert (
        "ai:use" in client_as(user).get("/api/users/me/permissions/").json()["global"]
    )
