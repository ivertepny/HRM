import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.company.tests.factories import StructuralUnitFactory

pytestmark = pytest.mark.django_db


def count_queries(client, url):
    with CaptureQueriesContext(connection) as ctx:
        response = client.get(url)
    assert response.status_code == 200
    return len(ctx)


def build_tree(width):
    root = StructuralUnitFactory(name="HQ")
    for i in range(width):
        dept = StructuralUnitFactory(name=f"Dept {i}", parent=root)
        StructuralUnitFactory(name=f"Team {i}", parent=dept)
    return root


def test_unit_list_queries_do_not_grow_with_rows(auth_client):
    build_tree(2)
    count_queries(auth_client, "/api/company/units/")  # прогрів
    small = count_queries(auth_client, "/api/company/units/")

    build_tree(8)
    large = count_queries(auth_client, "/api/company/units/")

    assert large == small


def test_children_count_counts_only_active_children(auth_client):
    root = StructuralUnitFactory(name="HQ")
    StructuralUnitFactory(name="IT", parent=root)
    StructuralUnitFactory(name="Sales", parent=root)
    StructuralUnitFactory(name="Closed", parent=root, is_active=False)

    results = auth_client.get("/api/company/units/").json()["results"]

    counts = {u["name"]: u["children_count"] for u in results}
    assert counts == {"HQ": 2, "IT": 0, "Sales": 0}


def test_children_count_and_ancestors_on_create(auth_client):
    root = StructuralUnitFactory(name="HQ")

    body = auth_client.post(
        "/api/company/units/", {"name": "IT", "parent": root.id}, format="json"
    ).json()

    assert body["children_count"] == 0
    assert body["ancestors"] == [
        {"id": root.id, "name": "HQ", "type": root.custom_type}
    ]


def test_list_is_in_tree_order_with_ancestors(auth_client):
    root = StructuralUnitFactory(name="HQ")
    it = StructuralUnitFactory(name="IT", parent=root)
    StructuralUnitFactory(name="Backend", parent=it)

    results = auth_client.get("/api/company/units/").json()["results"]

    assert [u["name"] for u in results] == ["HQ", "IT", "Backend"]
    assert [a["name"] for a in results[2]["ancestors"]] == ["HQ", "IT"]


def test_history_ancestors_include_unit_itself(auth_client):
    root = StructuralUnitFactory(name="HQ")
    it = StructuralUnitFactory(name="IT", parent=root)

    record = auth_client.get(f"/api/company/units/{it.id}/history/").json()[0]

    assert [a["name"] for a in record["ancestors"]] == ["HQ", "IT"]
