import pytest
from django.core.management import call_command

from apps.access.models import Permission, Role, UserRole


@pytest.fixture(autouse=True)
def catalog(db):
    """Каталог дозволів і системні ролі, як після `manage.py seed_roles`."""
    call_command("seed_roles", verbosity=0)


@pytest.fixture
def grant():
    """grant(user, "employees:read", unit=None) — створює роль з дозволами і видає її."""
    counter = iter(range(1, 10_000))

    def _grant(user, *codenames, unit=None, **extra):
        role = Role.objects.create(name=f"Test role {next(counter)}")
        role.permissions.set(Permission.objects.filter(codename__in=codenames))
        return UserRole.objects.create(
            user=user, role=role, structural_unit=unit, **extra
        )

    return _grant
