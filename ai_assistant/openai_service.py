import uuid, spacy
from openai import OpenAI
from django.conf import settings
from .models import AIQuery, ChatSession
from .utils import count_tokens, build_messages
from company.models import StructuralUnit  # Імпорт  моделі

client = OpenAI(api_key=settings.OPENAI_API_KEY)

max_tokens = settings.MAX_TOKENS_INPUT_AI
max_history_length = settings.MAX_HISTORY_AI
model_name = settings.MODEL_NAME_AI

# Ініціалізуємо spaCy
try:
    nlp = spacy.load("uk_core_news_sm")
except Exception as e:
    nlp = None  # Обробка помилок за потреби

# Ключові леми для визначення запитів про структуру
STRUCTURE_LEMMAS = {
    "структура", "підрозділ", "відділ", "компанія",
    "організація", "структурний", "організаційний", "департамент"
}


def is_structure_query(prompt: str) -> bool:
    """Використовуємо spaCy для визначення наміру"""
    if not nlp:
        return any(kw in prompt.lower() for kw in ["структур", "підрозділ", "відділ"])

    doc = nlp(prompt.lower())
    found_lemmas = {token.lemma_ for token in doc}
    return bool(found_lemmas & STRUCTURE_LEMMAS)


def get_company_structure_text():
    """Повертає структуру у вигляді тексту з відступами"""
    units = StructuralUnit.objects.filter(is_active=True, parent=None).order_by('name')

    if not units.exists():
        return "Структура компанії не знайдена."

    lines = []

    def add_unit(unit, level=0):
        prefix = "  " * level
        unit_type = unit.custom_type or "Підрозділ"
        lines.append(f"{prefix}{unit_type}: {unit.name}")
        for child in unit.children.filter(is_active=True).order_by('name'):
            add_unit(child, level + 1)

    for root_unit in units:
        add_unit(root_unit)

    return "\n".join(lines)


def ask_openai(prompt: str, user, session) -> str:
    if is_structure_query(prompt):
        return get_company_structure_text()
    else:
        if count_tokens(prompt) > max_tokens:
            return "Ваше повідомлення занадто велике. Будь ласка, скоротіть текст."

        if "chat_session_id" not in session:
            session["chat_session_id"] = str(uuid.uuid4())

        chat_session_id = session["chat_session_id"]

        chat_session, _ = ChatSession.objects.get_or_create(
            session_id=chat_session_id,
            defaults={"user": user}
        )

        # Формуємо повідомлення для моделі
        messages = build_messages(prompt, session)

        # Запит до OpenAI
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_completion_tokens=max_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
        )

        answer = response.choices[0].message.content

        # Оновлюємо історію в сесії
        chat_history = session.get("chat_history", [])
        chat_history.append({"role": "user", "content": prompt})
        chat_history.append({"role": "assistant", "content": answer})
        session["chat_history"] = chat_history
        session.modified = True

        # ОНОВЛЕННЯ conversation в ChatSession
        conversation = chat_session.conversation or []
        conversation.append({"role": "user", "content": prompt})
        conversation.append({"role": "assistant", "content": answer})
        chat_session.conversation = conversation
        chat_session.save(update_fields=["conversation"])

        # Запис у базу даних
        AIQuery.objects.create(
            user=user,
            message=prompt,
            response=answer,
            chat_session=chat_session
        )

        return answer
