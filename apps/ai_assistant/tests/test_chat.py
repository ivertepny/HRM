import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import openai
import pytest

from apps.ai_assistant import openai_service
from apps.ai_assistant.models import AIQuery, ChatSession
from apps.ai_assistant.openai_service import is_structure_query
from apps.company.tests.factories import StructuralUnitFactory

CHAT_URL = "/api/ai/chat/"


def fake_completion(content):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


@pytest.fixture
def llm():
    """Мок OpenAI-клієнта; llm.reply("...") задає відповідь моделі."""
    client = MagicMock()
    client.reply = lambda text: setattr(
        client.chat.completions.create, "return_value", fake_completion(text)
    )
    client.reply("Відповідь")
    with patch.object(openai_service, "get_client", return_value=client):
        yield client


def sent_messages(llm):
    return llm.chat.completions.create.call_args.kwargs["messages"]


def ask(client, message, **extra):
    return client.post(CHAT_URL, {"message": message, **extra}, format="json")


@pytest.mark.parametrize(
    ("prompt", "expected"),
    [
        ("Покажи структуру компанії", True),
        ("Який відділ займається продажами?", True),
        ("Скільки днів відпустки мені належить у компанії?", False),
    ],
)
def test_is_structure_query(prompt, expected):
    assert is_structure_query(prompt) is expected


# --- розмова -------------------------------------------------------------------


@pytest.mark.django_db
def test_first_message_creates_session(auth_client, admin_user, llm):
    llm.reply("24 дні")

    response = ask(
        auth_client, "Скільки днів відпустки?", chat_session_name="Відпустки"
    )

    assert response.status_code == 200
    body = response.json()
    session = ChatSession.objects.get(user=admin_user)
    assert body["session_id"] == str(session.session_id)
    assert body["response"] == "24 дні"
    assert session.name == "Відпустки"
    query = AIQuery.objects.get(chat_session=session)
    assert (query.message, query.response, query.source) == (
        "Скільки днів відпустки?",
        "24 дні",
        "openai",
    )


@pytest.mark.django_db
def test_session_id_continues_conversation_with_history(auth_client, llm):
    llm.reply("Перша відповідь")
    session_id = ask(auth_client, "Перше питання").json()["session_id"]

    llm.reply("Друга відповідь")
    response = ask(auth_client, "Друге питання", session_id=session_id)

    assert response.json()["session_id"] == session_id
    assert ChatSession.objects.count() == 1
    assert [m["content"] for m in sent_messages(llm)[1:]] == [
        "Перше питання",
        "Перша відповідь",
        "Друге питання",
    ]


@pytest.mark.django_db
def test_without_session_id_each_message_starts_new_session(auth_client, llm):
    ask(auth_client, "Раз")
    ask(auth_client, "Два")

    assert ChatSession.objects.count() == 2
    assert len(sent_messages(llm)) == 2  # system + питання, без чужої історії


@pytest.mark.django_db
def test_history_is_limited_to_max_history(auth_client, llm, settings):
    settings.MAX_HISTORY_AI = 2
    session_id = ask(auth_client, "q1").json()["session_id"]
    for prompt in ("q2", "q3"):
        ask(auth_client, prompt, session_id=session_id)

    ask(auth_client, "q4", session_id=session_id)

    user_messages = [m["content"] for m in sent_messages(llm) if m["role"] == "user"]
    assert user_messages == ["q2", "q3", "q4"]


@pytest.mark.django_db
def test_structure_answers_are_not_sent_to_model_as_history(auth_client, llm):
    StructuralUnitFactory(name="HQ")
    session_id = ask(auth_client, "Покажи структуру").json()["session_id"]

    ask(auth_client, "Дякую", session_id=session_id)

    assert [m["content"] for m in sent_messages(llm)[1:]] == ["Дякую"]


@pytest.mark.django_db
def test_foreign_session_id_returns_404(client_as, auth_client, user, grant, llm):
    foreign = ask(auth_client, "Моє").json()["session_id"]
    grant(user, "ai:use")

    response = ask(client_as(user), "Чуже", session_id=foreign)

    assert response.status_code == 404


@pytest.mark.django_db
def test_unknown_session_id_returns_404(auth_client, llm):
    assert ask(auth_client, "Привіт", session_id=str(uuid.uuid4())).status_code == 404


@pytest.mark.django_db
def test_too_long_message_returns_400_without_calling_model(auth_client, llm, settings):
    settings.MAX_TOKENS_INPUT_AI = 3

    response = ask(auth_client, "дуже довге повідомлення про відпустку")

    assert response.status_code == 400
    assert "message" in response.json()
    llm.chat.completions.create.assert_not_called()
    assert not AIQuery.objects.exists()


@pytest.mark.django_db
def test_openai_failure_returns_503_and_stores_nothing(auth_client, llm):
    llm.chat.completions.create.side_effect = openai.OpenAIError("boom")

    response = ask(auth_client, "Привіт")

    assert response.status_code == 503
    assert "boom" not in str(response.json())
    assert not AIQuery.objects.exists()


@pytest.mark.django_db
def test_missing_api_key_returns_503(auth_client, settings):
    settings.OPENAI_API_KEY = ""
    openai_service.get_client.cache_clear()
    try:
        response = ask(auth_client, "Привіт")
    finally:
        openai_service.get_client.cache_clear()

    assert response.status_code == 503


# --- оргструктура -------------------------------------------------------------


@pytest.mark.django_db
def test_structure_question_is_answered_from_db_without_openai(auth_client, llm):
    root = StructuralUnitFactory(name="HQ", custom_type="Офіс")
    StructuralUnitFactory(name="IT", custom_type="Департамент", parent=root)

    response = ask(auth_client, "Яка структура компанії?")

    assert response.json()["response"] == "Офіс: HQ\n  Департамент: IT"
    assert response.json()["query"]["source"] == "company_structure"
    llm.chat.completions.create.assert_not_called()


@pytest.mark.django_db
def test_structure_respects_scope(client_as, user, grant, llm):
    root = StructuralUnitFactory(name="HQ", custom_type="Офіс")
    it = StructuralUnitFactory(name="IT", custom_type="Департамент", parent=root)
    StructuralUnitFactory(name="Backend", custom_type="Команда", parent=it)
    StructuralUnitFactory(name="Sales", custom_type="Департамент", parent=root)
    grant(user, "ai:use")
    grant(user, "company:read", unit=it)

    response = ask(client_as(user), "Покажи структуру")

    assert response.json()["response"] == "Департамент: IT\n  Команда: Backend"


@pytest.mark.django_db
def test_structure_requires_company_read(client_as, user, grant, llm):
    StructuralUnitFactory(name="HQ")
    grant(user, "ai:use")

    response = ask(client_as(user), "Покажи структуру")

    assert response.json()["response"] == openai_service.NO_STRUCTURE_ACCESS


# --- сесії та історія ---------------------------------------------------------


@pytest.mark.django_db
def test_sessions_list_shows_only_own_with_counts(
    client_as, auth_client, user, grant, llm
):
    session_id = ask(auth_client, "Раз").json()["session_id"]
    ask(auth_client, "Два", session_id=session_id)
    grant(user, "ai:use")
    ask(client_as(user), "Чуже")

    results = auth_client.get("/api/ai/chat/sessions/").json()["results"]

    assert [(s["session_id"], s["messages_count"]) for s in results] == [
        (session_id, 2)
    ]


@pytest.mark.django_db
def test_session_messages_in_chronological_order(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]
    ask(auth_client, "Два", session_id=session_id)

    response = auth_client.get(f"/api/ai/chat/sessions/{session_id}/messages/")

    assert [m["message"] for m in response.json()["results"]] == ["Раз", "Два"]


@pytest.mark.django_db
def test_rename_session_with_patch_only(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]
    url = f"/api/ai/chat/sessions/{session_id}/"

    response = auth_client.patch(url, {"name": "Нова назва"}, format="json")

    assert response.status_code == 200
    assert ChatSession.objects.get(session_id=session_id).name == "Нова назва"
    assert auth_client.put(url, {"name": "X"}, format="json").status_code == 405


@pytest.mark.django_db
def test_delete_session_removes_messages(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]

    response = auth_client.delete(f"/api/ai/chat/sessions/{session_id}/")

    assert response.status_code == 204
    assert not AIQuery.objects.exists()


@pytest.mark.django_db
def test_other_users_session_is_invisible(client_as, auth_client, user, grant, llm):
    session_id = ask(auth_client, "Моє").json()["session_id"]
    grant(user, "ai:use")
    client = client_as(user)

    assert client.get(f"/api/ai/chat/sessions/{session_id}/").status_code == 404
    assert client.delete(f"/api/ai/chat/sessions/{session_id}/").status_code == 404


@pytest.mark.django_db
def test_chat_history_lists_own_queries_newest_first(
    client_as, auth_client, user, grant, llm
):
    ask(auth_client, "Перше")
    ask(auth_client, "Друге")
    grant(user, "ai:use")
    ask(client_as(user), "Чуже")

    results = auth_client.get("/api/ai/chat/history/").json()["results"]

    assert [q["message"] for q in results] == ["Друге", "Перше"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("post", CHAT_URL),
        ("get", "/api/ai/chat/sessions/"),
        ("get", "/api/ai/chat/history/"),
    ],
)
def test_ai_requires_ai_use(client_as, user, grant, llm, method, url):
    payload = {"message": "Привіт"} if method == "post" else None

    denied = getattr(client_as(user), method)(url, payload, format="json")
    grant(user, "ai:use")
    allowed = getattr(client_as(user), method)(url, payload, format="json")

    assert denied.status_code == 403
    assert allowed.status_code == 200
