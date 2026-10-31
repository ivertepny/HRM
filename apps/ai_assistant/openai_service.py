"""Логіка асистента: відповіді про оргструктуру з БД, решта — через OpenAI."""

import logging
from functools import cache

import openai
from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.access.services import UserAccess
from apps.company.models import StructuralUnit
from apps.core.exceptions import ServiceUnavailable

from .models import AIQuery
from .utils import count_tokens

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = "Ти HR-асистент компанії. Відповідай коротко і по суті справи."

# Ключові підрядки для визначення запитів про структуру компанії
STRUCTURE_KEYWORDS = [
    "структур",
    "підрозділ",
    "відділ",
    "департамент",
]

NO_STRUCTURE_ACCESS = "У вас немає доступу до організаційної структури."
EMPTY_STRUCTURE = "Структура компанії не знайдена."


@cache
def get_client():
    """OpenAI-клієнт створюється при першому запиті, а не при імпорті."""
    if not settings.OPENAI_API_KEY:
        raise ServiceUnavailable("AI-асистент не налаштований.")
    return openai.OpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=settings.OPENAI_TIMEOUT_AI,
        max_retries=2,
    )


def is_structure_query(prompt: str) -> bool:
    """Визначає, чи запит стосується організаційної структури компанії."""
    text = prompt.lower()
    return any(kw in text for kw in STRUCTURE_KEYWORDS)


def get_company_structure_text(access: UserAccess) -> str:
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


def build_messages(session, prompt: str) -> list[dict[str, str]]:
    """Системний промпт + останні MAX_HISTORY_AI обмінів сесії + нове питання."""
    history = list(
        session.queries.filter(source=AIQuery.Source.OPENAI).order_by(
            "-created_at", "-id"
        )[: settings.MAX_HISTORY_AI]
    )
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for query in reversed(history):
        messages.append({"role": "user", "content": query.message})
        messages.append({"role": "assistant", "content": query.response})
    messages.append({"role": "user", "content": prompt})
    return messages


def ask_openai(session, prompt: str) -> str:
    try:
        response = get_client().chat.completions.create(
            model=settings.MODEL_NAME_AI,
            messages=build_messages(session, prompt),
            temperature=0.7,
            max_completion_tokens=settings.MAX_TOKENS_OUTPUT_AI,
        )
    except openai.OpenAIError as exc:
        logger.exception("OpenAI request failed")
        raise ServiceUnavailable(
            "AI-асистент тимчасово недоступний. Спробуйте пізніше."
        ) from exc
    return response.choices[0].message.content or ""


def answer(session, prompt: str, access: UserAccess) -> AIQuery:
    """Відповідає на питання в межах сесії і зберігає обмін."""
    if count_tokens(prompt) > settings.MAX_TOKENS_INPUT_AI:
        raise ValidationError(
            {"message": "Повідомлення занадто велике. Будь ласка, скоротіть текст."}
        )

    if is_structure_query(prompt):
        text, source = (
            get_company_structure_text(access),
            AIQuery.Source.COMPANY_STRUCTURE,
        )
    else:
        text, source = ask_openai(session, prompt), AIQuery.Source.OPENAI

    query = AIQuery.objects.create(
        user=session.user,
        chat_session=session,
        message=prompt,
        response=text,
        source=source,
    )
    session.save(update_fields=["updated_at"])
    return query
