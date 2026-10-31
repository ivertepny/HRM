from functools import cache

import tiktoken


@cache
def _encoding(model):
    return tiktoken.encoding_for_model(model)


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    return len(_encoding(model).encode(text))
