FROM python:3.14-slim

# uv тієї ж версії, що в CI (.github/workflows/ci.yml)
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
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 app \
    && useradd --system --uid 1000 --gid app --home /usr/src --shell /usr/sbin/nologin app

WORKDIR /usr/src

# Спочатку тільки залежності — шар кешується, поки не змінився lock
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Точка монтування volume з файлами: новий volume успадкує власника app
RUN mkdir -p media && chown app:app media

# Код належить root і лише читається процесом застосунку
USER app

EXPOSE 8000

# Продакшн. Міграції запускає команда сервісу в compose (docker-compose.server.yml);
# dev (docker-compose.yml) і e2e підміняють команду на runserver.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", \
     "--workers", "3", "--worker-class", "gthread", "--threads", "4", \
     "--timeout", "60", "--access-logfile", "-"]
