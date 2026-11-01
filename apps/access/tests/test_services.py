import datetime

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.access.catalog import SYSTEM_ROLES, all_codenames, matches
from apps.access.models import Permission, Role
from apps.access.services import UserAccess
from apps.company.tests.factories import StructuralUnitFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("granted", "codename", "expected"),
    [
        ({"employees:read"}, "employees:read", True),
        ({"employees:read"}, "employees:write", False),
        ({"employees:*"}, "employees:write", True),
        ({"employees:*"}, "salary:read", False),
        ({"*:*"}, "salary:write", True),
        (set(), "employees:read", False),
    ],
)
def test_matches_supports_wildcards(granted, codename, expected):
    assert matches(granted, codename) is expected


def test_system_roles_use_only_catalog_permissions():
    known = set(all_codenames())
    for spec in SYSTEM_ROLES.values():
        assert set(spec["permissions"]) <= known


def test_seed_roles_is_idempotent():
    call_command("seed_roles", verbosity=0)

    assert Permission.objects.count() == len(all_codenames())
    assert set(
        Role.objects.filter(is_system=True).values_list("name", flat=True)
    ) == set(SYSTEM_ROLES)


def test_seed_roles_keeps_customized_system_role_unless_reset():
    hr = Role.objects.get(name="HR Manager")
    hr.permissions.clear()

    call_command("seed_roles", verbosity=0)
    assert hr.permissions.count() == 0

    call_command("seed_roles", "--reset-system-roles", verbosity=0)
    assert hr.permissions.count() == len(SYSTEM_ROLES["HR Manager"]["permissions"])


def test_seed_roles_prunes_stale_permissions_only_on_request():
    Permission.objects.create(resource="legacy", action="read")

    call_command("seed_roles", verbosity=0)
    assert Permission.objects.filter(codename="legacy:read").exists()

    call_command("seed_roles", "--prune", verbosity=0)
    assert not Permission.objects.filter(codename="legacy:read").exists()


def test_global_role_grants_everywhere(grant):
    user = UserFactory()
    grant(user, "employees:read")
    access = UserAccess(user)

    assert access.has("employees:read")
    assert access.has("employees:read", unit=StructuralUnitFactory())
    assert not access.has("employees:write")
    assert access.units_for("employees:read") is None


def test_scoped_role_applies_to_unit_and_descendants_only(grant):
    company = StructuralUnitFactory(name="Company")
    it = StructuralUnitFactory(name="IT", parent=company)
    backend = StructuralUnitFactory(name="Backend", parent=it)
    sales = StructuralUnitFactory(name="Sales", parent=company)
    user = UserFactory()
    grant(user, "employees:read", unit=it)
    access = UserAccess(user)

    assert access.has("employees:read", unit=it)
    assert access.has("employees:read", unit=backend)
    assert not access.has("employees:read", unit=company)
    assert not access.has("employees:read", unit=sales)
    assert not access.has("employees:read")  # глобально — ні
    assert access.has_anywhere("employees:read")
    assert set(access.units_for("employees:read")) == {it, backend}


def test_expired_role_is_ignored(grant):
    user = UserFactory()
    grant(user, "employees:read", expires_at=timezone.now() - datetime.timedelta(1))
    grant(user, "salary:read", expires_at=timezone.now() + datetime.timedelta(1))
    access = UserAccess(user)

    assert not access.has("employees:read")
    assert access.has("salary:read")


def test_inactive_user_has_no_permissions(grant):
    user = UserFactory(status="inactive")  # is_active виводиться зі статусу
    grant(user, "*:*")

    assert not UserAccess(user).has("employees:read")


def test_superuser_has_everything():
    access = UserAccess(UserFactory(is_superuser=True))

    assert access.has("salary:write")
    assert access.units_for("salary:write") is None


def test_user_without_roles_sees_no_units():
    access = UserAccess(UserFactory())

    assert not access.has_anywhere("employees:read")
    assert not access.units_for("employees:read").exists()
