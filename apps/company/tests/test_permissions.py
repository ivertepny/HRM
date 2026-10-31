import pytest

from apps.company.tests.factories import StructuralUnitFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def tree():
    company = StructuralUnitFactory(name="Company")
    it = StructuralUnitFactory(name="IT", parent=company)
    return {
        "company": company,
        "it": it,
        "backend": StructuralUnitFactory(name="Backend", parent=it),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


def names(response):
    return {u["name"] for u in response.json()["results"]}


def test_structure_requires_company_read(client_as, user, grant, tree):
    assert client_as(user).get("/api/company/units/").status_code == 403

    grant(user, "company:read")

    assert names(client_as(user).get("/api/company/units/")) == {
        "Company",
        "IT",
        "Backend",
        "Sales",
    }


def test_scoped_read_shows_only_subtree(client_as, user, grant, tree):
    grant(user, "company:read", unit=tree["it"])

    assert names(client_as(user).get("/api/company/units/")) == {"IT", "Backend"}


def test_employee_role_can_read_structure(client_as, user, catalog, tree):
    from apps.access.services import grant_default_role

    grant_default_role(user)

    assert client_as(user).get("/api/company/units/").status_code == 200


def test_read_only_cannot_create_units(client_as, user, grant):
    grant(user, "company:read")

    response = client_as(user).post(
        "/api/company/units/", {"name": "New"}, format="json"
    )

    assert response.status_code == 403


def test_scoped_write_can_add_children_only_inside_scope(client_as, user, grant, tree):
    grant(user, "company:read", "company:write", unit=tree["it"])
    client = client_as(user)

    inside = client.post(
        "/api/company/units/", {"name": "QA", "parent": tree["it"].id}, format="json"
    )
    outside = client.post(
        "/api/company/units/", {"name": "QA", "parent": tree["sales"].id}, format="json"
    )
    root = client.post("/api/company/units/", {"name": "Holding"}, format="json")

    assert inside.status_code == 201
    assert outside.status_code == 403
    assert root.status_code == 403


def test_scoped_write_cannot_move_unit_out_of_scope(client_as, user, grant, tree):
    grant(user, "company:read", "company:write", unit=tree["it"])

    response = client_as(user).patch(
        f"/api/company/units/{tree['backend'].id}/",
        {"parent": tree["sales"].id},
        format="json",
    )

    assert response.status_code == 403


def test_delete_requires_company_delete(client_as, user, grant, tree):
    grant(user, "company:read", "company:write")
    client = client_as(user)

    assert client.delete(f"/api/company/units/{tree['sales'].id}/").status_code == 403

    grant(user, "company:delete")
    assert (
        client_as(user).delete(f"/api/company/units/{tree['sales'].id}/").status_code
        == 204
    )
