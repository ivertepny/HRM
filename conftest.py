import itertools

import pytest
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Завантажені в тестах файли — у тимчасову теку, а не в media/ проєкту."""
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture(autouse=True)
def clear_cache():
    """Кеш (зокрема прав) не переживає тест."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


@pytest.fixture
def user(db):
    """Звичайний користувач без ролей."""
    return UserFactory()


@pytest.fixture
def admin_user(db):
    return UserFactory(is_superuser=True)


@pytest.fixture
def auth_client(api_client, admin_user):
    """Клієнт з повними правами — для тестів бізнес-логіки, не доступу."""
    api_client.force_authenticate(admin_user)
    return api_client


@pytest.fixture
def client_as(db):
    """client_as(user) — окремий клієнт, автентифікований як user."""

    def _client(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    return _client


@pytest.fixture
def catalog(db):
    """Каталог дозволів і системні ролі, як після `manage.py seed_roles`."""
    call_command("seed_roles", verbosity=0)


@pytest.fixture
def grant(catalog):
    """grant(user, "employees:read", unit=None) — створює роль з дозволами і видає її."""
    from apps.access.models import Permission, Role, UserRole

    counter = itertools.count(1)

    def _grant(user, *codenames, unit=None, **extra):
        role = Role.objects.create(name=f"Test role {next(counter)}")
        role.permissions.set(Permission.objects.filter(codename__in=codenames))
        return UserRole.objects.create(
            user=user, role=role, structural_unit=unit, **extra
        )

    return _grant
