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


def test_duplicate_name_among_siblings_returns_400(auth_client):
    root = StructuralUnitFactory(name="HQ")
    StructuralUnitFactory(name="IT", parent=root)

    response = auth_client.post(
        "/api/company/units/", {"name": "IT", "parent": root.id}, format="json"
    )

    assert response.status_code == 400
    assert "name" in response.json()


def test_duplicate_root_name_returns_400(auth_client):
    StructuralUnitFactory(name="HQ")

    response = auth_client.post("/api/company/units/", {"name": "HQ"}, format="json")

    assert response.status_code == 400


def test_same_name_under_different_parents_is_allowed(auth_client):
    kyiv = StructuralUnitFactory(name="Kyiv")
    lviv = StructuralUnitFactory(name="Lviv")
    StructuralUnitFactory(name="IT", parent=kyiv)

    response = auth_client.post(
        "/api/company/units/", {"name": "IT", "parent": lviv.id}, format="json"
    )

    assert response.status_code == 201


def test_renaming_unit_to_its_own_name_is_allowed(auth_client):
    unit = StructuralUnitFactory(name="HQ")

    response = auth_client.patch(
        f"/api/company/units/{unit.id}/", {"name": "HQ"}, format="json"
    )

    assert response.status_code == 200


@pytest.mark.parametrize("target", ["self", "descendant"])
def test_cycle_in_tree_returns_400(auth_client, target):
    root = StructuralUnitFactory(name="HQ")
    child = StructuralUnitFactory(name="IT", parent=root)
    new_parent = root if target == "self" else child

    response = auth_client.patch(
        f"/api/company/units/{root.id}/", {"parent": new_parent.id}, format="json"
    )

    assert response.status_code == 400
    assert "parent" in response.json()


def test_depth_limit_is_enforced(auth_client, settings):
    settings.MAX_STRUCTURAL_UNIT_DEPTH = 1
    root = StructuralUnitFactory(name="HQ")
    child = StructuralUnitFactory(name="IT", parent=root)

    response = auth_client.post(
        "/api/company/units/", {"name": "Backend", "parent": child.id}, format="json"
    )

    assert response.status_code == 400
    assert "parent" in response.json()


def test_history_endpoint_returns_change_log(auth_client, user):
    unit_id = auth_client.post(
        "/api/company/units/", {"name": "HQ"}, format="json"
    ).json()["id"]
    auth_client.patch(
        f"/api/company/units/{unit_id}/", {"name": "Head Office"}, format="json"
    )

    response = auth_client.get(f"/api/company/units/{unit_id}/history/")

    assert response.status_code == 200
    updated, created = response.json()
    assert updated["event_type"] == "updated"
    assert updated["history_user"] == user.email
    assert updated["changes"] == [{"field": "name", "old": "HQ", "new": "Head Office"}]
    assert created["event_type"] == "created"


def test_history_limit_must_be_a_number(auth_client):
    unit = StructuralUnitFactory()

    response = auth_client.get(f"/api/company/units/{unit.id}/history/?limit=abc")

    assert response.status_code == 400
