# HRM — внутрішня HR-система

Кадри однієї компанії в одному місці:
- профілі працівників і документи;
- оргструктура;
- відпустки зі схваленням;
- обладнання на руках;
- табель присутності;
- AI-асистент, який відповідає з урахуванням прав.

Доступ налаштовується гнучко: ролі з дозволами `resource:action`, які діють
на всю компанію або лише на підрозділ (див. [docs/access.md](docs/access.md)).

| Частина | Технології |
|---------|-----------|
| Бекенд | Python 3.14, Django 5.2, DRF, PostgreSQL 17, Redis (кеш прав), drf-spectacular |
| Фронтенд | Next.js 16 (App Router, BFF), React 19, TypeScript, Tailwind 4, TanStack Query |
| AI | LangGraph / LangChain + OpenAI |
| Тести | pytest + factory_boy, Vitest, Playwright (e2e) |
| Інфраструктура | Docker, GitHub Actions, Hetzner VPS (gunicorn + nginx), restic-бекапи |

## Як це влаштовано

```
браузер ──▶ Next.js (сторінки + BFF) ──▶ Django REST API ──▶ PostgreSQL
              │ JWT у httpOnly-cookie        │ ролі й scope       Redis (кеш прав)
              └ /media → файли з перевіркою прав
```

- **Браузер не бачить ні JWT, ні Django.** Next.js тримає токени в
  httpOnly-cookie і проксує запити (`/api/backend/…`), додаючи
  `Authorization`. Подробиці — у [frontend/README.md](frontend/README.md).
- **Права перевіряє лише бекенд.** Фронт ховає пункти меню, на які немає
  дозволу, але кожну відповідь вирішує Django: області видимості (scope)
  застосовуються до кожного запиту і кожного об'єкта.
- **Типи фронту генеруються з OpenAPI-схеми бекенду.** Це `openapi.json` і
  `schema.d.ts`; CI перевіряє, що вони не застаріли.

## Швидкий старт (Docker)

```powershell
copy .env.example .env          # заповнити SECRET_KEY і POSTGRES_PASSWORD
docker compose up -d --build    # api :8000, frontend :3000, db, redis, pgAdmin :5050
docker compose exec api python manage.py seed_demo
```

Відкрийте http://localhost:3000. Якщо порт 8000 уже зайнятий, задайте
`API_PORT=8001` у `.env`.

Що створює `seed_demo` (лише для розробки, з `DEBUG=False` команда відмовляється
працювати):
- **оргструктуру:** Головний офіс → HR, IT → Backend / Frontend;
- **користувачів:** `admin@`, `hr@`, `olena@`, `petro@`, `maria@example.com`;
- **дані:** відпустки, обладнання і табель за минулий тиждень.

Пароль за замовчуванням — `DEFAULT_PASSWORD` у
`apps/core/management/commands/seed_demo.py`, свій можна задати через
`--password`.

## Розробка без Docker

Потрібні Python 3.14 + [uv](https://docs.astral.sh/uv/), Node 22, PostgreSQL і
(необов'язково) Redis. Без `REDIS_URL` кеш живе в пам'яті процесу.

```powershell
.\dev.ps1 install      # uv sync
.\dev.ps1 migrate
.\dev.ps1 seed         # дозволи і системні ролі (seed_roles)
.\dev.ps1 run          # Django на :8000; Swagger — /api/schema/swagger-ui/

cd frontend
npm install
copy .env.example .env.local
npm run dev            # http://localhost:3000
```

Інші команди `dev.ps1`: `lint`, `fmt`, `fix`, `check`, `test`, `test-cov`,
`makemigrations`, `shell`, `docker-up` / `docker-down` / `docker-logs`.

## Тести і перевірки

```powershell
uv run pytest                       # бекенд (потрібен PostgreSQL з POSTGRES_* з .env)
uv run ruff check . ; uv run ruff format --check .

cd frontend
npm test ; npm run lint ; npm run typecheck
npm run e2e:stack ; npx playwright test ; npm run e2e:down   # e2e на ізольованому стенді :13000
```

E2e-стенд (`docker-compose.e2e.yml`) має власну базу в пам'яті й засіюється
`seed_demo`. Dev-базу він не чіпає.

**Після змін в API** (серіалізатори, в'юсети, `extend_schema`): у `frontend/`
виконайте `npm run api:types` і закомітьте `openapi.json` разом зі
`schema.d.ts`.

**Після змін каталогу дозволів** (`apps/access/catalog.py`): виконайте
`python manage.py seed_roles --reset-system-roles`, щоб оновити системні ролі в
наявній базі.

## Структура

```
config/              налаштування: base / dev / prod / test, urls
apps/
  users/             облікові записи, вхід (JWT), профіль
  employees/         працівники, посади, кадровий журнал, документи, зарплата
  company/           оргструктура (MPTT-дерево), історія змін, SVG-діаграма
  access/            дозволи, ролі, призначення зі scope, кеш прав
  vacations/         заявки на відпустку і їх розгляд
  equipment/         облік і видача обладнання
  attendance/        табель і місячний звіт
  ai_assistant/      LangGraph-агент з інструментом оргструктури
  core/              обробник помилок, пагінація, ліміти, health, /media, Sentry
frontend/            Next.js-клієнт (див. frontend/README.md)
nginx/, deploy.sh, docker-compose.server.yml, scripts/   продакшн
docs/                план, доступ, деплой, зведення
```

## Документація

- [docs/access.md](docs/access.md) — ролі й дозволи, для HR і адміністраторів.
- [docs/deploy.md](docs/deploy.md) — сервер, деплой, бекапи, відновлення.
- [docs/summary.md](docs/summary.md) — що вже є в системі і як воно працює.
- [docs/plan.md](docs/plan.md) — план розвитку.
- Swagger у dev: http://localhost:8000/api/schema/swagger-ui/.

## Продакшн

Push у `main` запускає CI (`.github/workflows/ci.yml`). Після нього, якщо
в `deploy.yml` стоїть `START: "1"`, GitHub Actions по SSH запускає
`deploy.sh` на Hetzner VPS. Як налаштувати сервер, бекапи і відновлення — у
[docs/deploy.md](docs/deploy.md).
