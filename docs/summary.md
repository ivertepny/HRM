# HRM-система — Зведений документ для консультанта

> **Станом на:** 30 червня 2026  
> **Призначення документа:** передача контексту зовнішньому консультанту — поточний стан проекту, технічний стек, що вже реалізовано і що планується.

---

## 1. Що це за продукт

**HRM-система** (Human Resource Management) — внутрішній корпоративний інструмент для управління персоналом.

**Ключові задачі системи:**
- Ведення бази працівників (профіль, посада, підрозділ, рівень, зарплата, документи)
- Управління організаційною структурою компанії (ієрархія підрозділів)
- Облік відпусток: подача заявок → схвалення керівником
- Облік обладнання компанії (що на складі, що у кого)
- Тайм-трекінг (присутність: офіс / remote / вихідний)
- AI-асистент для HR-відповідей (OpenAI GPT-4o-mini)

---

## 2. Технічний стек

| Компонент | Технологія |
|-----------|-----------|
| **Backend** | Python 3.14, Django 5.2, Django REST Framework 3.16 |
| **База даних** | PostgreSQL (psycopg2) |
| **Аутентифікація** | JWT (djangorestframework-simplejwt), blacklist токенів |
| **API документація** | Swagger / ReDoc (drf-spectacular) |
| **Організаційне дерево** | django-mptt (Modified Preorder Tree Traversal) |
| **Історія змін** | django-simple-history (всі критичні моделі) |
| **Файлове сховище** | AWS S3 (django-storages + boto3) |
| **AI** | OpenAI API (GPT-4o-mini), tiktoken для підрахунку токенів |
| **Менеджер пакетів** | uv (з `pyproject.toml` та `uv.lock`) |
| **Лінтер / форматер** | Ruff |
| **Тести** | pytest + pytest-django + pytest-cov |
| **Контейнеризація** | Docker + docker-compose |
| **Reverse proxy (план)** | Nginx |
| **CI/CD (план)** | GitHub Actions → VPS / AWS |
| **Фронтенд (план)** | React (Web), Flutter (Mobile) |

---

## 3. Поточна структура проекту

```
HRM_NEW/
├── HRM_NEW/          — конфігурація Django (settings, urls, wsgi, asgi)
├── users/            — кастомна модель User (email-based auth, JWT)
├── employees/        — Employee, Position, CareerHistory
├── company/          — StructuralUnit (MPTT-дерево підрозділів)
├── ai_assistant/     — AI-чат (OpenAI GPT-4o-mini, ChatSession, AIQuery)
├── docs/             — документація (plan.md, summary.md)
├── pyproject.toml    — залежності та налаштування (uv)
├── uv.lock           — lock-файл залежностей
├── docker-compose.yml
├── Dockerfile
└── dev.ps1           — PowerShell-скрипт задач розробки (замість Makefile)
```

---

## 4. Реалізовано (поточний стан)

### 4.1 Аутентифікація та користувачі (`users`)
- Кастомна модель `User`: email як логін, ім'я, прізвище, статус (active/inactive)
- JWT-аутентифікація: `Bearer` токен, access (3 дні) + refresh (7 днів), ротація токенів, blacklist
- Endpoints: `POST /api/users/register/`, `POST /api/users/login/`, `POST /api/users/logout/`
- Перегляд і редагування: `GET /api/users/`, `GET/PATCH/DELETE /api/users/{id}/`

### 4.2 Працівники (`employees`)
- Модель `Employee`: OneToOne → User, посада, підрозділ, дата прийому/звільнення, `HistoricalRecords`
- Модель `Position`: унікальна назва посади
- Модель `CareerHistory`: дата, посада, підрозділ, зарплата — повна кар'єрна історія
- Endpoints (ViewSet): `GET/POST /api/employees/employees/`, `GET/PATCH/DELETE /api/employees/employees/{id}/`
- Аналогічно для `positions` та `career-history`

### 4.3 Організаційна структура (`company`)
- Модель `StructuralUnit`: MPTT-дерево (необмежена вкладеність), `custom_type` (Офіс / Департамент / тощо)
- Soft-delete з каскадом: деактивація підрозділу деактивує всіх нащадків
- Валідація: унікальність імені серед дітей, захист від циклічних зв'язків
- `HistoricalRecords` для відстеження змін структури
- Endpoint: `GET/POST /api/company/units/`

### 4.4 AI-асистент (`ai_assistant`)
- Ізольовані чат-сесії по UUID (прив'язані до user — не можна зайти в чужу сесію)
- Якщо запит стосується структури компанії (`структур`, `підрозділ`, `відділ` тощо) — повертає дані з БД без виклику OpenAI (економія токенів)
- Зберігання діалогу: `ChatSession` (JSON conversation) + `AIQuery` (кожне повідомлення окремо)
- Контроль токенів: `tiktoken`, ліміт на вхідне повідомлення

### 4.5 Інфраструктура
- PostgreSQL через docker-compose
- `dev.ps1` — всі задачі розробки: `install`, `run`, `migrate`, `lint`, `fmt`, `fix`, `test`, `test-cov`, `docker-up/down/logs`
- Swagger UI: `GET /api/schema/swagger-ui/`
- ReDoc: `GET /api/schema/redoc/`

---

## 5. Що НЕ реалізовано (заплановано)

### 5.1 Система ролей і дозволів (Крок 2) — **наступний пріоритет**

Замість хардкодних ролей — **гнучка IAM-подібна система**:

- Дозволи задаються рядками `resource:action` (наприклад: `employees:read`, `salary:write`, `vacations:manage`)
- **Роль** = іменований набір дозволів (створюється динамічно, не захардкоджено)
- Користувач може мати **декілька ролей**
- Scope: роль може бути обмежена конкретним підрозділом (`StructuralUnit`) — наприклад Team Lead бачить тільки свій відділ
- Тимчасові ролі (`expires_at`)
- Seed-команда з 3 системними ролями за замовчуванням:

| Роль | Дозволи |
|------|---------|
| `System Admin` | всі ресурси, всі дії |
| `HR Manager` | employees, salary, vacations, equipment, attendance, company (читання) |
| `Employee` | власний профіль, власна зарплата, подача на відпустку, AI |

### 5.2 Розширення профілю працівника (Крок 3)

Додати до `Employee`:
- `birth_date` — дата народження
- `photo` — фото (AWS S3)
- `salary` + `HistoricalRecords` — зарплата з повною історією змін
- `level` (Trainee / Junior / Middle / Senior) + `HistoricalRecords`
- `documents` — завантаження файлів (CV, NDA тощо, AWS S3)

### 5.3 Модуль відпусток — новий застосунок `vacations` (Крок 4)

- `VacationRequest`: працівник, дати початку/кінця, статус (pending/approved/rejected), хто схвалив, `HistoricalRecords`
- Workflow: працівник подає → HR/Адмін схвалює або відхиляє
- Повна історія відпусток за весь період роботи

### 5.4 Модуль обладнання — новий застосунок `equipment` (Крок 5)

- `Equipment`: унікальний серійний номер, назва, статус (in_stock / assigned)
- `EquipmentAssignment`: обладнання → працівник, дати призначення та повернення
- Валідація: одна одиниця обладнання не може бути у двох працівників одночасно
- Обладнання без призначення = на складі

### 5.5 Тайм-трекінг — новий застосунок `attendance` (Крок 6)

- `AttendanceRecord`: працівник, дата, час початку/завершення, статус (remote/office/off)
- API для відмітки присутності
- Агрегований звіт по місяцях

### 5.6 Скидання пароля через email (Крок 7)

- Email-бекенд (SMTP або AWS SES)
- Стандартний Django flow: `password-reset/` → підтвердження через посилання

### 5.7 CI/CD (Крок 8)

- GitHub Actions: lint + tests при PR, Docker build при push у `main`
- Deploy workflow → VPS / AWS

### 5.8 Продакшн-готовність (Крок 9)

- Nginx як reverse proxy
- HTTPS (Let's Encrypt)
- `collectstatic` у Docker
- `DEBUG=False`, перевірка `ALLOWED_HOSTS`
- Кеш дозволів у Redis

---

## 6. Інтеграції (заплановані)

| Інтеграція | Опис |
|-----------|------|
| **Slack Bot** | Webhook: подача на відпустку, нагадування |
| **Google Calendar API** | Синхронізація відпусток та подій |
| **React (Web)** | Основний фронтенд (замінить поточний Swagger UI для кінцевих юзерів) |
| **Flutter (Mobile)** | Авторизація, профіль, відпустки, присутність, Push-сповіщення |
| **Graphviz** | Вже є в залежностях — візуалізація org-структури |

---

## 7. Відомі технічні борги

| # | Проблема | Де |
|---|----------|----|
| 7.1 | `graphviz` є в `INSTALLED_APPS`, але це не Django-застосунок — треба прибрати | `settings.py` рядок 33 |
| 7.2 | JWT `ACCESS_TOKEN_LIFETIME = 3 дні` — занадто довго для продакшну (рекомендовано 15–60 хв) | `settings.py` |
| 7.3 | `DEBUG = os.getenv('DEBUG')` повертає рядок `"False"` (truthy!) замість `bool` — небезпечно в prod | `settings.py` |
| 7.4 | Всі views ще не захищені дозволами (тільки `IsAuthenticated`) — буде виправлено в Кроку 2 | всі `views.py` |
| 7.5 | Відсутні тести (файли `tests.py` порожні) | всі застосунки |
| 7.6 | `STATIC_ROOT` не налаштовано — `collectstatic` не спрацює | `settings.py` |

---

## 8. API — поточні endpoints

| Метод | URL | Опис |
|-------|-----|------|
| `POST` | `/api/users/register/` | Реєстрація |
| `POST` | `/api/users/login/` | Вхід (повертає JWT) |
| `POST` | `/api/users/logout/` | Вихід (blacklist токена) |
| `GET` | `/api/users/` | Список користувачів |
| `GET/PATCH/DELETE` | `/api/users/{id}/` | Деталі користувача |
| `GET/POST` | `/api/employees/employees/` | Список / створення працівників |
| `GET/PATCH/DELETE` | `/api/employees/employees/{id}/` | Деталі працівника |
| `GET/POST` | `/api/employees/positions/` | Посади |
| `GET/POST` | `/api/employees/career-history/` | Кар'єрна історія |
| `GET/POST` | `/api/company/units/` | Підрозділи (дерево) |
| `POST` | `/api/ai/ask/` | Запит до AI-асистента |
| `GET` | `/api/schema/swagger-ui/` | Swagger UI |
| `GET` | `/api/schema/redoc/` | ReDoc |

---

## 9. Запуск проекту локально

```powershell
# 1. Встановити залежності
uv sync --group dev

# 2. Запустити PostgreSQL (через Docker)
.\dev.ps1 docker-up

# 3. Міграції
.\dev.ps1 migrate

# 4. Запустити сервер
.\dev.ps1 run
# → http://localhost:8000/api/schema/swagger-ui/
```

**.env файл** (потрібен у корені проекту):
```
SECRET_KEY=...
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=hrm_db
POSTGRES_USER=hrm_user
POSTGRES_PASSWORD=...
POSTGRES_HOST=db
POSTGRES_PORT=5432
OPENAI_API_KEY=...
IN_DOCKER=False
```

