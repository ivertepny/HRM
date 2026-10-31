import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import ProtectedError

from apps.core.exceptions import exception_handler


def test_django_validation_error_becomes_400_with_field_errors():
    response = exception_handler(ValidationError({"name": "Bad name"}), {})

    assert response.status_code == 400
    assert response.data == {"name": ["Bad name"]}


@pytest.mark.parametrize(
    "exc", [IntegrityError("duplicate key"), ProtectedError("in use", set())]
)
def test_integrity_problems_become_409_without_internal_details(exc):
    response = exception_handler(exc, {})

    assert response.status_code == 409
    assert str(exc.args[0]) not in str(response.data)


def test_unexpected_errors_are_left_to_django():
    assert exception_handler(RuntimeError("boom"), {}) is None
