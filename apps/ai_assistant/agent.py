"""LangGraph-агент HR-асистента.

Граф: agent (LLM з інструментами) ⇄ tools, доки модель не дасть фінальну
відповідь. Граф stateless: історію розмови сервіс підставляє з БД, а права
користувача (UserAccess) передаються інструментам через
config["configurable"]["access"] — модель не може їх підмінити.
"""

from functools import cache

from django.conf import settings
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import tools_condition

from apps.company.models import StructuralUnit
from apps.core.exceptions import ServiceUnavailable

SYSTEM_PROMPT = (
    "Ти HR-асистент компанії. Відповідай українською, коротко і по суті. "
    "Для питань про підрозділи, відділи чи оргструктуру викликай інструмент "
    "get_company_structure і спирайся лише на його результат; не вигадуй "
    "підрозділів, яких там немає."
)

NO_STRUCTURE_ACCESS = "У користувача немає доступу до організаційної структури."
EMPTY_STRUCTURE = "Структура компанії не знайдена."


def company_structure_text(access) -> str:
    """Структура з відступами — лише ті підрозділи, які користувач може бачити."""
    if not access.has_anywhere("company:read"):
        return NO_STRUCTURE_ACCESS

    units = StructuralUnit.objects.filter(is_active=True)
    visible = access.units_for("company:read")
    if visible is not None:
        units = units.filter(pk__in=visible)

    depth = {}
    lines = []
    for unit in units.order_by("tree_id", "lft"):
        # Видимий підрозділ без видимого батька стає коренем свого піддерева
        depth[unit.id] = depth[unit.parent_id] + 1 if unit.parent_id in depth else 0
        prefix = "  " * depth[unit.id]
        lines.append(f"{prefix}{unit.custom_type or 'Підрозділ'}: {unit.name}")

    return "\n".join(lines) or EMPTY_STRUCTURE


@tool
def get_company_structure(config: RunnableConfig) -> str:
    """Повертає організаційну структуру компанії (підрозділи та їх ієрархію),
    доступну поточному користувачу."""
    return company_structure_text(config["configurable"]["access"])


TOOLS = [get_company_structure]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


@cache
def get_llm():
    """Модель створюється при першому запиті, а не при імпорті."""
    if not settings.OPENAI_API_KEY:
        raise ServiceUnavailable("AI-асистент не налаштований.")
    return ChatOpenAI(
        model=settings.MODEL_NAME_AI,
        api_key=settings.OPENAI_API_KEY,
        temperature=0.7,
        max_tokens=settings.MAX_TOKENS_OUTPUT_AI,
        timeout=settings.OPENAI_TIMEOUT_AI,
        max_retries=2,
    )


def run_tools(state: MessagesState, config: RunnableConfig):
    """Виконує виклики інструментів з останньої відповіді моделі.

    Замість langgraph.prebuilt.ToolNode: той запускає інструменти в thread
    pool, а в Django кожен потік — окреме з'єднання з БД, яке ніхто не
    закриває (і яке не бачить даних поточної транзакції).
    """
    results = []
    for call in state["messages"][-1].tool_calls:
        tool_ = TOOLS_BY_NAME.get(call["name"])
        content = (
            tool_.invoke(call["args"], config)
            if tool_
            else f"Невідомий інструмент: {call['name']}"
        )
        results.append(
            ToolMessage(content=content, tool_call_id=call["id"], name=call["name"])
        )
    return {"messages": results}


def build_graph(llm):
    model = llm.bind_tools(TOOLS)

    def agent(state: MessagesState):
        return {"messages": [model.invoke(state["messages"])]}

    graph = StateGraph(MessagesState)
    graph.add_node("agent", agent)
    graph.add_node("tools", run_tools)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()
