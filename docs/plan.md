# План розвитку HRM-системи

> Оновлено: 31.10.2026

## ✅ Зроблено

- [x] Тулінг: uv + ruff, Python 3.14, Docker на uv
- [x] Структура `config/` (settings `base` / `dev` / `prod` / `test`) + `apps/`, міграції з нуля
- [x] Основа API: пагінація, глобальний обробник помилок, CORS, JWT refresh (access 30 хв), Swagger
- [x] Тести: pytest + factory_boy (143 тести, ~93%)
- [x] Ролі та дозволи (`apps/access`): `resource:action` з wildcard-ами, scope на підрозділ, тимчасові ролі, захист від ескалації, `seed_roles` (System Admin / HR Manager / Employee)
- [x] Дозволи на всіх ендпоінтах; власні дані доступні завжди; зарплата — окремо через `salary:read` / `write`; реєстрація лише через HR
- [x] Працівник: рівень, зарплата, дата народження, фото, документи; автоматичний кадровий журнал (`CareerHistory`); `PROTECT` замість `CASCADE`
- [x] Оргструктура: валідація дерева через API, історія змін з автором, SVG-діаграма
- [x] S3 для файлів у prod — лише через IAM-роль (код готовий, підключення — при деплої)

---

## ⏭ Крок 1 — Рефакторинг AI-асистента

- [ ] Сесії чату в БД за `session_id` з запиту, а не в cookie-сесії (не працює з JWT-клієнтами)
- [ ] Виправити `chat/reset` (другий виклик падає з `IntegrityError`)
- [ ] Обмежити історію (`MAX_HISTORY_AI`)
- [ ] OpenAI-клієнт ліниво; таймаути, 503 при збої API
- [ ] Відповідь про структуру — з урахуванням `company:read` і scope
- [ ] Прибрати дублювання `ChatSession.conversation` / `AIQuery`

## Крок 2 — Відпустки (`vacations`)

- [ ] `VacationRequest`: `employee`, `date_start`, `date_end`, `status` (`pending` / `approved` / `rejected`), `approved_by`, історія
- [ ] Валідація дат і перетинів зі схваленими відпустками
- [ ] Подати заявку за себе (`vacations:write`), схвалити / відхилити (`vacations:manage`, у межах scope)

## Крок 3 — Обладнання (`equipment`)

- [ ] `Equipment`: `serial_number` (унікальний), `name`, `description`
- [ ] `EquipmentAssignment`: `equipment`, `employee`, `date_assigned`, `date_returned`
- [ ] Одна одиниця — не більше одного активного призначення; без призначення = «на складі»

## Крок 4 — Тайм-трекінг (`attendance`)

- [ ] `AttendanceRecord`: `employee`, `date`, `time_start`, `time_end`, `status` (`remote` / `office` / `off`)
- [ ] Відмітка присутності за себе; місячний звіт для HR (з урахуванням scope)

## Крок 5 — Скидання пароля і запрошення

- [ ] Email: AWS SES (через IAM-роль), SMTP / console для dev
- [ ] `password-reset/` → `password-reset/confirm/` на `django.contrib.auth`
- [ ] Лист-запрошення новим користувачам замість пароля від HR

## Крок 6 — CI/CD (GitHub Actions)

- [ ] PR: `ruff check`, `ruff format --check`, `pytest` на PostgreSQL, `spectacular --validate`, Docker build
- [ ] Deploy з `main`; доступ до AWS лише через OIDC + assume-role

## Крок 7 — Продакшн

- [ ] gunicorn, Nginx, HTTPS (Let's Encrypt), `SECURE_SSL_REDIRECT`, HSTS, `collectstatic`
- [ ] S3: приватний бакет + IAM-роль сервера (`GetObject` / `PutObject` / `DeleteObject` на `employees/*`)
- [ ] Redis-кеш дозволів між запитами
- [ ] Довгий випадковий `SECRET_KEY`

## Крок 8 — Документація

- [ ] Переписати `README.md` (зараз — чужий шаблон)
- [ ] Оновити `docs/summary.md`
- [ ] Описати модель доступу для HR / адміністраторів

---

## Технічний борг

- [ ] `StructuralUnit.children_count` оголошено, але не заповнюється
- [ ] Перевірка зарплати в списках для scoped-ролей — запит на кожен рядок
- [ ] Зарплата без валюти
- [ ] `psycopg2-binary` → `psycopg[binary]` (за бажанням)

## Пізніше

React (web), Flutter (mobile), Slack-бот, Google Calendar
