import datetime
from unittest.mock import patch

import pytest
from graphviz import ExecutableNotFound

from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tree():
    company = StructuralUnitFactory(name="Company")
    it = StructuralUnitFactory(name="IT", parent=company)
    return {
        "company": company,
        "it": it,
        "backend": StructuralUnitFactory(name="Backend", parent=it),
        "frontend": StructuralUnitFactory(name="Frontend", parent=it),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


def test_tree_returns_all_units_unpaginated_in_tree_order(auth_client, tree):
    for i in range(25):
        StructuralUnitFactory(name=f"Team {i:02}", parent=tree["sales"])

    response = auth_client.get("/api/company/units/tree/")

    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 30
    assert [u["name"] for u in body[:5]] == [
        "Company",
        "IT",
        "Backend",
        "Frontend",
        "Sales",
    ]


def test_tree_respects_scope(client_as, user, grant, tree):
    grant(user, "company:read", unit=tree["it"])

    names = [u["name"] for u in client_as(user).get("/api/company/units/tree/").json()]

    assert names == ["IT", "Backend", "Frontend"]


def test_counts_are_not_multiplied_by_joins(auth_client, tree):
    EmployeeFactory.create_batch(3, structural_unit=tree["it"])
    EmployeeFactory(structural_unit=tree["it"], date_fired=datetime.date(2020, 1, 1))
    EmployeeFactory(structural_unit=tree["backend"])

    units = {u["name"]: u for u in auth_client.get("/api/company/units/tree/").json()}

    assert (units["IT"]["children_count"], units["IT"]["employees_count"]) == (2, 3)
    assert (
        units["Backend"]["children_count"],
        units["Backend"]["employees_count"],
    ) == (0, 1)


def test_employees_count_on_create_response(auth_client, tree):
    body = auth_client.post(
        "/api/company/units/", {"name": "QA", "parent": tree["it"].id}, format="json"
    ).json()

    assert (body["employees_count"], body["children_count"]) == (0, 0)


def test_diagram_returns_svg(auth_client, tree):
    with patch("apps.company.views.Digraph.pipe", return_value=b"<svg/>"):
        response = auth_client.get(f"/api/company/units/{tree['it'].id}/diagram/")

    assert response.status_code == 200
    assert response["Content-Type"] == "image/svg+xml"


def test_diagram_without_graphviz_returns_503(auth_client, tree):
    with patch(
        "apps.company.views.Digraph.pipe", side_effect=ExecutableNotFound(["dot"])
    ):
        response = auth_client.get(f"/api/company/units/{tree['it'].id}/diagram/")

    assert response.status_code == 503
    assert "Graphviz" in response.json()["detail"]


def test_unit_with_working_employees_cannot_be_closed(auth_client, tree):
    EmployeeFactory(structural_unit=tree["backend"])

    response = auth_client.delete(f"/api/company/units/{tree['it'].id}/")

    assert response.status_code == 400
    assert "працівники (1)" in response.json()["detail"]
    tree["it"].refresh_from_db()
    assert tree["it"].is_active


def test_unit_with_only_dismissed_employees_can_be_closed(auth_client, tree):
    EmployeeFactory(
        structural_unit=tree["backend"], date_fired=datetime.date(2020, 1, 1)
    )

    assert auth_client.delete(f"/api/company/units/{tree['it'].id}/").status_code == 204
