# План розвитку HRM-системи

> Оновлено: 31.10.2026

## Поточний стан

- ✅ Тулінг: uv + ruff, Python 3.14, Docker на `python:3.14-slim`
- ✅ Структура `config/` (settings `base` / `dev` / `prod` / `test`) + `apps/`
- ✅ Аутентифікація: JWT (access 30 хв, refresh 7 днів з ротацією і blacklist), `token/refresh/`, `me/`
- ✅ Ролі та дозволи (`apps/access`): `resource:action`, wildcard-и, scope на підрозділ, тимчасові ролі
- ✅ Дозволи застосовані до всіх наявних ендпоінтів; власні дані доступні завжди
- ✅ Працівник: рівень, зарплата, дата народження, фото, документи; автоматичний кадровий журнал
- ✅ Оргструктура (`StructuralUnit`, MPTT): soft-delete, валідація дерева через API, історія змін з автором
- ✅ AI-асистент (OpenAI GPT-4o-mini) — працює, але потребує рефакторингу (Крок 3.5)
- ✅ Основа API: пагінація, глобальний обробник помилок, CORS, Swagger / ReDoc
- ✅ Тести: pytest + factory_boy, 143 тести, покриття ~93%

---

## Крок 1 — Виправити критичні проблеми ✅ *виконано*

| # | Задача | Файл | Статус |
|---|--------|------|--------|
| 1.1 | Прибрати `'spacy'` з `INSTALLED_APPS` | `HRM_NEW/settings.py` | ✅ |
| 1.2 | Замінити `AllowAny` → `IsAuthenticated` в усіх `views.py` | `employees`, `users`, `company` | ✅ |
| 1.3 | Виправити `__str__` у `Employee` | `employees/models.py` | ✅ |
| 1.4 | Розкоментувати `CareerHistory` модель, серіалізатор, `ViewSet`, маршрут | `employees/*` | ✅ |
| 1.5 | Прибрати `spacy` з `openai_service.py`, замінити на keyword-пошук | `ai_assistant/openai_service.py` | ✅ |

---

## Крок 1.5 — Стабілізація фундаменту ✅ *виконано*

| # | Задача | Статус |
|---|--------|--------|
| 1.6 | uv + ruff, Python 3.14; Dockerfile на uv (`uv sync --frozen`), healthcheck БД у compose, прибрано `requirements.txt` | ✅ |
| 1.7 | `HRM_NEW/` → `config/`, застосунки → `apps/`; settings `base` / `dev` / `prod` / `test` через `django-environ` (`DEBUG` — справжній `bool`) | ✅ |
| 1.8 | Перегенеровано міграції (у `users` і `ai_assistant` їх не було — чиста БД не розгорталась) | ✅ |
| 1.9 | Пагінація (20 / `?page_size` до 100), глобальний обробник помилок (400 / 409 замість 500), CORS, `HistoryRequestMiddleware` | ✅ |
| 1.10 | pytest + factory_boy, тестові settings, фікстури `auth_client` / `client_as` / `grant` | ✅ |

---

## Крок 2 — Гнучка IAM-подібна система ролей і дозволів ✅ *виконано*

> **Концепція:** замість 3 хардкодних ролей — динамічна система.
> Дозволи задаються рядками `resource:action` (наприклад `employees:read`, `salary:write`).
> Ролі — це іменовані набори дозволів. Користувач може мати кілька ролей.
> Scope дозволу може бути обмежений конкретним `StructuralUnit`.

### 2.1 — Застосунок `access`

- [x] Застосунок названо `access` (а не `permissions`), щоб не плутати з `rest_framework.permissions` і `auth.Permission`
- [x] **`Permission`**: `resource`, `action`, `description`, `codename` (авто). Каталог — у коді (`apps/access/catalog.py`), включно з wildcard-ами `resource:*` і `*:*`
- [x] **`Role`**: `name`, `description`, `permissions` (M2M), `is_system` (не можна видалити чи перейменувати)
- [x] **`UserRole`**: `user`, `role`, `structural_unit` (scope: підрозділ + нащадки), `granted_by`, `expires_at`, історія змін (аудит видачі / відкликання)

### 2.2 — Backend перевірки

- [x] Сервіс `UserAccess` (замість `user.get_permissions()`): `has(codename, unit)`, `has_anywhere()`, `units_for()` — для фільтрації списків
- [x] DRF permission **`HasPermission`** — дозволи задаються у view через `required_permissions` (`action` → метод → `read` / `write` → `*`); без відповідного дозволу — заборонено
- [x] Scope-перевірка на рівні об'єкта (`obj.structural_unit` або `view.get_permission_unit()`)
- [x] Захист від ескалації: не можна створити, видати чи відкликати роль з дозволами, яких немає у вас самих
- [x] `GET /api/users/me/permissions/` — глобальні дозволи, дозволи по підрозділах, активні ролі
- [x] Superuser має всі дозволи

### 2.3 — Seed: системні ролі з коробки

`python manage.py seed_roles` (ідемпотентна; `--reset-system-roles`, `--prune`; запускається при старті контейнера і через `.\dev.ps1 seed`):

| Роль | Дозволи |
|------|---------|
| `System Admin` | `*:*` |
| `HR Manager` | `employees:*`, `salary:*`, `documents:*`, `users:read`, `company:read`, `vacations:manage`, `equipment:manage`, `attendance:read`, `ai:use` |
| `Employee` | `employees:read`, `company:read`, `vacations:write`, `ai:use` |

> Власні дані (профіль, своя зарплата, кар'єрна історія, документи) доступні **завжди, без дозволів** — тому в `Employee` немає `salary:read`: він відкрив би чужі зарплати.
> Роль `Employee` автоматично видається кожному новому користувачу.

### 2.4 — Endpoints

Спрощено до плоских ресурсів під `/api/access/`:

- [x] `GET /api/access/permissions/` — каталог дозволів
- [x] `GET/POST/PATCH/DELETE /api/access/roles/` — ролі (дозволи ролі — поле `permissions`)
- [x] `GET/POST/DELETE /api/access/user-roles/` — призначення (фільтри `?user=`, `?role=`, `?structural_unit=`); змінити не можна — лише відкликати і видати нове
- [x] Адмінка для ролей і призначень

### 2.5 — Кешування дозволів

- [x] Дозволи завантажуються одним запитом і кешуються на час HTTP-запиту
- [ ] **Пізніше (Крок 9):** Redis-кеш між запитами + інвалідація при зміні `UserRole` / `Role`

### 2.6 — Застосування дозволів до наявних модулів ✅

| Модуль | Дозволи | Особливості |
|--------|---------|-------------|
| `users` | `users:read` / `write` / `delete` | Реєстрація лише з `users:write` + валідатори пароля; себе видно завжди; змінити можна лише своє ім'я; не можна видалити себе |
| `employees`, `positions`, `career-history` | `employees:read` / `write` / `delete` | Переведення і прийом — лише в підрозділ зі scope |
| зарплата | `salary:read` / `write` | Без `salary:read` поле `salary` не повертається; `employees:write` не дає права змінювати зарплату |
| `documents` | `documents:read` / `write` / `delete` | Свої документи — лише перегляд |
| `company` | `company:read` / `write` / `delete` | Кореневий підрозділ — лише з глобальним `company:write` |
| `ai` | `ai:use` | — |

Scoped-ролі звужують списки до піддерева; чужі об'єкти повертають 404.

---

## Крок 3 — Розширити модель Employee ✅ *виконано*

- [x] `birth_date` — дата народження
- [x] `photo` — фото (UUID-імена файлів; dev — `media/`, prod — S3)
- [x] `salary` — поточна зарплата в `Employee` (історія — через `CareerHistory` і `HistoricalRecords`)
- [x] `level` — `Trainee` / `Junior` / `Middle` / `Senior`
- [x] `EmployeeDocument` — CV / NDA / договір / інше; whitelist розширень, ліміт 10 МБ; `/api/employees/documents/`
- [x] `CareerHistory` — **автоматичний журнал тільки для читання**: прийом, зміна посади / підрозділу / рівня / зарплати, звільнення; знімок стану + причина (`change_reason`), дата (`effective_date`), автор
- [x] `on_delete=PROTECT` для `user`, `position`, `structural_unit` (раніше видалення посади видаляло працівників)
- [x] `StructuralUnit.clean()` реально викликається з API (`ModelCleanMixin`); виправлено перевірки циклу, глибини, унікальності коренів

---

## Крок 3.5 — Рефакторинг AI-асистента ⏭ *наступний*

- [ ] Сесії чату — у БД за `session_id` з запиту, а не в Django session (cookie): з JWT-клієнтами (React / Flutter) кожен запит зараз відкриває нову сесію
- [ ] Виправити `chat/reset` (створює `ChatSession` без `session_id` → другий виклик падає з `IntegrityError`)
- [ ] Застосувати `MAX_HISTORY_AI` — історія зараз росте без обмежень
- [ ] OpenAI-клієнт — ліниво, при першому запиті; таймаути та обробка помилок API (503 замість 500)
- [ ] Відповідь про структуру — з урахуванням прав (`company:read` і scope)
- [ ] Прибрати дублювання `ChatSession.conversation` / `AIQuery`
- [ ] Виправити попередження drf-spectacular для AI-views

---

## Крок 4 — Модуль відпусток (`vacations` app)

> Дозволи `vacations:read` / `write` / `manage` вже є в каталозі і в системних ролях.

- [ ] Створити застосунок `vacations`
- [ ] Модель `VacationRequest`:
  - `employee`, `date_start`, `date_end`
  - `status`: `pending` / `approved` / `rejected`
  - `approved_by` (FK → User)
  - `HistoricalRecords` — повна історія відпусток за весь період роботи
- [ ] Валідація: `date_end >= date_start`, без перетину з іншими схваленими відпустками
- [ ] API endpoints:
  - Працівник подає заявку (`vacations:write`, лише за себе)
  - HR / керівник схвалює або відхиляє (`vacations:manage`, у межах scope)
  - Перегляд відпусток по співробітнику (свої — завжди)

---

## Крок 5 — Модуль обладнання (`equipment` app)

> Дозволи `equipment:read` / `manage` вже є в каталозі.

- [ ] Створити застосунок `equipment`
- [ ] Модель `Equipment`:
  - `serial_number` — унікальний реєстраційний номер
  - `name`, `description`, `status`: `in_stock` / `assigned`
- [ ] Модель `EquipmentAssignment`:
  - `equipment`, `employee`, `date_assigned`, `date_returned`
- [ ] Валідація: одиниця обладнання не може бути у двох працівників одночасно (partial unique constraint на активне призначення)
- [ ] Обладнання без призначення автоматично вважається **"на складі"**
- [ ] Працівник бачить своє обладнання без дозволів

---

## Крок 6 — Тайм-трекінг (`attendance` app)

> Дозволи `attendance:read` / `write` вже є в каталозі.

- [ ] Створити застосунок `attendance`
- [ ] Модель `AttendanceRecord`:
  - `employee`, `date`, `time_start`, `time_end`
  - `status`: `remote` / `office` / `off`
- [ ] API для відмітки присутності (за себе)
- [ ] Агрегований звіт по місяцях для HR-аналітики (з урахуванням scope)

---

## Крок 7 — Скидання пароля через email

- [ ] Email-бекенд: AWS SES (доступ лише через IAM-роль) або SMTP для dev
- [ ] Endpoints: `password-reset/` → `password-reset/confirm/`
- [ ] Використати вбудований механізм `django.contrib.auth` (токени `PasswordResetTokenGenerator`)
- [ ] Лист-запрошення для нових користувачів замість пароля, який задає HR

---

## Крок 8 — CI/CD (GitHub Actions)

- [ ] Створити `.github/workflows/ci.yml`:
  - `ruff check` + `ruff format --check` при кожному PR
  - `pytest` з coverage на PostgreSQL (service container)
  - `manage.py spectacular --validate`
  - Build Docker image
- [ ] Deploy workflow: push у `main` → деплой на VPS / AWS
- [ ] Доступ до AWS з CI — лише GitHub OIDC + assume-role, **без статичних ключів**

---

## Крок 9 — Продакшн-готовність

- [ ] Nginx як реверс-проксі (за архітектурою)
- [ ] HTTPS через Let's Encrypt; `SECURE_SSL_REDIRECT`, HSTS
- [ ] gunicorn замість `runserver`; окремий prod-образ / команда запуску
- [ ] `collectstatic` у Docker (`STATIC_ROOT` уже налаштовано)
- [x] `DEBUG=False` і обов'язковий `ALLOWED_HOSTS` у `config.settings.prod`
- [ ] **S3 для файлів працівників** (код готовий, відкладено до деплою):
  - приватний бакет, Block Public Access
  - IAM-роль сервера з `s3:GetObject` / `PutObject` / `DeleteObject` на `employees/*`
  - **жодних** `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — prod-settings відмовляються стартувати, якщо вони є
- [ ] Redis-кеш дозволів між запитами (див. 2.5)
- [ ] Розглянути перехід `psycopg2-binary` → `psycopg[binary]` (psycopg3)
- [ ] Довгий випадковий `SECRET_KEY` для prod

---

## Крок 10 — Документація

- [ ] Переписати `README.md` (зараз — чужий шаблон про стартапи та інвесторів): опис, запуск, `.env`, тести
- [ ] Оновити `docs/summary.md` під нову структуру і ендпоінти
- [ ] Описати модель доступу (ролі, scope, власні дані) для HR / адміністраторів

---

## Відомі обмеження і технічний борг

| # | Проблема | Де закривається |
|---|----------|-----------------|
| Т1 | AI повертає всю оргструктуру без урахування scope | Крок 3.5 |
| Т2 | Працівник не може сам змінити своє фото / дату народження | За потреби — окремо |
| Т3 | Сума зарплати без валюти | За потреби — окремо |
| Т4 | `StructuralUnit.children_count` оголошено, але не заповнюється | Окремо |
| Т5 | Перевірка scope по об'єктах у списках робить запит на кожен рядок для scoped-ролей | Крок 9 (кеш) |

---

## Додаткові міркування

| Тема | Статус |
|------|--------|
| **Frontend (React)** | Основний веб-клієнт; CORS для `localhost:3000` / `5173` уже налаштовано в dev |
| **Mobile (Flutter)** | Авторизація, профіль, відпустки, присутність, Push-сповіщення |
| **Slack Bot** | Webhook: подача на відпустку, нагадування |
| **Google Calendar API** | Синхронізація відпусток та подій |
| **Graphviz** | ✅ Реалізовано: `GET /api/company/units/{id}/diagram/` (SVG) |
| **Streamlit** | Прототипу в репозиторії немає — пункт прибрано з активних |
