import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_no_missing_migrations():
    """Падає, якщо моделі змінені, а міграцію не створено."""
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
