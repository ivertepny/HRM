from types import SimpleNamespace

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.access.permissions import HasPermission
from apps.company.tests.factories import StructuralUnitFactory
from apps.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

factory = APIRequestFactory()


def drf_request(method, user):
    from rest_framework.request import Request

    django_request = getattr(factory, method.lower())("/")
    force_authenticate(django_request, user=user)
    request = Request(django_request)
    request.user = user
    return request


def handler(*args, **kwargs):
    return None


def view(action=None, **required):
    # Як у справжньої view: обробники методів є атрибутами
    return SimpleNamespace(
        action=action,
        required_permissions=required,
        get=handler,
        post=handler,
        delete=handler,
    )


@pytest.mark.parametrize(
    ("method", "action", "required", "expected"),
    [
        ("GET", "list", {"read": "employees:read"}, "employees:read"),
        ("POST", "create", {"read": "a:read", "write": "a:write"}, "a:write"),
        ("POST", "approve", {"approve": "a:manage", "write": "a:write"}, "a:manage"),
        ("DELETE", "destroy", {"DELETE": "a:delete", "write": "a:write"}, "a:delete"),
        ("GET", "list", {"*": "a:read"}, "a:read"),
        ("GET", "list", {}, None),
    ],
)
def test_required_permission_resolution(method, action, required, expected):
    request = drf_request(method, UserFactory())

    assert (
        HasPermission.required_permission(request, view(action, **required)) == expected
    )


def test_view_without_mapping_denies_by_default(grant):
    user = UserFactory()
    grant(user, "*:*")

    assert not HasPermission().has_permission(drf_request("GET", user), view("list"))


def test_object_permission_respects_unit_scope(grant):
    it = StructuralUnitFactory(name="IT")
    sales = StructuralUnitFactory(name="Sales")
    user = UserFactory()
    grant(user, "employees:read", unit=it)
    request = drf_request("GET", user)
    v = view("retrieve", read="employees:read")

    assert HasPermission().has_permission(request, v)
    assert HasPermission().has_object_permission(
        request, v, SimpleNamespace(structural_unit=it)
    )
    assert not HasPermission().has_object_permission(
        request, v, SimpleNamespace(structural_unit=sales)
    )


def test_unsupported_method_is_left_to_drf_for_405():
    read_only_view = SimpleNamespace(action=None, required_permissions={}, get=handler)

    assert HasPermission().has_permission(
        drf_request("POST", UserFactory()), read_only_view
    )
