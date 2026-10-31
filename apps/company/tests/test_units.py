import pytest

from apps.company.models import StructuralUnit
from apps.company.tests.factories import StructuralUnitFactory

pytestmark = pytest.mark.django_db


def test_create_root_and_child_unit(auth_client):
    root = auth_client.post("/api/company/units/", {"name": "HQ"}, format="json")
    assert root.status_code == 201

    child = auth_client.post(
        "/api/company/units/",
        {"name": "IT", "parent": root.json()["id"]},
        format="json",
    )
    assert child.status_code == 201

    it = StructuralUnit.objects.get(name="IT")
    assert it.parent.name == "HQ"
    assert it.level == 1


def test_cannot_attach_to_inactive_parent(auth_client):
    inactive = StructuralUnitFactory(is_active=False)

    response = auth_client.post(
        "/api/company/units/",
        {"name": "Orphan", "parent": inactive.id},
        format="json",
    )

    assert response.status_code == 400
    assert "parent" in response.json()


def test_delete_is_soft_and_cascades_to_descendants(auth_client):
    root = StructuralUnitFactory(name="HQ")
    child = StructuralUnitFactory(name="IT", parent=root)
    grandchild = StructuralUnitFactory(name="Backend", parent=child)

    response = auth_client.delete(f"/api/company/units/{root.id}/")

    assert response.status_code == 204
    for unit in (root, child, grandchild):
        unit.refresh_from_db()
        assert unit.is_active is False


def test_list_hides_inactive_units(auth_client):
    StructuralUnitFactory(name="Active")
    StructuralUnitFactory(name="Closed", is_active=False)

    response = auth_client.get("/api/company/units/")

    names = [u["name"] for u in response.json()["results"]]
    assert names == ["Active"]


def test_children_endpoint_returns_only_active_direct_children(auth_client):
    root = StructuralUnitFactory(name="HQ")
    StructuralUnitFactory(name="IT", parent=root)
    StructuralUnitFactory(name="Closed", parent=root, is_active=False)

    response = auth_client.get(f"/api/company/units/children/?parent_id={root.id}")

    assert response.status_code == 200
    assert [u["name"] for u in response.json()] == ["IT"]


def test_history_records_author(auth_client, user):
    auth_client.post("/api/company/units/", {"name": "HQ"}, format="json")

    record = StructuralUnit.objects.get(name="HQ").history.first()

    assert record.history_type == "+"
    assert record.history_user == user
