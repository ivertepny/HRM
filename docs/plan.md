# План розвитку HRM-системи

## Поточний стан

Проект має базову архітектуру:
- ✅ Аутентифікація (JWT, реєстрація, логін, логаут)
- ✅ Модель користувача (`User`) на основі email
- ✅ Модель працівника (`Employee`) з `HistoricalRecords`
- ✅ Організаційна структура (`StructuralUnit`, MPTT-дерево)
- ✅ AI-асистент (OpenAI GPT-4o-mini, чат-сесії)
- ✅ Swagger / OpenAPI (drf-spectacular)
- ✅ Docker + docker-compose
- ✅ AWS S3 підготовлено (django-storages, boto3)

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

## Крок 2 — Гнучка IAM-подібна система ролей і дозволів

> **Концепція:** замість 3 хардкодних ролей — динамічна система.  
> Дозволи задаються рядками `resource:action` (наприклад `employees:read`, `salary:write`).  
> Ролі — це іменовані набори дозволів. Користувач може мати кілька ролей.  
> Scope дозволу може бути обмежений конкретним `StructuralUnit`.

### 2.1 — Новий застосунок `permissions`

- [ ] Створити `permissions` app (`python manage.py startapp permissions`)
- [ ] Модель **`Permission`**:
  - `resource` — рядок (`employees`, `salary`, `company`, `ai`, `vacations`, `equipment`, `attendance`)
  - `action` — рядок (`read`, `write`, `delete`, `manage`)
  - `description` — людиночитаний опис
  - `codename` — унікальний рядок `resource:action` (авто-генерується)
- [ ] Модель **`Role`**:
  - `name` — назва ролі (наприклад: `HR Manager`, `Recruiter`, `Team Lead`)
  - `description`
  - `permissions` — M2M → `Permission`
  - `is_system` — захист від видалення системних ролей
- [ ] Модель **`UserRole`**:
  - `user` — FK → `User`
  - `role` — FK → `Role`
  - `structural_unit` — FK → `StructuralUnit` (nullable) — scope: якщо заданий, роль діє тільки в межах цього підрозділу та його нащадків
  - `granted_by` — FK → `User` — хто призначив
  - `expires_at` — DateTimeField (nullable) — тимчасові ролі

### 2.2 — Backend перевірки

- [ ] Метод `user.get_permissions(structural_unit=None)` — повертає `set` рядків `resource:action` для даного контексту (глобальні + scope для підрозділу)
- [ ] Кастомний DRF permission **`HasPermission("resource:action")`** — замінює `IsAuthenticated` у всіх views
- [ ] Scope-перевірка: при доступі до об'єкта конкретного підрозділу — враховувати `UserRole.structural_unit`
- [ ] Endpoint `GET /api/users/me/permissions/` — повертає всі активні дозволи поточного юзера

### 2.3 — Seed: системні ролі з коробки

Три дефолтних ролі через `management command` (`python manage.py seed_roles`):

| Роль | Дозволи |
|------|---------|
| `System Admin` | `*:*` (всі ресурси, всі дії) |
| `HR Manager` | `employees:*`, `salary:*`, `vacations:manage`, `equipment:manage`, `attendance:read`, `company:read` |
| `Employee` | `employees:read` (тільки свій профіль), `salary:read` (тільки своя), `vacations:write` (подати заявку), `ai:use` |

### 2.4 — Endpoints

- [ ] `GET/POST /api/roles/` — список ролей, створення (тільки System Admin)
- [ ] `GET/PATCH/DELETE /api/roles/{id}/` — деталі, редагування, видалення
- [ ] `GET/POST /api/roles/{id}/permissions/` — дозволи ролі
- [ ] `GET/POST /api/users/{id}/roles/` — ролі користувача, призначення ролі
- [ ] `DELETE /api/users/{id}/roles/{role_id}/` — зняти роль
- [ ] `GET /api/permissions/` — каталог всіх дозволів (тільки читання)

### 2.5 — Кешування дозволів

- [ ] Дозволи кешувати в `request`-об'єкті на час одного запиту (уникнути N+1 запитів до БД)
- [ ] При зміні `UserRole` — інвалідувати кеш (сигнал `post_save`)
- [ ] **Пізніше (Крок 9):** мігрувати кеш у Redis для горизонтального масштабування

---

## Крок 3 — Розширити модель Employee

За специфікацією в базі має зберігатись:

- [ ] `birth_date` — дата народження
- [ ] `photo` — фотографія (AWS S3)
- [ ] `salary` (з `HistoricalRecords`) — зарплата + повна історія змін
- [ ] `level` — рівень: `Trainee` / `Junior` / `Middle` / `Senior` + повна історія змін
- [ ] `documents` — можливість завантажити файл (AWS S3)
- [ ] Активувати `CareerHistory` — зберігати повну історію посад та підрозділів

---

## Крок 4 — Модуль відпусток (`vacations` app)

- [ ] Створити застосунок `vacations`
- [ ] Модель `VacationRequest`:
  - `employee`, `date_start`, `date_end`
  - `status`: `pending` / `approved` / `rejected`
  - `approved_by` (FK → User)
  - `HistoricalRecords` — повна історія відпусток за весь період роботи
- [ ] API endpoints:
  - Працівник подає заявку
  - HR / Адмін схвалює або відхиляє
  - Перегляд всіх відпусток по співробітнику

---

## Крок 5 — Модуль обладнання (`equipment` app)

- [ ] Створити застосунок `equipment`
- [ ] Модель `Equipment`:
  - `serial_number` — унікальний реєстраційний номер
  - `name`, `description`, `status`: `in_stock` / `assigned`
- [ ] Модель `EquipmentAssignment`:
  - `equipment` (OneToOne), `employee`, `date_assigned`, `date_returned`
- [ ] Валідація: одиниця обладнання не може бути у двох працівників одночасно
- [ ] Обладнання без призначення автоматично вважається **"на складі"**

---

## Крок 6 — Тайм-трекінг (`attendance` app)

- [ ] Створити застосунок `attendance`
- [ ] Модель `AttendanceRecord`:
  - `employee`, `date`, `time_start`, `time_end`
  - `status`: `remote` / `office` / `off`
- [ ] API для відмітки присутності
- [ ] Агрегований звіт по місяцях для HR-аналітики

---

## Крок 7 — Скидання пароля через email

- [ ] Налаштувати email-бекенд (SMTP або AWS SES)
- [ ] Endpoints: `password-reset/` → `password-reset/confirm/`
- [ ] Використати вбудований механізм `django.contrib.auth`

---

## Крок 8 — CI/CD (GitHub Actions)

- [ ] Створити `.github/workflows/ci.yml`:
  - `ruff check` + `ruff format --check` при кожному PR
  - `pytest` з coverage
  - Build Docker image
- [ ] Deploy workflow: push у `main` → деплой на VPS / AWS

---

## Крок 9 — Продакшн-готовність

- [ ] Nginx як реверс-проксі (за архітектурою)
- [ ] HTTPS через Let's Encrypt
- [ ] Налаштувати `STATIC_ROOT` + `collectstatic` у Docker
- [ ] Замінити `psycopg2-binary` на `psycopg[binary]` (psycopg3, вже є в `pyproject.toml`)
- [ ] Встановити `DEBUG=False` та перевірити `ALLOWED_HOSTS` у prod

---

## Додаткові міркування

| Тема | Статус |
|------|--------|
| **Streamlit** (`frontend/streamlit_app.py`) | Тимчасовий прототип; фінальний фронт — React (за архітектурою). Можна залишити для внутрішньої HR-аналітики |
| **Mobile (Flutter)** | Авторизація, профіль, відпустки, присутність, Push-сповіщення |
| **Slack Bot** | Webhook: подача на відпустку, нагадування |
| **Google Calendar API** | Синхронізація відпусток та подій |
| **Graphviz** | Вже є в залежностях — візуалізація org-структури готова до реалізації |

