import datetime

import httpx
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.access.services import grant_default_role
from apps.attendance.models import AttendanceRecord, Holiday
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.tests.factories import EmployeeFactory
from apps.slack import client, reminders
from apps.vacations.models import VacationRequest
from apps.vacations.tests.factories import VacationRequestFactory, in_days

pytestmark = pytest.mark.django_db

VACATIONS = "/api/vacations/requests/"
MONDAY = datetime.date(2026, 11, 2)


class FakeSlack:
    """Підміна Slack Web API: хто в workspace, що надіслано."""

    def __init__(self):
        self.messages = []  # (email, text)
        self.lookups = []
        self.missing = set()
        self.fail_with = None
        self._ids = {}

    def post(self, url, headers=None, json=None, data=None, timeout=None):
        method = url.rsplit("/", 1)[-1]
        assert headers["Authorization"] == "Bearer xoxb-test"
        if self.fail_with:
            return self._response({"ok": False, "error": self.fail_with})
        if method == "users.lookupByEmail":
            email = data["email"]
            self.lookups.append(email)
            if email in self.missing:
                return self._response({"ok": False, "error": "users_not_found"})
            user_id = f"U{len(self._ids) + 1}"
            self._ids[user_id] = email
            return self._response({"ok": True, "user": {"id": user_id}})
        if method == "chat.postMessage":
            self.messages.append((self._ids[json["channel"]], json["text"]))
            return self._response({"ok": True})
        raise AssertionError(f"unexpected Slack method {method}")

    @staticmethod
    def _response(body):
        return httpx.Response(
            200, json=body, request=httpx.Request("POST", "https://x")
        )

    def to(self, email):
        return [text for address, text in self.messages if address == email]


@pytest.fixture
def slack(settings, monkeypatch):
    settings.SLACK_BOT_TOKEN = "xoxb-test"
    fake = FakeSlack()
    monkeypatch.setattr(client.httpx, "post", fake.post)
    return fake


@pytest.fixture
def units():
    company = StructuralUnitFactory(name="Company")
    it = StructuralUnitFactory(name="IT", parent=company)
    return {
        "company": company,
        "it": it,
        "backend": StructuralUnitFactory(name="Backend", parent=it),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


@pytest.fixture
def dev(units, catalog):
    employee = EmployeeFactory(structural_unit=units["backend"], date_hired=None)
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def approvers(units, grant):
    """HR на всю компанію, керівник IT (предок Backend) і керівник Sales."""
    hr = EmployeeFactory(structural_unit=units["company"]).user
    it_lead = EmployeeFactory(structural_unit=units["it"]).user
    sales_lead = EmployeeFactory(structural_unit=units["sales"]).user
    grant(hr, "vacations:*")
    grant(it_lead, "vacations:*", unit=units["it"])
    grant(sales_lead, "vacations:manage", unit=units["sales"])
    return {"hr": hr, "it_lead": it_lead, "sales_lead": sales_lead}


def submit(api, **extra):
    payload = {"date_start": in_days(10), "date_end": in_days(12), **extra}
    return api.post(VACATIONS, payload, format="json")


# --- клієнт ------------------------------------------------------------------------


def test_disabled_without_token(settings, monkeypatch):
    settings.SLACK_BOT_TOKEN = ""
    monkeypatch.setattr(client.httpx, "post", lambda *a, **k: pytest.fail("HTTP call"))
    assert client.send_dm("olena@example.com", "hi") is False


def test_slack_user_lookup_is_cached(slack):
    client.send_dm("olena@example.com", "1")
    client.send_dm("OLENA@example.com", "2")

    assert slack.lookups == ["olena@example.com"]
    assert len(slack.messages) == 2


def test_person_not_in_workspace_is_skipped(slack):
    slack.missing.add("guest@example.com")

    assert client.send_dm("guest@example.com", "hi") is False
    assert client.send_dm("guest@example.com", "hi") is False
    assert slack.lookups == ["guest@example.com"]  # «не знайдено» теж кешується


def test_slack_errors_never_raise(slack, caplog):
    slack.fail_with = "invalid_auth"
    assert client.send_dm("olena@example.com", "hi") is False
    assert "Slack" in caplog.text


# --- відпустки ----------------------------------------------------------------------


def test_new_request_goes_to_everyone_who_can_review_it(
    client_as, slack, dev, approvers, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        assert submit(client_as(dev.user)).status_code == 201

    notified = {address for address, _ in slack.messages}
    assert notified == {approvers["hr"].email, approvers["it_lead"].email}
    [text] = slack.to(approvers["hr"].email)
    assert str(dev) in text
    assert "http://localhost:3000/vacations/review" in text


def test_nothing_is_sent_when_request_fails(
    client_as, slack, dev, approvers, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        assert submit(client_as(dev.user), date_end=in_days(5)).status_code == 400
    assert slack.messages == []


def test_hr_submitting_for_employee_notifies_employee_not_hr(
    client_as, slack, dev, approvers, django_capture_on_commit_callbacks
):
    hr = approvers["hr"]
    with django_capture_on_commit_callbacks(execute=True):
        response = submit(client_as(hr), employee_id=dev.pk, vacation_type="sick")
    assert response.status_code == 201

    assert slack.to(hr.email) == []
    assert "оформив(-ла) для вас" in slack.to(dev.user.email)[0]
    assert slack.to(approvers["it_lead"].email)  # керівник усе одно бачить


def test_decision_and_cancellation_reach_the_employee(
    client_as, slack, dev, approvers, django_capture_on_commit_callbacks
):
    approved = VacationRequestFactory(employee=dev)
    other = VacationRequestFactory(
        employee=dev, date_start=in_days(30), date_end=in_days(31)
    )
    hr = client_as(approvers["hr"])

    with django_capture_on_commit_callbacks(execute=True):
        hr.post(f"{VACATIONS}{approved.id}/approve/", {}, format="json")
        hr.post(f"{VACATIONS}{other.id}/cancel/", {}, format="json")

    first, second = slack.to(dev.user.email)
    assert "схвалено" in first
    assert "скасовано" in second


def test_own_cancellation_is_silent(
    client_as, slack, dev, django_capture_on_commit_callbacks
):
    vacation = VacationRequestFactory(employee=dev)
    with django_capture_on_commit_callbacks(execute=True):
        client_as(dev.user).post(f"{VACATIONS}{vacation.id}/cancel/", {}, format="json")
    assert slack.messages == []


def test_markup_in_names_is_escaped(
    client_as, slack, dev, approvers, django_capture_on_commit_callbacks
):
    dev.user.last_name = "<!channel>"
    dev.user.save()
    with django_capture_on_commit_callbacks(execute=True):
        submit(client_as(dev.user))
    [text] = slack.to(approvers["hr"].email)
    assert "<!channel>" not in text
    assert "&lt;!channel&gt;" in text


# --- запрошення --------------------------------------------------------------------


def test_invite_is_duplicated_in_slack(
    auth_client, slack, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        auth_client.post(
            "/api/users/register/", {"email": "new@example.com"}, format="json"
        )
    [text] = slack.to("new@example.com")
    assert "http://localhost:3000/invite?uid=" in text


# --- нагадування -------------------------------------------------------------------


def test_attendance_reminder_only_for_those_who_should_mark(slack, units, catalog):
    unmarked = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    marked = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    resting = EmployeeFactory(structural_unit=units["it"], date_hired=None)
    fired = EmployeeFactory(
        structural_unit=units["it"],
        date_hired=None,
        date_fired=MONDAY - datetime.timedelta(days=3),
    )
    AttendanceRecord.objects.create(employee=marked, date=MONDAY, status="office")
    VacationRequest.objects.create(
        employee=resting,
        date_start=MONDAY,
        date_end=MONDAY,
        status=VacationRequest.Status.APPROVED,
    )

    assert reminders.remind_attendance(today=MONDAY) == 1
    assert [address for address, _ in slack.messages] == [unmarked.user.email]
    assert fired.user.email not in {a for a, _ in slack.messages}
    # Повторний запуск cron того ж дня — без дублів
    assert reminders.remind_attendance(today=MONDAY) == 0


def test_no_attendance_reminder_on_weekend_or_holiday(slack, units, catalog):
    EmployeeFactory(structural_unit=units["it"], date_hired=None)
    Holiday.objects.create(date=MONDAY, name="Свято")

    assert reminders.remind_attendance(today=MONDAY) == 0
    assert reminders.remind_attendance(today=MONDAY - datetime.timedelta(days=1)) == 0
    assert slack.messages == []


def test_pending_reminder_counts_only_reviewable_requests(slack, dev, approvers, units):
    VacationRequestFactory(employee=dev)  # Backend — видно HR і керівнику IT
    seller = EmployeeFactory(structural_unit=units["sales"])
    VacationRequestFactory(employee=seller)
    # Власна заявка керівника IT — сам він її не розглядає
    own = approvers["it_lead"].employee_profile
    VacationRequestFactory(employee=own)

    reminders.remind_pending_vacations()

    assert "*3*" in slack.to(approvers["hr"].email)[0]
    assert "*1*" in slack.to(approvers["it_lead"].email)[0]
    assert "*1*" in slack.to(approvers["sales_lead"].email)[0]


def test_command_requires_a_kind_and_a_token(settings, capsys):
    with pytest.raises(CommandError):
        call_command("slack_reminders")
    settings.SLACK_BOT_TOKEN = ""
    call_command("slack_reminders", "--attendance")
    assert "вимкнені" in capsys.readouterr().out
