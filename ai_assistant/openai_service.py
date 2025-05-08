import uuid
from openai import OpenAI
from django.conf import settings
from .models import AIQuery, ChatSession
from .utils import count_tokens, build_messages

client = OpenAI(api_key=settings.OPENAI_API_KEY)

max_tokens = settings.MAX_TOKENS_INPUT_AI
max_history_length = settings.MAX_HISTORY_AI
model_name = settings.MODEL_NAME_AI

def ask_openai(prompt: str, user, session) -> str:
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
