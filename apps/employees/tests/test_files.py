import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.employees.models import EmployeeDocument
from apps.employees.tests.factories import EmployeeFactory

pytestmark = pytest.mark.django_db


def png_file(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def pdf_file(name="cv.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 test", content_type="application/pdf")


def upload_document(client, employee, file, **extra):
    return client.post(
        "/api/employees/documents/",
        {"employee": employee.id, "document_type": "cv", "file": file, **extra},
        format="multipart",
    )


def test_upload_photo(auth_client, media_root):
    employee = EmployeeFactory()

    response = auth_client.patch(
        f"/api/employees/employees/{employee.id}/",
        {"photo": png_file()},
        format="multipart",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.photo.name.startswith("employees/photos/")
    assert employee.photo.name.endswith(".png")
    assert "photo.png" not in employee.photo.name  # ім'я файлу замінено на UUID
    assert (media_root / employee.photo.name).exists()
    assert response.json()["photo"].endswith(employee.photo.name)


def test_photo_must_be_an_image(auth_client):
    employee = EmployeeFactory()

    response = auth_client.patch(
        f"/api/employees/employees/{employee.id}/",
        {"photo": pdf_file("fake.png")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "photo" in response.json()


def test_upload_document_records_uploader(auth_client, user):
    employee = EmployeeFactory()

    response = upload_document(auth_client, employee, pdf_file(), title="CV 2026")

    assert response.status_code == 201
    document = EmployeeDocument.objects.get(pk=response.json()["id"])
    assert document.uploaded_by == user
    assert document.file.name.startswith(f"employees/{employee.id}/documents/")
    assert response.json()["uploaded_by"] == user.email


def test_document_extension_is_validated(auth_client):
    employee = EmployeeFactory()

    response = upload_document(
        auth_client, employee, SimpleUploadedFile("script.exe", b"MZ")
    )

    assert response.status_code == 400
    assert "file" in response.json()


def test_document_size_is_limited(auth_client, settings):
    settings.MAX_UPLOAD_SIZE_MB = 0
    employee = EmployeeFactory()

    response = upload_document(auth_client, employee, pdf_file())

    assert response.status_code == 400
    assert "file" in response.json()


def test_delete_document_removes_file(auth_client, media_root):
    employee = EmployeeFactory()
    document_id = upload_document(auth_client, employee, pdf_file()).json()["id"]
    path = media_root / EmployeeDocument.objects.get(pk=document_id).file.name

    response = auth_client.delete(f"/api/employees/documents/{document_id}/")

    assert response.status_code == 204
    assert not path.exists()


def test_documents_filter_by_employee(auth_client):
    first, second = EmployeeFactory(), EmployeeFactory()
    upload_document(auth_client, first, pdf_file())
    upload_document(auth_client, second, pdf_file())

    response = auth_client.get(f"/api/employees/documents/?employee={first.id}")

    assert [d["employee"] for d in response.json()["results"]] == [first.id]
