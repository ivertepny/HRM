import pytest
from rest_framework.test import APIClient

from apps.users.tests.factories import DEFAULT_PASSWORD, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def password():
    return DEFAULT_PASSWORD


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def auth_client(api_client, user):
    """Клієнт, автентифікований як `user` (без JWT — для більшості тестів достатньо)."""
    api_client.force_authenticate(user)
    return api_client
