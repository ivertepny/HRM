# openai_service.py
from openai import OpenAI
from django.conf import settings
from .models import AIQuery
from .utils import count_tokens, build_messages

client = OpenAI(api_key=settings.OPENAI_API_KEY)
max_tokens = settings.MAX_TOKENS_INPUT  # ліміт токенів для введення
max_history_length = settings.MAX_HISTORY  # максимальна довжина історії

def ask_openai(prompt: str, user, session) -> str:
    if count_tokens(prompt) > max_tokens:
        return "Ваше повідомлення занадто велике. Будь ласка, скоротіть текст."

    messages = build_messages(prompt, session)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=max_tokens,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )

    answer = response.choices[0].message.content

    # Зберігаємо нову пару в історію сесії
    history = session.get("chat_history", [])
    history.append({"role": "user", "content": prompt})
    history.append({"role": "assistant", "content": answer})
    session["chat_history"] = history[-max_history_length:]  # обмеження довжини історії (наприклад, 10 пар)
    session.modified = True

    # Логування в базу
    AIQuery.objects.create(user=user, message=prompt, response=answer)

    return answer

