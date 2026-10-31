# План розвитку HRM-системи

> Оновлено: 31.10.2026

## ✅ Зроблено

- [x] Тулінг: uv + ruff, Python 3.14, Docker на uv
- [x] Структура `config/` (settings `base` / `dev` / `prod` / `test`) + `apps/`, міграції з нуля
- [x] Основа API: пагінація, глобальний обробник помилок, CORS, JWT refresh (access 30 хв), Swagger
- [x] Тести: pytest + factory_boy (218 тестів, ~96%)
- [x] Ролі та дозволи (`apps/access`): `resource:action` з wildcard-ами, scope на підрозділ, тимчасові ролі, захист від ескалації, `seed_roles` (System Admin / HR Manager / Employee)
- [x] Дозволи на всіх ендпоінтах; власні дані доступні завжди; зарплата — окремо через `salary:read` / `write`; реєстрація лише через HR
- [x] Працівник: рівень, зарплата, дата народження, фото, документи; автоматичний кадровий журнал (`CareerHistory`); `PROTECT` замість `CASCADE`
- [x] Оргструктура: валідація дерева через API, історія змін з автором, SVG-діаграма
- [x] S3 для файлів у prod — лише через IAM-роль (код готовий, підключення — при деплої)
- [x] AI-асистент на LangGraph / LangChain (`langchain-openai`): агент з інструментом оргструктури (з урахуванням прав), сесії в БД за `session_id`, ліміт історії, таймаут і 503 при збої LLM
- [x] Redis-кеш (`CACHES` з `REDIS_URL`, сервіс у docker-compose): права користувача кешуються між запитами, версійна інвалідація при зміні ролей / дозволів, TTL з урахуванням тимчасових ролей, fallback на БД при недоступності Redis
- [x] Технічний борг: `children_count`, без N+1 у списках (предки підрозділів, scope-перевірки зарплати), валюта зарплати (`salary_currency`), psycopg3 з `connect_timeout`

---

## ✅ Крок 1 — Рефакторинг AI-асистента

- [x] Сесії чату в БД за `session_id` з запиту, а не в cookie-сесії (не працює з JWT-клієнтами)
- [x] Виправити `chat/reset` (другий виклик падає з `IntegrityError`) — прибрано: нова розмова = запит без `session_id`
- [x] Обмежити історію (`MAX_HISTORY_AI`)
- [x] OpenAI-клієнт ліниво; таймаути, 503 при збої API
- [x] Відповідь про структуру — з урахуванням `company:read` і scope
- [x] Прибрати дублювання `ChatSession.conversation` / `AIQuery`
- [x] Перевести на LangGraph / LangChain: агент з інструментом `get_company_structure`

## ✅ Крок 2 — Відпустки (`vacations`)

- [x] `VacationRequest`: `employee`, `date_start`, `date_end`, `status` (`pending` / `approved` / `rejected` / `cancelled`), `reviewed_by` / `reviewed_at`, коментарі, історія; тип (щорічна / лікарняний / за свій рахунок / інше)
- [x] Валідація дат і перетинів з активними заявками; щорічна і за свій рахунок — не в минулому; звільнений працівник не подає
- [x] Подати заявку за себе (`vacations:write`), схвалити / відхилити (`vacations:manage`, у межах scope, не власну)
- [x] Скасування власником (поки не почалась) або HR; HR може подати заявку за працівника (лікарняний)
- [x] PostgreSQL exclusion constraint: схвалені періоди одного працівника не перетинаються навіть при гонці
- [x] Фільтри для календаря: `?date_from` / `?date_to` (перетин з періодом), `status`, `vacation_type`, `employee`

## ⏭ Крок 3 — Frontend (Next.js / React)

- [x] Каркас `frontend/` у цьому репозиторії: Next.js (App Router) + TypeScript, Tailwind + shadcn/ui, українська локаль
- [x] Типи API генеруються з OpenAPI-схеми бекенду (`/api/schema/`) — без ручних DTO
- [x] Дані: TanStack Query; форми: react-hook-form + zod; помилки API (400 по полях / 403 / 409 / 503) — у формах і тостах
- [x] Автентифікація через Next.js як BFF: JWT в httpOnly-cookie (не в localStorage), автоматичний refresh, logout з blacklist
- [x] UI з урахуванням прав: меню і кнопки за `/api/users/me/permissions/`
- [ ] Сторінки:
  - [x] Вхід, мій профіль (`/me`)
  - [ ] Довідник працівників і профіль працівника (зарплата — лише за правами), кадровий журнал, документи
  - [ ] Оргструктура: дерево, SVG-діаграма, історія змін
  - [x] Відпустки: мої заявки і подання, черга на розгляд для HR, календар (`date_from` / `date_to`)
  - [ ] AI-асистент: чат із сесіями
  - [ ] Адміністрування: облікові записи, ролі, призначення ролей
- [x] Тести: Vitest + Testing Library
- [ ] e2e — Playwright проти бекенду в docker-compose
- [ ] Сервіс `frontend` у docker-compose; CORS для dev уже налаштовано

## Крок 4 — Обладнання (`equipment`)

- [ ] `Equipment`: `serial_number` (унікальний), `name`, `description`
- [ ] `EquipmentAssignment`: `equipment`, `employee`, `date_assigned`, `date_returned`
- [ ] Одна одиниця — не більше одного активного призначення; без призначення = «на складі»

## Крок 5 — Тайм-трекінг (`attendance`)

- [ ] `AttendanceRecord`: `employee`, `date`, `time_start`, `time_end`, `status` (`remote` / `office` / `off`)
- [ ] Відмітка присутності за себе; місячний звіт для HR (з урахуванням scope)

## Крок 6 — Скидання пароля і запрошення

- [ ] Email: AWS SES (через IAM-роль), SMTP / console для dev
- [ ] `password-reset/` → `password-reset/confirm/` на `django.contrib.auth`
- [ ] Лист-запрошення новим користувачам замість пароля від HR

## Крок 7 — CI/CD (GitHub Actions)

- [ ] PR: `ruff check`, `ruff format --check`, `pytest` на PostgreSQL, `spectacular --validate`, Docker build
- [ ] Deploy з `main`; доступ до AWS лише через OIDC + assume-role

## Крок 8 — Продакшн

- [ ] gunicorn, Nginx, HTTPS (Let's Encrypt), `SECURE_SSL_REDIRECT`, HSTS, `collectstatic`
- [ ] S3: приватний бакет + IAM-роль сервера (`GetObject` / `PutObject` / `DeleteObject` на `employees/*`)
- [x] Redis-кеш дозволів між запитами
- [ ] Довгий випадковий `SECRET_KEY`

## Крок 9 — Документація

- [ ] Переписати `README.md` (зараз — чужий шаблон)
- [ ] Оновити `docs/summary.md`
- [ ] Описати модель доступу для HR / адміністраторів

---

## ✅ Технічний борг

- [x] `StructuralUnit.children_count` оголошено, але не заповнюється
- [x] Перевірка зарплати в списках для scoped-ролей — запит на кожен рядок
- [x] Зарплата без валюти
- [x] `psycopg2-binary` → `psycopg[binary]`
- [x] N+1 запитів предків підрозділу у списках (знайдено під час ревізії)

---

## Пізніше

React (web) → Крок 3; Flutter (mobile), Slack-бот, Google Calendar
