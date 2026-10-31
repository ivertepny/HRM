from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.ai_assistant.models import AIQuery
from apps.ai_assistant.openai_service import is_structure_query
from apps.company.tests.factories import StructuralUnitFactory


def fake_completion(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Покажи структуру компанії", True),
        ("Який відділ займається продажами?", True),
        ("Скільки днів відпустки мені належить?", False),
    ],
)
def test_is_structure_query(prompt, expected):
    assert is_structure_query(prompt) is expected


@pytest.mark.django_db
@patch("apps.ai_assistant.openai_service.client")
def test_structure_question_is_answered_from_db_without_openai(client, auth_client):
    root = StructuralUnitFactory(name="HQ", custom_type="Офіс")
    StructuralUnitFactory(name="IT", custom_type="Департамент", parent=root)

    response = auth_client.post(
        "/api/ai/chat/", {"message": "Яка структура компанії?"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Офіс: HQ\n  Департамент: IT"
    client.chat.completions.create.assert_not_called()


@pytest.mark.django_db
@patch("apps.ai_assistant.openai_service.client")
def test_regular_question_goes_to_openai_and_is_stored(client, auth_client, user):
    client.chat.completions.create.return_value = fake_completion("24 дні")

    response = auth_client.post(
        "/api/ai/chat/", {"message": "Скільки днів відпустки?"}, format="json"
    )

    assert response.status_code == 200
    assert response.json()["response"] == "24 дні"
    query = AIQuery.objects.get(user=user)
    assert (query.message, query.response) == ("Скільки днів відпустки?", "24 дні")
