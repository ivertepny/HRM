FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.5 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # venv поза /usr/src, щоб bind-mount коду в docker-compose його не перекривав
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# graphviz — бінарник dot для діаграм оргструктури
RUN apt-get update && apt-get install --no-install-recommends -y graphviz \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src

# Спочатку тільки залежності — шар кешується, поки не змінився lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
