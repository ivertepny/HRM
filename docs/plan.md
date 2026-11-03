# План розвитку HRM-системи

> Оновлено: 03.11.2026

## ✅ Зроблено

- [x] Тулінг: uv + ruff, Python 3.14, Docker на uv
- [x] Структура `config/` (settings `base` / `dev` / `prod` / `test`) + `apps/`, міграції з нуля
- [x] Основа API: пагінація, глобальний обробник помилок, CORS, JWT refresh (access 30 хв), Swagger
- [x] Тести: pytest + factory_boy (218 тестів, ~96%)
- [x] Ролі та дозволи (`apps/access`): `resource:action` з wildcard-ами, scope на підрозділ, тимчасові ролі, захист від ескалації, `seed_roles` (System Admin / HR Manager / Employee)
- [x] Дозволи на всіх ендпоінтах; власні дані доступні завжди; зарплата — окремо через `salary:read` / `write`; реєстрація лише через HR
- [x] Працівник: рівень, зарплата, дата народження, фото, документи; автоматичний кадровий журнал (`CareerHistory`); `PROTECT` замість `CASCADE`
- [x] Оргструктура: валідація дерева через API, історія змін з автором, SVG-діаграма
- [x] S3 для файлів у prod — лише через IAM-роль (код готовий, підключення — при деплої) → на кроці 7 замінено Docker volume: на Hetzner IAM-ролей немає
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

## ✅ Крок 3 — Frontend (Next.js / React)

- [x] Каркас `frontend/` у цьому репозиторії: Next.js (App Router) + TypeScript, Tailwind + shadcn/ui, українська локаль
- [x] Типи API генеруються з OpenAPI-схеми бекенду (`/api/schema/`) — без ручних DTO
- [x] Дані: TanStack Query; форми: react-hook-form + zod; помилки API (400 по полях / 403 / 409 / 503) — у формах і тостах
- [x] Автентифікація через Next.js як BFF: JWT в httpOnly-cookie (не в localStorage), автоматичний refresh, logout з blacklist
- [x] UI з урахуванням прав: меню і кнопки за `/api/users/me/permissions/`
- [x] Сторінки:
  - [x] Вхід, мій профіль (`/me`)
  - [x] Довідник працівників і профіль працівника (зарплата — лише за правами), кадровий журнал, документи
  - [x] Оргструктура: дерево, SVG-діаграма, історія змін
  - [x] Відпустки: мої заявки і подання, черга на розгляд для HR, календар (`date_from` / `date_to`)
  - [x] AI-асистент: чат із сесіями
  - [x] Адміністрування: облікові записи, ролі, призначення ролей, прийом на роботу
- [x] Тести: Vitest + Testing Library
- [x] e2e — Playwright проти бекенду в docker-compose (`docker-compose.e2e.yml`, демо-дані `seed_demo`)
- [x] Сервіс `frontend` у docker-compose (standalone-образ); CORS для dev уже налаштовано

## ✅ Крок 4 — Обладнання (`equipment`)

- [x] `Equipment`: `serial_number` (унікальний), `name`, `description` + `category`; стан — на складі / видано / списано
- [x] `EquipmentAssignment`: `equipment`, `employee`, `date_assigned`, `date_returned` + хто видав / прийняв, примітка
- [x] Одна одиниця — не більше одного активного призначення (частковий унікальний індекс у БД); без призначення = «на складі»
- [x] Операції видати / повернути / списати; обладнання з історією не видаляється, лише списується
- [x] Доступ: `equipment:read` / `equipment:manage` зі scope за підрозділом власника; своє обладнання видно завжди
- [x] Фронтенд: `/equipment` (облік, фільтри), картка з діями й історією, блок «Обладнання» в профілі та картці працівника; e2e-сценарій

## ✅ Крок 5 — Тайм-трекінг (`attendance`)

- [x] `AttendanceRecord`: `employee`, `date`, `time_start`, `time_end`, `status` (`remote` / `office` / `off`) + коментар; одна відмітка на день, порядок часу — обмеження БД
- [x] Відмітка присутності за себе (`attendance:write` у ролі Employee); виправлення — лише свого і в межах `ATTENDANCE_EDIT_DAYS` (7 днів)
- [x] Місячний звіт для HR (з урахуванням scope): офіс / віддалено / не працював / відпустка / без відмітки / години, фільтр за підрозділом
- [x] `TIME_ZONE = Europe/Kyiv` (env): «сьогодні» для табеля й відпусток — за часом компанії
- [x] Фронтенд: «Мій табель», «Табель команди»; e2e-сценарій
- [x] Пізніше: державні свята у робочих днях, експорт звіту в CSV → календар святкових днів веде HR (`attendance:manage`; під час воєнного стану держсвята — робочі дні), свята не рахуються робочими днями, відпусткою чи пропуском; CSV для Excel (BOM, «;», десяткова кома, захист від CSV-ін'єкції)

## ✅ Крок 6 — Скидання пароля і запрошення

- [x] Email: AWS SES (через IAM-роль), SMTP / console для dev — сервер тепер на Hetzner (без IAM-ролей), тож провайдера SMTP обрати на цьому кроці → будь-який SMTP через `EMAIL_*` (провайдера обрати при налаштуванні сервера); console у dev, файли в e2e
- [x] `password-reset/` → `password-reset/confirm/` на `django.contrib.auth` (токени `PasswordResetTokenGenerator`, 2 год, одноразові; вихід на всіх пристроях; без розкриття, чи існує пошта; ліміт 5/год на адресу)
- [x] Лист-запрошення новим користувачам замість пароля від HR (7 днів, повторне надсилання, «Запрошення не прийнято» в адмінці); e2e-сценарій
- [ ] На сервері: SMTP-провайдер, SPF / DKIM / DMARC для домену відправника

## ✅ Крок 7 — CI/CD (GitHub Actions) і деплой на Hetzner

- [x] PR: `ruff check`, `ruff format --check`, `pytest` на PostgreSQL, `spectacular --validate`, Docker build (`.github/workflows/ci.yml`; образи збирає e2e-job)
- [x] Deploy з `main`; доступ до AWS лише через OIDC + assume-role → деплой на Hetzner VPS по SSH, як у cosmetology (`deploy.yml` → `deploy.sh`); спільний шаблон сервера: `appleboy/ssh-action` за SHA, диспетчер на сервері за назвою репозиторію
- [x] CI перевіряє, що `openapi.json` і `schema.d.ts` не застаріли; `pip-audit`, `npm audit`; e2e Playwright на ізольованому стенді
- [x] Actions закріплені за SHA; Dependabot (actions, uv, npm, Docker)
- [x] Продакшн-стек `docker-compose.server.yml`: gunicorn, nginx стеку на `127.0.0.12:8000`, healthcheck-и, `deploy.sh` з `--wait`
- [x] Файли працівників — у volume з перевіркою прав (`MediaView`; раніше в dev `/media/` віддавався без перевірки)
- [x] `GET /api/health` (Next → Django → БД і Redis) для моніторингу
- [x] Бекапи БД і файлів (перед кожним деплоєм і щодня), `restore.sh`; `docs/deploy.md`
- [ ] Налаштувати сервер за `docs/deploy.md` і ввімкнути деплой (`START: "1"` у `deploy.yml`)

## ✅ Крок 8 — Продакшн

- [x] gunicorn, Nginx, HTTPS (Let's Encrypt), `SECURE_SSL_REDIRECT`, HSTS, `collectstatic` — gunicorn, nginx стеку і HSTS ✅ (крок 7); HTTPS — через Cloudflare, certbot не потрібен (окремий пункт нижче); `SECURE_SSL_REDIRECT` і `collectstatic` не потрібні: на HTTPS переводить Cloudflare, Django назовні статику не віддає
- [ ] На сервері: HTTPS через Cloudflare — SSL Full (strict) + Origin CA-сертифікат на nginx хоста, справжній IP клієнта (`real_ip` з діапазонів Cloudflare, `CF-Connecting-IP`), Rocket Loader вимкнено, конфіг nginx хоста (`proxy_pass` на `127.0.0.12:8000`, `X-Forwarded-Proto https`) — див. `docs/deploy.md`, крок 4
- [x] S3: приватний бакет + IAM-роль сервера (`GetObject` / `PutObject` / `DeleteObject` на `employees/*`) → не потрібно: файли у Docker volume на Hetzner (крок 7)
- [x] Redis-кеш дозволів між запитами
- [x] Довгий випадковий `SECRET_KEY` (шаблон `.env.production.example`; `check --deploy` без попереджень — у тестах)
- [x] Копія бекапів поза сервером (Hetzner Storage Box: `rsync` / `borg`) → restic у Docker (`scripts/offsite_backup.sh`): шифрування, дедуплікація, ротація 14/8/12, щоденний `check`; випадкове стирання на сервері не дзеркалиться (без `rsync --delete`), від зловмисника з доступом до сервера — snapshots Storage Box
- [x] Пінг моніторингу після успішного бекапу (`BACKUP_PING_URL`, напр. healthchecks.io)
- [x] Ліміти в Django: вхід — на email (10/год), AI-асистент — на користувача (10/хв, 200/день), загальний — 600/хв на користувача; українське повідомлення 429
- [x] Sentry (за `SENTRY_DSN`): без тіл запитів, локальних змінних і даних користувачів; release = git SHA
- [x] Постійні з'єднання з БД (`CONN_MAX_AGE`, `CONN_HEALTH_CHECKS`)
- [x] Заголовки безпеки фронту: CSP, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`
- [ ] На сервері: Storage Box з SSH і snapshots, `restic.env`, `offsite_backup.sh init` (див. `docs/deploy.md`)
- [ ] Підняти HSTS до 31536000, коли HTTPS кілька днів працює (`nginx.conf` і `.env`) — після запуску

## ✅ Крок 9 — Документація

- [x] Переписати `README.md` (зараз — чужий шаблон): огляд, архітектура, запуск, тести, структура
- [x] Оновити `docs/summary.md`: поточний стан модулів, архітектура, безпека, що лишилось
- [x] Описати модель доступу для HR / адміністраторів (`docs/access.md`)
- [x] `docs/deploy.md` — сервер, деплой, бекапи (кроки 7–8); `frontend/README.md` — файли і заголовки безпеки

---

## ✅ Технічний борг

- [x] `StructuralUnit.children_count` оголошено, але не заповнюється
- [x] Перевірка зарплати в списках для scoped-ролей — запит на кожен рядок
- [x] Зарплата без валюти
- [x] `psycopg2-binary` → `psycopg[binary]`
- [x] N+1 запитів предків підрозділу у списках (знайдено під час ревізії)
- [x] `.gitignore`: правило `lib/` з Python-шаблону ховало `frontend/src/lib/` — тепер `/lib/`

---

## Пізніше

React (web) → Крок 3; Flutter (mobile), Slack-бот, Google Calendar

- [x] Slack-бот (`apps/slack`), сповіщення в особисті: нова заявка на відпустку — тим, хто розглядає; рішення / скасування — працівнику; запрошення. Нагадування з cron: заявки на розгляді (09:30), відмітка в табелі (11:00, не у свята й відпустку), не частіше разу на день. Лише вихідні запити, люди — за email
- [ ] Slack: кнопки «Схвалити / Відхилити» і slash-команди (потрібен публічний ендпоінт з перевіркою підпису Slack)
- [ ] На сервері: Slack-застосунок, `SLACK_BOT_TOKEN`, `setup_reminders_cron.sh`
- [ ] Flutter (mobile)
- [ ] Google Calendar
