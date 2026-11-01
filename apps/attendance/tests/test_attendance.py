import datetime

import pytest
from django.utils import timezone

from apps.access.models import Role, UserRole
from apps.access.services import grant_default_role
from apps.attendance.models import AttendanceRecord
from apps.attendance.report import build_report
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import Employee
from apps.employees.tests.factories import EmployeeFactory
from apps.vacations.models import VacationRequest

pytestmark = pytest.mark.django_db

URL = "/api/attendance/records/"
REPORT = f"{URL}report/"


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
    employee = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def seller(units, catalog):
    employee = EmployeeFactory(structural_unit=units["sales"], date_hired=None)
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def it_lead(units, grant):
    """Бачить табель лише IT; як і всі, має роль Employee (attendance:write)."""
    employee = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    grant_default_role(employee.user)
    grant(employee.user, "attendance:read", unit=units["it"])
    return employee


def record(employee, days=0, **extra):
    data = {
        "status": "office",
        "time_start": datetime.time(9),
        "time_end": datetime.time(18),
    }
    data.update(extra)
    return AttendanceRecord.objects.create(
        employee=employee, date=days_ago(days), **data
    )


# --- відмітка ------------------------------------------------------------------


def test_mark_today_for_self(client_as, dev):
    response = client_as(dev.user).post(
        URL,
        {"status": "remote", "time_start": "09:00", "time_end": "17:30"},
        format="json",
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["date"], body["hours"], body["employee"]["id"]) == (
        timezone.localdate().isoformat(),
        8.5,
        dev.id,
    )
    assert body["editable"] is True


def test_second_record_for_same_day_rejected(client_as, dev):
    record(dev)
    response = client_as(dev.user).post(URL, {"status": "office"}, format="json")
    assert response.status_code == 400
    assert "date" in response.json()


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        (
            {"date": (timezone.localdate() + datetime.timedelta(days=1)).isoformat()},
            "date",
        ),
        ({"date": days_ago(30).isoformat()}, "date"),
        ({"time_start": "18:00", "time_end": "09:00"}, "time_end"),
        ({"time_end": "18:00"}, "time_start"),
    ],
)
def test_invalid_marks_rejected(client_as, dev, payload, field):
    response = client_as(dev.user).post(
        URL, {"status": "office", **payload}, format="json"
    )
    assert response.status_code == 400
    assert field in response.json()


def test_off_day_drops_times(client_as, dev):
    response = client_as(dev.user).post(
        URL,
        {"status": "off", "time_start": "09:00", "time_end": "18:00"},
        format="json",
    )
    assert response.status_code == 201
    assert (response.json()["time_start"], response.json()["hours"]) == (None, None)


def test_cannot_mark_after_firing(client_as, dev):
    dev.date_fired = days_ago(2)
    dev.save()
    response = client_as(dev.user).post(URL, {"status": "office"}, format="json")
    assert response.status_code == 400


def test_user_without_employee_profile(client_as, user, catalog):
    grant_default_role(user)
    response = client_as(user).post(URL, {"status": "office"}, format="json")
    assert response.status_code == 400


def test_close_day_by_setting_end_time(client_as, dev):
    mark = record(dev, time_end=None)
    response = client_as(dev.user).patch(
        f"{URL}{mark.id}/", {"time_end": "18:00"}, format="json"
    )
    assert response.status_code == 200
    assert response.json()["hours"] == 9.0


def test_old_record_is_locked(client_as, dev):
    mark = record(dev, days=20)
    client = client_as(dev.user)

    assert (
        client.patch(
            f"{URL}{mark.id}/", {"status": "remote"}, format="json"
        ).status_code
        == 400
    )
    assert client.delete(f"{URL}{mark.id}/").status_code == 400


def test_date_cannot_be_moved(client_as, dev):
    mark = record(dev, days=1)
    response = client_as(dev.user).patch(
        f"{URL}{mark.id}/", {"date": days_ago(2).isoformat()}, format="json"
    )
    assert response.status_code == 400


# --- доступ --------------------------------------------------------------------


def test_employee_sees_only_own(client_as, dev, seller):
    record(dev)
    record(seller)
    results = client_as(dev.user).get(URL).json()["results"]
    assert [r["employee"]["id"] for r in results] == [dev.id]


def test_lead_sees_unit_but_cannot_edit_others(client_as, it_lead, dev, seller):
    mine = record(dev)
    record(seller)
    client = client_as(it_lead.user)

    results = client.get(URL).json()["results"]
    assert {r["employee"]["id"] for r in results} == {dev.id}
    response = client.patch(f"{URL}{mine.id}/", {"status": "off"}, format="json")
    assert response.status_code == 403


def test_employee_cannot_open_report(client_as, dev):
    assert client_as(dev.user).get(REPORT).status_code == 403


# --- звіт ----------------------------------------------------------------------


def test_report_counts_statuses_vacation_and_missing(units, catalog):
    employee = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    # Листопад 2026: 1-ше — неділя, 2–6 — пн–пт
    AttendanceRecord.objects.create(
        employee=employee,
        date=datetime.date(2026, 11, 2),
        status="office",
        time_start=datetime.time(9),
        time_end=datetime.time(18),
    )
    AttendanceRecord.objects.create(
        employee=employee,
        date=datetime.date(2026, 11, 3),
        status="remote",
        time_start=datetime.time(10),
        time_end=datetime.time(14, 30),
    )
    VacationRequest.objects.create(
        employee=employee,
        date_start=datetime.date(2026, 11, 5),
        date_end=datetime.date(2026, 11, 8),  # чт–нд: робочих 2
        status=VacationRequest.Status.APPROVED,
    )

    report = build_report(
        Employee.objects.filter(pk=employee.pk),
        datetime.date(2026, 11, 1),
        today=datetime.date(2026, 11, 6),
    )

    assert (report["month"], report["working_days"]) == ("2026-11", 21)
    row = report["rows"][0]
    assert (row["office"], row["remote"], row["vacation"], row["hours"]) == (
        1,
        1,
        2,
        13.5,
    )
    assert row["missing"] == 1  # 4 листопада: без відмітки і не у відпустці


def test_report_api_respects_scope_and_unit(client_as, it_lead, dev, seller, units):
    record(dev)
    response = client_as(it_lead.user).get(REPORT)

    assert response.status_code == 200
    ids = {row["employee"]["id"] for row in response.json()["rows"]}
    assert ids == {dev.id, it_lead.id}


def test_report_hr_filters_by_unit(client_as, dev, seller, units, catalog):
    hr = EmployeeFactory()
    UserRole.objects.create(user=hr.user, role=Role.objects.get(name="HR Manager"))

    rows = client_as(hr.user).get(REPORT, {"unit": units["sales"].id}).json()["rows"]
    assert [row["employee"]["id"] for row in rows] == [seller.id]


def test_report_rejects_bad_month(client_as, it_lead):
    assert client_as(it_lead.user).get(REPORT, {"month": "11/2026"}).status_code == 400
