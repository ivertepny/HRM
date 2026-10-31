"""Розмова з асистентом: історія з БД → LangGraph-агент → збереження обміну."""

import logging

import openai
from django.conf import settings
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.errors import GraphRecursionError
from rest_framework.exceptions import ValidationError

from apps.core.exceptions import ServiceUnavailable

from . import agent
from .models import AIQuery
from .utils import count_tokens

logger = logging.getLogger(__name__)

UNAVAILABLE = "AI-асистент тимчасово недоступний. Спробуйте пізніше."


def history_messages(session):
    """Останні MAX_HISTORY_AI обмінів сесії у вигляді повідомлень LangChain."""
    recent = list(
        session.queries.order_by("-created_at", "-id")[: settings.MAX_HISTORY_AI]
    )
    messages = []
    for query in reversed(recent):
        messages.append(HumanMessage(query.message))
        messages.append(AIMessage(query.response))
    return messages


def run_agent(session, prompt, access):
    """Повертає (текст відповіді, назви викликаних інструментів)."""
    messages = [
        SystemMessage(agent.SYSTEM_PROMPT),
        *history_messages(session),
        HumanMessage(prompt),
    ]
    graph = agent.build_graph(agent.get_llm())
    try:
        result = graph.invoke(
            {"messages": messages},
            config={
                "configurable": {"access": access},
                "recursion_limit": settings.AI_RECURSION_LIMIT,
            },
        )
    except openai.OpenAIError as exc:
        logger.exception("LLM request failed")
        raise ServiceUnavailable(UNAVAILABLE) from exc
    except GraphRecursionError as exc:
        logger.exception("Agent exceeded recursion limit")
        raise ServiceUnavailable(UNAVAILABLE) from exc

    produced = result["messages"][len(messages) :]
    tools_used = [
        call["name"]
        for message in produced
        if isinstance(message, AIMessage)
        for call in message.tool_calls
    ]
    return produced[-1].text, tools_used


def answer(session, prompt, access) -> AIQuery:
    """Відповідає на питання в межах сесії і зберігає обмін."""
    if count_tokens(prompt) > settings.MAX_TOKENS_INPUT_AI:
        raise ValidationError(
            {"message": "Повідомлення занадто велике. Будь ласка, скоротіть текст."}
        )

    text, tools_used = run_agent(session, prompt, access)

    query = AIQuery.objects.create(
        user=session.user,
        chat_session=session,
        message=prompt,
        response=text,
        tools_used=tools_used,
    )
    session.save(update_fields=["updated_at"])
    return query
