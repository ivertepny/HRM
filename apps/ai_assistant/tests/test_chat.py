import uuid
from unittest.mock import patch

import openai
import pytest
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from apps.access.services import UserAccess
from apps.ai_assistant import agent
from apps.ai_assistant.models import AIQuery, ChatSession
from apps.company.tests.factories import StructuralUnitFactory

CHAT_URL = "/api/ai/chat/"


def structure_call(n=1):
    """Відповідь моделі з викликом інструмента (новий об'єкт щоразу: LangGraph
    дедуплікує повідомлення за id)."""
    return AIMessage(
        "",
        tool_calls=[{"name": "get_company_structure", "args": {}, "id": f"call_{n}"}],
    )


class ScriptedChatModel(BaseChatModel):
    """Фейкова LLM: віддає кроки зі script (текст, AIMessage або виняток)
    і запам'ятовує вхідні повідомлення кожного виклику."""

    script: list = Field(default_factory=list)
    calls: list = Field(default_factory=list)
    bound_tools: list = Field(default_factory=list)

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        self.bound_tools = [t.name for t in tools]
        return self

    def say(self, *steps):
        self.script.extend(steps)

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.calls.append(list(messages))
        step = self.script.pop(0) if self.script else "Відповідь"
        if isinstance(step, Exception):
            raise step
        message = AIMessage(step) if isinstance(step, str) else step
        return ChatResult(generations=[ChatGeneration(message=message)])


@pytest.fixture
def llm():
    model = ScriptedChatModel()
    with patch.object(agent, "get_llm", return_value=model):
        yield model


def contents(messages):
    return [m.content for m in messages]


def ask(client, message, **extra):
    return client.post(CHAT_URL, {"message": message, **extra}, format="json")


pytestmark = pytest.mark.django_db


# --- розмова -------------------------------------------------------------------


def test_first_message_creates_session(auth_client, admin_user, llm):
    llm.say("24 дні")

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
    assert (query.message, query.response, query.tools_used) == (
        "Скільки днів відпустки?",
        "24 дні",
        [],
    )


def test_agent_gets_system_prompt_and_tools(auth_client, llm):
    ask(auth_client, "Привіт")

    first = llm.calls[0][0]
    assert isinstance(first, SystemMessage)
    assert first.content == agent.SYSTEM_PROMPT
    assert llm.bound_tools == ["get_company_structure"]


def test_session_id_continues_conversation_with_history(auth_client, llm):
    llm.say("Перша відповідь", "Друга відповідь")
    session_id = ask(auth_client, "Перше питання").json()["session_id"]

    response = ask(auth_client, "Друге питання", session_id=session_id)

    assert response.json()["session_id"] == session_id
    assert ChatSession.objects.count() == 1
    assert contents(llm.calls[-1][1:]) == [
        "Перше питання",
        "Перша відповідь",
        "Друге питання",
    ]


def test_without_session_id_each_message_starts_new_session(auth_client, llm):
    ask(auth_client, "Раз")
    ask(auth_client, "Два")

    assert ChatSession.objects.count() == 2
    assert contents(llm.calls[-1][1:]) == ["Два"]


def test_history_is_limited_to_max_history(auth_client, llm, settings):
    settings.MAX_HISTORY_AI = 2
    session_id = ask(auth_client, "q1").json()["session_id"]
    for prompt in ("q2", "q3"):
        ask(auth_client, prompt, session_id=session_id)

    ask(auth_client, "q4", session_id=session_id)

    user_turns = [m.content for m in llm.calls[-1] if m.type == "human"]
    assert user_turns == ["q2", "q3", "q4"]


def test_foreign_session_id_returns_404(client_as, auth_client, user, grant, llm):
    foreign = ask(auth_client, "Моє").json()["session_id"]
    grant(user, "ai:use")

    response = ask(client_as(user), "Чуже", session_id=foreign)

    assert response.status_code == 404


def test_unknown_session_id_returns_404(auth_client, llm):
    assert ask(auth_client, "Привіт", session_id=str(uuid.uuid4())).status_code == 404


def test_too_long_message_returns_400_without_calling_model(auth_client, llm, settings):
    settings.MAX_TOKENS_INPUT_AI = 3

    response = ask(auth_client, "дуже довге повідомлення про відпустку")

    assert response.status_code == 400
    assert "message" in response.json()
    assert llm.calls == []
    assert not AIQuery.objects.exists()


# --- збої ---------------------------------------------------------------------


def test_llm_failure_returns_503_and_stores_nothing(auth_client, llm):
    llm.say(openai.OpenAIError("boom"))

    response = ask(auth_client, "Привіт")

    assert response.status_code == 503
    assert "boom" not in str(response.json())
    assert not AIQuery.objects.exists()


def test_endless_tool_loop_is_cut_by_recursion_limit(auth_client, llm, settings):
    settings.AI_RECURSION_LIMIT = 4
    llm.say(*(structure_call(n) for n in range(10)))

    response = ask(auth_client, "Структура?")

    assert response.status_code == 503
    assert not AIQuery.objects.exists()


def test_missing_api_key_returns_503(auth_client, settings):
    settings.OPENAI_API_KEY = ""
    agent.get_llm.cache_clear()
    try:
        response = ask(auth_client, "Привіт")
    finally:
        agent.get_llm.cache_clear()

    assert response.status_code == 503


# --- інструмент оргструктури --------------------------------------------------


def tool_result(llm):
    """Що інструмент повернув моделі (ToolMessage у другому виклику LLM)."""
    return next(m.content for m in llm.calls[1] if isinstance(m, ToolMessage))


def test_agent_answers_structure_question_via_tool(auth_client, llm):
    root = StructuralUnitFactory(name="HQ", custom_type="Офіс")
    StructuralUnitFactory(name="IT", custom_type="Департамент", parent=root)
    llm.say(structure_call(), "У компанії є офіс HQ з департаментом IT.")

    response = ask(auth_client, "Яка структура компанії?")

    assert response.json()["response"] == "У компанії є офіс HQ з департаментом IT."
    assert response.json()["query"]["tools_used"] == ["get_company_structure"]
    assert tool_result(llm) == "Офіс: HQ\n  Департамент: IT"


def test_structure_tool_respects_scope(client_as, user, grant, llm):
    root = StructuralUnitFactory(name="HQ", custom_type="Офіс")
    it = StructuralUnitFactory(name="IT", custom_type="Департамент", parent=root)
    StructuralUnitFactory(name="Backend", custom_type="Команда", parent=it)
    StructuralUnitFactory(name="Sales", custom_type="Департамент", parent=root)
    grant(user, "ai:use")
    grant(user, "company:read", unit=it)
    llm.say(structure_call(), "Готово")

    ask(client_as(user), "Покажи структуру")

    assert tool_result(llm) == "Департамент: IT\n  Команда: Backend"


def test_structure_tool_without_company_read(client_as, user, grant, llm):
    StructuralUnitFactory(name="HQ")
    grant(user, "ai:use")
    llm.say(structure_call(), "Немає доступу")

    ask(client_as(user), "Покажи структуру")

    assert tool_result(llm) == agent.NO_STRUCTURE_ACCESS


def test_company_structure_text_for_empty_company(admin_user):
    assert agent.company_structure_text(UserAccess(admin_user)) == agent.EMPTY_STRUCTURE


def test_tool_answers_are_not_replayed_as_history(auth_client, llm):
    StructuralUnitFactory(name="HQ")
    llm.say(structure_call(), "Є HQ", "Будь ласка")
    session_id = ask(auth_client, "Структура?").json()["session_id"]

    ask(auth_client, "Дякую", session_id=session_id)

    # В історії — лише питання і фінальна відповідь, без проміжних tool-повідомлень
    assert contents(llm.calls[-1][1:]) == ["Структура?", "Є HQ", "Дякую"]


# --- сесії та історія ---------------------------------------------------------


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


def test_session_messages_in_chronological_order(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]
    ask(auth_client, "Два", session_id=session_id)

    response = auth_client.get(f"/api/ai/chat/sessions/{session_id}/messages/")

    assert [m["message"] for m in response.json()["results"]] == ["Раз", "Два"]


def test_rename_session_with_patch_only(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]
    url = f"/api/ai/chat/sessions/{session_id}/"

    response = auth_client.patch(url, {"name": "Нова назва"}, format="json")

    assert response.status_code == 200
    assert ChatSession.objects.get(session_id=session_id).name == "Нова назва"
    assert auth_client.put(url, {"name": "X"}, format="json").status_code == 405


def test_delete_session_removes_messages(auth_client, llm):
    session_id = ask(auth_client, "Раз").json()["session_id"]

    response = auth_client.delete(f"/api/ai/chat/sessions/{session_id}/")

    assert response.status_code == 204
    assert not AIQuery.objects.exists()


def test_other_users_session_is_invisible(client_as, auth_client, user, grant, llm):
    session_id = ask(auth_client, "Моє").json()["session_id"]
    grant(user, "ai:use")
    client = client_as(user)

    assert client.get(f"/api/ai/chat/sessions/{session_id}/").status_code == 404
    assert client.delete(f"/api/ai/chat/sessions/{session_id}/").status_code == 404


def test_chat_history_lists_own_queries_newest_first(
    client_as, auth_client, user, grant, llm
):
    ask(auth_client, "Перше")
    ask(auth_client, "Друге")
    grant(user, "ai:use")
    ask(client_as(user), "Чуже")

    results = auth_client.get("/api/ai/chat/history/").json()["results"]

    assert [q["message"] for q in results] == ["Друге", "Перше"]


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


# --- ліміти --------------------------------------------------------------------


def test_chat_is_rate_limited_per_user(client_as, user, grant, llm, throttle_rates):
    grant(user, "ai:use")
    client = client_as(user)

    assert ask(client, "Привіт").status_code == 200
    response = ask(client, "Ще раз")

    assert response.status_code == 429
    assert len(llm.calls) == 1  # модель удруге не викликалась
