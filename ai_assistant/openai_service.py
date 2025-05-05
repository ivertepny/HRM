# ai_assistant/openai_service.py
import tiktoken
from openai import OpenAI
from django.conf import settings
from .models import AIQuery

client = OpenAI(api_key=settings.OPENAI_API_KEY)
max_tokens = settings.MAX_TOKENS_INPUT  # лимит токенов для ввода пользователя

def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    tokenizer = tiktoken.encoding_for_model(model)
    return len(tokenizer.encode(text))

def ask_openai(prompt: str, user, session) -> str:
    if count_tokens(prompt) > max_tokens:
        return "Ваше повідомлення занадто велике. Будь ласка, скоротіть текст."

    # Пытаемся получить предыдущий запрос из сессии
    last_query_id = session.get('last_ai_query_id')
    messages = [
        {"role": "system", "content": "Ти HR-асистент компанії. Відповідай коротко і по суті справи."}
    ]

    if last_query_id:
        try:
            prev_query = AIQuery.objects.get(id=last_query_id, user=user)
            messages.append({"role": "user", "content": prev_query.message})
            messages.append({"role": "assistant", "content": prev_query.response})
        except AIQuery.DoesNotExist:
            pass  # если сообщение не найдено — игнорируем

    # Добавляем текущее сообщение
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.7,
        max_tokens=350,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
        stop=None,
        n=1,
    )

    answer = response.choices[0].message.content

    # Сохраняем в базу
    ai_query = AIQuery.objects.create(user=user, message=prompt, response=answer)
    session['last_ai_query_id'] = ai_query.id  # сохраняем ID в сессии

    return answer
