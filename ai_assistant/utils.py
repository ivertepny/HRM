# ai_assistant/utils.py

import tiktoken


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))


def build_messages(prompt: str, session) -> list[dict[str, str]]:
    """
    Формує список повідомлень для OpenAI API, включаючи історію з сесії.
    """
    messages = [
        {
            "role": "system",
            "content": "Ти HR-асистент компанії. Відповідай коротко і по суті справи.",
        }
    ]

    history = session.get("chat_history", [])
    messages.extend(history)

    messages.append({"role": "user", "content": prompt})
    return messages
