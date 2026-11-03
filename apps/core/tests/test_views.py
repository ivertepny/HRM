import os
import subprocess
import sys

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.access.services import grant_default_role
from apps.company.tests.factories import StructuralUnitFactory
from apps.employees.models import EmployeeDocument
from apps.employees.tests.factories import EmployeeFactory

pytestmark = pytest.mark.django_db


# --- health ----------------------------------------------------------------------


def test_health_is_public(api_client):
    response = api_client.get("/api/health/")
    assert (response.status_code, response.json()) == (200, {"status": "ok"})


def test_health_reports_broken_cache(api_client, monkeypatch):
    from django.core.cache import cache

    monkeypatch.setattr(cache, "get", lambda *args, **kwargs: None)
    assert api_client.get("/api/health/").status_code == 503


# --- media -----------------------------------------------------------------------


@pytest.fixture
def units():
    company = StructuralUnitFactory(name="Company")
    return {
        "it": StructuralUnitFactory(name="IT", parent=company),
        "sales": StructuralUnitFactory(name="Sales", parent=company),
    }


@pytest.fixture
def owner(units, catalog):
    employee = EmployeeFactory(structural_unit=units["it"])
    grant_default_role(employee.user)
    return employee


@pytest.fixture
def document(owner):
    return EmployeeDocument.objects.create(
        employee=owner,
        file=SimpleUploadedFile("cv.pdf", b"%PDF-1.4 test"),
    )


def media_url(name):
    return f"/media/{name}"


def test_owner_downloads_own_document(client_as, owner, document):
    response = client_as(owner.user).get(media_url(document.file.name))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Cache-Control"] == "private, no-store"
    assert b"".join(response.streaming_content) == b"%PDF-1.4 test"


def test_colleague_without_permission_gets_404(client_as, units, catalog, document):
    colleague = EmployeeFactory(structural_unit=units["it"])
    grant_default_role(colleague.user)

    response = client_as(colleague.user).get(media_url(document.file.name))
    assert response.status_code == 404


def test_document_scope_is_respected(client_as, units, grant, document):
    it_hr = EmployeeFactory(structural_unit=units["it"]).user
    sales_hr = EmployeeFactory(structural_unit=units["sales"]).user
    grant(it_hr, "documents:read", unit=units["it"])
    grant(sales_hr, "documents:read", unit=units["sales"])

    assert client_as(it_hr).get(media_url(document.file.name)).status_code == 200
    assert client_as(sales_hr).get(media_url(document.file.name)).status_code == 404


def test_photo_follows_employee_visibility(client_as, units, grant, owner):
    owner.photo = SimpleUploadedFile("me.png", b"\x89PNG fake")
    owner.save()
    viewer = EmployeeFactory(structural_unit=units["sales"]).user
    url = media_url(owner.photo.name)

    assert client_as(owner.user).get(url).status_code == 200
    assert client_as(viewer).get(url).status_code == 404
    grant(viewer, "employees:read")
    assert client_as(viewer).get(url).status_code == 200


def test_media_requires_login(api_client, document):
    assert api_client.get(media_url(document.file.name)).status_code == 401


def test_unknown_or_unlisted_file_is_404(client_as, admin_user, media_root):
    (media_root / "stray.txt").parent.mkdir(parents=True, exist_ok=True)
    (media_root / "stray.txt").write_text("x")
    client = client_as(admin_user)

    assert client.get("/media/stray.txt").status_code == 404
    assert client.get("/media/employees/1/documents/nope.pdf").status_code == 404


# --- prod settings ---------------------------------------------------------------


def test_prod_settings_pass_deploy_check():
    """`check --deploy` з шаблоном .env.production.example — без попереджень."""
    env = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.prod",
        "SECRET_KEY": "x" * 60 + "-not-a-real-secret-but-long-and-varied-0123456789",
        "ALLOWED_HOSTS": "api",
        "EMAIL_HOST": "smtp.example.com",
        "DEFAULT_FROM_EMAIL": "HRM <hr@example.com>",
        "FRONTEND_URL": "https://hrm.example.com",
    }
    # Порожні, а не відсутні: інакше їх підставить локальний .env
    for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        env[name] = ""
    result = subprocess.run(
        [sys.executable, "manage.py", "check", "--deploy", "--fail-level", "WARNING"],
        cwd=settings.BASE_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


# --- sentry ----------------------------------------------------------------------


def test_sentry_disabled_without_dsn(monkeypatch):
    from apps.core import sentry

    calls = []
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kw: calls.append(kw))
    assert sentry.configure_sentry("") is False
    assert calls == []


def test_sentry_never_sends_personal_data(monkeypatch):
    from apps.core import sentry

    calls = []
    monkeypatch.setattr(sentry.sentry_sdk, "init", lambda **kw: calls.append(kw))
    assert sentry.configure_sentry("https://k@o.ingest.sentry.io/1", release="abc")

    options = calls[0]
    assert options["send_default_pii"] is False
    assert options["max_request_body_size"] == "never"
    assert options["include_local_variables"] is False
    assert options["release"] == "abc"
