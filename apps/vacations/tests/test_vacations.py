import pytest

from apps.access.services import grant_default_role
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.vacations.models import VacationRequest
from apps.vacations.tests.factories import VacationRequestFactory, in_days

pytestmark = pytest.mark.django_db

URL = "/api/vacations/requests/"


@pytest.fixture
def units():
    company = StructuralUnitFactory(name="Company")
    return {
        "it": StructuralUnitFactory(name="IT", parent=company),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


@pytest.fixture
def me(units, catalog):
    """Працівник IT з базовою роллю Employee (vacations:write)."""
    employee = EmployeeFactory(structural_unit=units["it"])
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def hr(units, grant):
    """HR, що веде IT: бачить і розглядає заявки лише цього підрозділу.
    Як і всі, має базову роль Employee (vacations:write)."""
    employee = EmployeeFactory(structural_unit=units["it"])
    grant_default_role(employee.user)
    grant(employee.user, "vacations:read", "vacations:manage", unit=units["it"])
    return employee


def submit(client, start=10, end=14, **extra):
    payload = {
        "vacation_type": "annual",
        "date_start": in_days(start).isoformat(),
        "date_end": in_days(end).isoformat(),
        **extra,
    }
    return client.post(URL, payload, format="json")


def action(client, vacation, name, **data):
    return client.post(f"{URL}{vacation.id}/{name}/", data, format="json")


# --- подання -------------------------------------------------------------------


def test_employee_submits_own_request(client_as, me):
    response = submit(client_as(me.user), comment="Відпочинок")

    assert response.status_code == 201
    body = response.json()
    assert (body["status"], body["days"], body["employee"]["id"]) == (
        "pending",
        5,
        me.id,
    )
    assert body["created_by"] == me.user.email
    assert VacationRequest.objects.get().history.count() == 1


def test_end_before_start_is_rejected(client_as, me):
    response = submit(client_as(me.user), start=10, end=5)

    assert response.status_code == 400
    assert "date_end" in response.json()


@pytest.mark.parametrize(
    ("vacation_type", "expected"), [("annual", 400), ("unpaid", 400), ("sick", 201)]
)
def test_only_sick_leave_can_start_in_the_past(client_as, me, vacation_type, expected):
    response = submit(client_as(me.user), start=-3, end=-1, vacation_type=vacation_type)

    assert response.status_code == expected


def test_overlap_with_active_request_is_rejected(client_as, me):
    client = client_as(me.user)
    submit(client, start=10, end=14)

    response = submit(client, start=14, end=20)

    assert response.status_code == 400


@pytest.mark.parametrize("status", ["rejected", "cancelled"])
def test_overlap_with_closed_request_is_allowed(client_as, me, status):
    VacationRequestFactory(employee=me, status=status)

    assert submit(client_as(me.user)).status_code == 201


def test_fired_employee_cannot_request(client_as, me):
    me.date_fired = in_days(5)
    me.save()

    response = submit(client_as(me.user), start=10, end=12)

    assert response.status_code == 400
    assert "employee" in response.json()


def test_user_without_employee_profile_gets_400(client_as, user, grant):
    grant(user, "vacations:write")

    response = submit(client_as(user))

    assert response.status_code == 400
    assert "employee_id" in response.json()


def test_submit_requires_vacations_write(client_as, units):
    employee = EmployeeFactory(structural_unit=units["it"])

    assert submit(client_as(employee.user)).status_code == 403


def test_hr_registers_sick_leave_for_employee(client_as, hr, me):
    response = submit(
        client_as(hr.user), start=-2, end=1, vacation_type="sick", employee_id=me.id
    )

    assert response.status_code == 201
    vacation = VacationRequest.objects.get()
    assert (vacation.employee, vacation.created_by) == (me, hr.user)


def test_employee_cannot_submit_for_colleague(client_as, me, units):
    colleague = EmployeeFactory(structural_unit=units["it"])

    response = submit(client_as(me.user), employee_id=colleague.id)

    assert response.status_code == 403


def test_scoped_hr_cannot_submit_outside_scope(client_as, hr, units):
    stranger = EmployeeFactory(structural_unit=units["sales"])

    response = submit(client_as(hr.user), employee_id=stranger.id)

    assert response.status_code == 403


# --- розгляд --------------------------------------------------------------------


def test_hr_approves_with_comment(client_as, hr, me):
    vacation = VacationRequestFactory(employee=me)

    response = action(
        client_as(hr.user), vacation, "approve", comment="Гарного відпочинку"
    )

    assert response.status_code == 200
    vacation.refresh_from_db()
    assert vacation.status == "approved"
    assert (vacation.reviewed_by, vacation.decision_comment) == (
        hr.user,
        "Гарного відпочинку",
    )
    assert vacation.reviewed_at is not None


def test_hr_rejects(client_as, hr, me):
    vacation = VacationRequestFactory(employee=me)

    response = action(client_as(hr.user), vacation, "reject", comment="Дедлайн")

    assert response.json()["status"] == "rejected"
    assert response.json()["decision_comment"] == "Дедлайн"


@pytest.mark.parametrize("status", ["approved", "rejected", "cancelled"])
def test_only_pending_can_be_reviewed(client_as, hr, me, status):
    vacation = VacationRequestFactory(employee=me, status=status)

    assert action(client_as(hr.user), vacation, "approve").status_code == 400


def test_cannot_review_own_request(client_as, hr):
    vacation = VacationRequestFactory(employee=hr)

    response = action(client_as(hr.user), vacation, "approve")

    assert response.status_code == 400
    vacation.refresh_from_db()
    assert vacation.status == "pending"


def test_employee_cannot_approve(client_as, me, units):
    colleague_request = VacationRequestFactory(
        employee=EmployeeFactory(structural_unit=units["it"])
    )

    assert action(client_as(me.user), colleague_request, "approve").status_code == 403


def test_scoped_hr_cannot_review_other_units(client_as, hr, units):
    vacation = VacationRequestFactory(
        employee=EmployeeFactory(structural_unit=units["sales"])
    )

    assert action(client_as(hr.user), vacation, "approve").status_code == 404


def test_db_prevents_two_overlapping_approved_periods(client_as, hr, me):
    # Обхід model.clean() — як при гонці двох паралельних запитів
    first = VacationRequestFactory(
        employee=me, date_start=in_days(10), date_end=in_days(14)
    )
    second = VacationRequestFactory(
        employee=me, date_start=in_days(12), date_end=in_days(20)
    )
    client = client_as(hr.user)

    assert action(client, first, "approve").status_code == 200
    assert action(client, second, "approve").status_code == 409
    second.refresh_from_db()
    assert second.status == "pending"


def test_adjacent_periods_can_both_be_approved(client_as, hr, me):
    first = VacationRequestFactory(
        employee=me, date_start=in_days(10), date_end=in_days(14)
    )
    second = VacationRequestFactory(
        employee=me, date_start=in_days(15), date_end=in_days(20)
    )
    client = client_as(hr.user)

    assert action(client, first, "approve").status_code == 200
    assert action(client, second, "approve").status_code == 200


# --- скасування -----------------------------------------------------------------


@pytest.mark.parametrize("status", ["pending", "approved"])
def test_owner_cancels_future_request(client_as, me, status):
    vacation = VacationRequestFactory(employee=me, status=status)

    response = action(client_as(me.user), vacation, "cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_started_approved_vacation_cannot_be_cancelled(client_as, me):
    vacation = VacationRequestFactory(
        employee=me,
        status="approved",
        vacation_type="sick",
        date_start=in_days(-1),
        date_end=in_days(3),
    )

    assert action(client_as(me.user), vacation, "cancel").status_code == 400


def test_hr_can_cancel_employee_request(client_as, hr, me):
    vacation = VacationRequestFactory(employee=me)

    assert action(client_as(hr.user), vacation, "cancel").status_code == 200


def test_hr_with_read_only_cannot_cancel_others(client_as, grant, me, units):
    viewer = EmployeeFactory(structural_unit=units["it"])
    grant(viewer.user, "vacations:read", "vacations:write")
    vacation = VacationRequestFactory(employee=me)

    assert action(client_as(viewer.user), vacation, "cancel").status_code == 403


# --- перегляд -------------------------------------------------------------------


def test_employee_sees_only_own_requests(client_as, me, units):
    own = VacationRequestFactory(employee=me)
    VacationRequestFactory(employee=EmployeeFactory(structural_unit=units["it"]))

    results = client_as(me.user).get(URL).json()["results"]

    assert [r["id"] for r in results] == [own.id]


def test_scoped_hr_sees_unit_requests_only(client_as, hr, me, units):
    in_it = VacationRequestFactory(employee=me)
    VacationRequestFactory(employee=EmployeeFactory(structural_unit=units["sales"]))

    results = client_as(hr.user).get(URL).json()["results"]

    assert [r["id"] for r in results] == [in_it.id]


def test_period_filter_returns_overlapping_requests(auth_client, me):
    inside = VacationRequestFactory(
        employee=me, date_start=in_days(10), date_end=in_days(14)
    )
    VacationRequestFactory(
        employee=me, status="cancelled", date_start=in_days(30), date_end=in_days(35)
    )

    params = f"date_from={in_days(12)}&date_to={in_days(20)}"
    results = auth_client.get(f"{URL}?{params}").json()["results"]

    assert [r["id"] for r in results] == [inside.id]


def test_status_filter(auth_client, me):
    VacationRequestFactory(employee=me, status="rejected")
    pending = VacationRequestFactory(
        employee=me, date_start=in_days(30), date_end=in_days(31)
    )

    results = auth_client.get(f"{URL}?status=pending").json()["results"]

    assert [r["id"] for r in results] == [pending.id]


@pytest.mark.parametrize("method", ["put", "patch", "delete"])
def test_requests_are_immutable(auth_client, me, method):
    vacation = VacationRequestFactory(employee=me)

    response = getattr(auth_client, method)(f"{URL}{vacation.id}/", {}, format="json")

    assert response.status_code == 405
