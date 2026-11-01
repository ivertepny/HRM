import datetime

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.access.services import grant_default_role
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.equipment.models import Equipment, EquipmentAssignment
from apps.equipment.tests.factories import EquipmentFactory

pytestmark = pytest.mark.django_db

ITEMS = "/api/equipment/items/"
ASSIGNMENTS = "/api/equipment/assignments/"


def days_ago(days):
    return timezone.localdate() - datetime.timedelta(days=days)


@pytest.fixture
def units():
    company = StructuralUnitFactory(name="Company")
    return {
        "it": StructuralUnitFactory(name="IT", parent=company),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


@pytest.fixture
def dev(units, catalog):
    employee = EmployeeFactory(structural_unit=units["it"])
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def seller(units, catalog):
    employee = EmployeeFactory(structural_unit=units["sales"])
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def it_manager(units, grant):
    """Веде обладнання лише в IT."""
    employee = EmployeeFactory(structural_unit=units["it"])
    grant(employee.user, "equipment:read", "equipment:manage", unit=units["it"])
    return employee


@pytest.fixture
def hr(catalog):
    from apps.access.models import Role, UserRole

    employee = EmployeeFactory()
    UserRole.objects.create(
        user=employee.user, role=Role.objects.get(name="HR Manager")
    )
    return employee


def post(client, item, name, **data):
    return client.post(f"{ITEMS}{item.id}/{name}/", data, format="json")


# --- модель ------------------------------------------------------------------


def test_assign_and_return_keep_log_and_holder(dev):
    item = EquipmentFactory()

    item.assign(dev, days_ago(10))
    assert (item.state, item.holder) == (Equipment.State.ASSIGNED, dev)

    item.return_from_holder(days_ago(2))
    assert (item.state, item.holder) == (Equipment.State.IN_STOCK, None)
    log = item.assignments.get()
    assert (log.date_assigned, log.date_returned) == (days_ago(10), days_ago(2))


def test_cannot_assign_held_item(dev, seller):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))

    with pytest.raises(ValidationError, match="на складі"):
        item.assign(seller, days_ago(1))


def test_single_active_assignment_enforced_by_db(dev, seller):
    item = EquipmentFactory()
    EquipmentAssignment.objects.create(
        equipment=item, employee=dev, date_assigned=days_ago(5)
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        EquipmentAssignment.objects.create(
            equipment=item, employee=seller, date_assigned=days_ago(1)
        )


def test_assign_date_not_before_last_return(dev, seller):
    item = EquipmentFactory()
    item.assign(dev, days_ago(10))
    item.return_from_holder(days_ago(3))

    with pytest.raises(ValidationError, match="останнє повернення"):
        item.assign(seller, days_ago(5))
    item.assign(seller, days_ago(3))  # того ж дня — можна


def test_dates_in_future_rejected(dev):
    item = EquipmentFactory()
    with pytest.raises(ValidationError, match="майбутньому"):
        item.assign(dev, timezone.localdate() + datetime.timedelta(days=1))


def test_return_before_assign_rejected(dev):
    item = EquipmentFactory()
    item.assign(dev, days_ago(2))
    with pytest.raises(ValidationError, match="раніше за дату видачі"):
        item.return_from_holder(days_ago(5))


def test_fired_employee_cannot_receive(dev):
    dev.date_fired = days_ago(3)
    dev.save()
    with pytest.raises(ValidationError, match="звільнений"):
        EquipmentFactory().assign(dev, days_ago(1))


def test_write_off_only_from_stock(dev):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))
    with pytest.raises(ValidationError, match="на складі"):
        item.write_off(timezone.localdate())

    item.return_from_holder(timezone.localdate())
    item.write_off(timezone.localdate())
    assert item.state == Equipment.State.WRITTEN_OFF
    with pytest.raises(ValidationError):
        item.assign(dev, timezone.localdate())


def test_item_with_history_is_not_deleted(dev):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))
    item.return_from_holder(timezone.localdate())
    with pytest.raises(ValidationError, match="списати"):
        item.delete()


# --- API: HR ------------------------------------------------------------------


def test_hr_full_cycle(client_as, hr, dev):
    client = client_as(hr.user)

    created = client.post(
        ITEMS,
        {"name": "MacBook Air", "category": "laptop", "serial_number": "C02XYZ"},
        format="json",
    )
    assert created.status_code == 201
    assert created.json()["state"] == "in_stock"
    item = Equipment.objects.get()

    assigned = post(client, item, "assign", employee_id=dev.id, note="Новий працівник")
    assert assigned.status_code == 200
    body = assigned.json()
    assert body["state"] == "assigned"
    assert body["holder"] == {"id": dev.id, "name": str(dev)}
    assert body["held_since"] == timezone.localdate().isoformat()

    returned = post(client, item, "return")
    assert returned.status_code == 200
    assert returned.json()["holder"] is None

    written_off = post(client, item, "write-off")
    assert written_off.json()["state"] == "written_off"

    log = client.get(ASSIGNMENTS, {"equipment": item.id}).json()["results"]
    assert len(log) == 1
    assert log[0]["assigned_by"] == hr.user.email
    assert log[0]["returned_by"] == hr.user.email
    assert log[0]["is_active"] is False


def test_duplicate_serial_number_rejected(client_as, hr):
    EquipmentFactory(serial_number="SN-1")
    response = client_as(hr.user).post(
        ITEMS, {"name": "X", "serial_number": "SN-1"}, format="json"
    )
    assert response.status_code == 400
    assert "serial_number" in response.json()


def test_holder_is_not_writable(client_as, hr, dev):
    item = EquipmentFactory()
    response = client_as(hr.user).patch(
        f"{ITEMS}{item.id}/", {"holder": dev.id, "name": "Renamed"}, format="json"
    )
    assert response.status_code == 200
    item.refresh_from_db()
    assert (item.name, item.holder) == ("Renamed", None)


def test_assign_validation_error_is_400(client_as, hr, dev, seller):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))
    response = post(client_as(hr.user), item, "assign", employee_id=seller.id)
    assert response.status_code == 400


def test_delete_item_with_history_is_400(client_as, hr, dev):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))
    item.return_from_holder(timezone.localdate())
    response = client_as(hr.user).delete(f"{ITEMS}{item.id}/")
    assert response.status_code == 400
    assert Equipment.objects.filter(pk=item.pk).exists()


@pytest.mark.parametrize(
    ("state", "expected"),
    [("in_stock", {"stock"}), ("assigned", {"held"}), ("written_off", {"old"})],
)
def test_filter_by_state(client_as, hr, dev, state, expected):
    EquipmentFactory(name="stock")
    EquipmentFactory(name="held").assign(dev, days_ago(1))
    old = EquipmentFactory(name="old")
    old.write_off(timezone.localdate())

    results = client_as(hr.user).get(ITEMS, {"state": state}).json()["results"]
    assert {r["name"] for r in results} == expected


def test_search_by_serial(client_as, hr):
    EquipmentFactory(name="Dell", serial_number="ABC-123")
    EquipmentFactory(name="HP", serial_number="XYZ-999")
    results = client_as(hr.user).get(ITEMS, {"search": "abc"}).json()["results"]
    assert [r["name"] for r in results] == ["Dell"]


# --- API: доступ ----------------------------------------------------------------


def test_employee_sees_only_own_equipment(client_as, dev, seller):
    EquipmentFactory(name="mine").assign(dev, days_ago(1))
    EquipmentFactory(name="theirs").assign(seller, days_ago(1))
    EquipmentFactory(name="stock")
    client = client_as(dev.user)

    items = client.get(ITEMS).json()["results"]
    assert [i["name"] for i in items] == ["mine"]
    log = client.get(ASSIGNMENTS, {"active": "true"}).json()["results"]
    assert [a["equipment"]["name"] for a in log] == ["mine"]


def test_employee_cannot_manage(client_as, dev):
    item = EquipmentFactory()
    item.assign(dev, days_ago(1))
    client = client_as(dev.user)

    assert client.post(ITEMS, {"name": "X", "serial_number": "1"}).status_code == 403
    assert post(client, item, "return").status_code == 403


def test_scoped_manager_sees_stock_and_own_unit(client_as, it_manager, dev, seller):
    EquipmentFactory(name="stock")
    EquipmentFactory(name="it").assign(dev, days_ago(1))
    EquipmentFactory(name="sales").assign(seller, days_ago(1))

    items = client_as(it_manager.user).get(ITEMS).json()["results"]
    assert {i["name"] for i in items} == {"stock", "it"}


def test_scoped_manager_assigns_only_within_scope(client_as, it_manager, dev, seller):
    client = client_as(it_manager.user)
    item = EquipmentFactory()

    assert post(client, item, "assign", employee_id=seller.id).status_code == 403
    assert post(client, item, "assign", employee_id=dev.id).status_code == 200
    assert post(client, item, "return").status_code == 200


def test_scoped_manager_cannot_touch_other_unit_items(client_as, it_manager, seller):
    item = EquipmentFactory()
    item.assign(seller, days_ago(1))

    response = post(client_as(it_manager.user), item, "return")
    assert response.status_code == 404  # поза scope — не видно взагалі
