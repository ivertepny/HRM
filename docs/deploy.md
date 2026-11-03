# Деплой на VPS (Hetzner)

HRM працює на тому ж VPS, що й cosmetology / strava-ai-coach. Схема та сама:
push у `main` → CI → GitHub Actions по SSH запускає `deploy.sh` на сервері.

```
браузер ──HTTPS──▶ nginx хоста (TLS, Let's Encrypt)
                     │  127.0.0.12:8000
                     ▼
                   hrm-nginx ──▶ hrm-frontend (Next.js, BFF) ──▶ hrm-api (gunicorn + Django)
                                                                   │            │
                                                                 hrm-db      hrm-redis
                                                              (PostgreSQL)  (кеш прав)
```

- Назовні відкритий лише `hrm-nginx` на `127.0.0.12:8000`. Сусіди займають
  `127.0.0.10` (strava) і `127.0.0.11` (cosmetology).
- Браузер говорить тільки з Next.js. Django (API, адмінка, swagger) з
  інтернету недоступний.
- Файли працівників лежать у volume `media`. Django віддає їх з перевіркою
  прав (`/media/…` → Next → `MediaView`).
- Образи збираються на сервері з вихідного коду: `Dockerfile` і
  `frontend/Dockerfile`.

## Що є в репозиторії

| Файл | Призначення |
|------|-------------|
| `docker-compose.server.yml` | продакшн-стек: db, redis, api, frontend, nginx |
| `nginx/nginx.conf` | nginx стеку: усе в Next, ліміти запитів, HSTS |
| `.env.production.example` | шаблон `/www/hrm/.env` з поясненням кожної змінної |
| `deploy.sh` | git reset → бекап → `docker compose up -d --build --wait` |
| `scripts/backup.sh` | дамп БД + архів файлів у `/www/hrm-backups`, ротація 14 днів |
| `scripts/restore.sh` | відновлення з бекапу (руйнівно, з підтвердженням) |
| `scripts/setup_backup_cron.sh` | щоденний бекап о 03:00 |
| `.github/workflows/ci.yml` | перевірки на кожен PR і push |
| `.github/workflows/deploy.yml` | push у `main`: CI, потім деплой |

## Перше налаштування сервера

Команди виконуються від імені користувача деплою (далі `deploy`). Він має
бути в групі `docker`. Майте на увазі, що доступ до Docker фактично
рівноцінний root.

### 1. Каталоги і код

```bash
sudo mkdir -p /www/hrm /www/hrm-backups
sudo chown deploy:deploy /www/hrm /www/hrm-backups
chmod 700 /www/hrm-backups          # у бекапах — персональні дані
git clone https://github.com/ivertepny/HRM.git /www/hrm
```

Якщо репозиторій приватний, серверу потрібен read-only **deploy key**. Його
додають у GitHub → Settings → Deploy keys, а клонують тоді через
`git@github.com:ivertepny/HRM.git`.

### 2. `.env`

```bash
cd /www/hrm
cp .env.production.example .env
chmod 600 .env
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # → SECRET_KEY, POSTGRES_PASSWORD
nano .env
```

AWS-ключів у `.env` бути не повинно: `prod.py` з ними не стартує.

### 3. Перший запуск

```bash
bash deploy.sh
docker compose -f docker-compose.server.yml exec api python manage.py createsuperuser
bash scripts/setup_backup_cron.sh
```

Контейнер `api` при кожному старті сам виконує `migrate` і `seed_roles`.

### 4. nginx хоста і TLS

`/etc/nginx/sites-available/hrm`, потім `ln -s` у `sites-enabled` і
`sudo certbot --nginx -d hrm.example.com`. Certbot додасть блок 443 і
редирект з 80. Всередині `server` для 443 потрібні такі директиви:

```nginx
server {
    server_name hrm.example.com;
    client_max_body_size 11m;               # завантаження файлів до 10 МБ

    location / {
        proxy_pass http://127.0.0.12:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;            # AI-асистент
    }
}
```

`X-Forwarded-Proto https` обов'язковий. Від нього залежать HSTS у
`nginx/nginx.conf` і `SECURE_PROXY_SSL_HEADER` у Django.

### 5. Ключ для GitHub Actions

Ключ окремий для цього проєкту і обмежений однією командою. Навіть якщо він
витече, з ним можна лише запустити деплой.

```bash
ssh-keygen -t ed25519 -N "" -C "github-deploy-hrm" -f hrm_deploy
```

На сервері `hrm_deploy.pub` дописується в `~deploy/.ssh/authorized_keys` одним
рядком:

```
command="bash /www/hrm/deploy.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty ssh-ed25519 AAAA… github-deploy-hrm
```

### 6. Секрети в GitHub

У Settings → Environments створіть environment `production`. За бажанням
увімкніть Required reviewers: тоді кожен деплой треба буде підтвердити
вручну. Потім додайте:

| Тип | Назва | Значення |
|-----|-------|----------|
| secret | `DEPLOY_HOST` | IP або домен сервера |
| secret | `DEPLOY_USER` | `deploy` |
| secret | `DEPLOY_SSH_KEY` | вміст приватного `hrm_deploy` (після цього файл видалити) |
| secret | `DEPLOY_KNOWN_HOSTS` | вивід `ssh-keyscan -t ed25519 <host>` |
| variable (repo) | `DEPLOY_ENABLED` | `true` — вмикає job деплою |
| variable (repo) | `DEPLOY_PORT` | порт SSH, якщо не 22 |

`DEPLOY_KNOWN_HOSTS` спершу звірте з відбитком на самому сервері:
`ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub`. Тоді Actions підключиться
лише до справжнього сервера.

Поки `DEPLOY_ENABLED` не задано, push у `main` проганяє лише CI.

## Щоденна робота

- **Деплой:** push у `main`. Якщо CI впав, деплою не буде. Якщо стек не став
  healthy за 5 хвилин, `deploy.sh` падає і job стає червоним.
- **Логи:** `docker compose -f docker-compose.server.yml logs -f api` (або
  `frontend`, `nginx`).
- **Django-команди:**
  `docker compose -f docker-compose.server.yml exec api python manage.py <команда>`.
  Адмінка Django в інтернет не виходить. Усе адміністрування робиться в
  розділі «Адміністрування» застосунку.
- **Моніторинг:** `GET https://hrm.example.com/api/health` перевіряє весь
  ланцюжок: nginx → Next → Django → БД і Redis. Відповідь `{"status":"ok"}`
  або 503.

## Відкат

Зробіть `git revert` поганого коміту і push у `main`: деплой збере попередній
код. `deploy.sh` завжди бере `origin/main`, тож ручний `git reset` на сервері
перезапишеться наступним деплоєм.

Міграції назад не відкочуються. Тому їх треба робити сумісними: колонку
додають в одному деплої, а стару видаляють у наступному. Міграцію, яку так не
відкотити, лікують відновленням з бекапу.

## Бекапи

- **Коли знімаються:** `deploy.sh` перед кожним деплоєм і cron щодня о 03:00.
- **Що в них:** `db_<дата>.sql.gz` (`pg_dump`) і `media_<дата>.tar.gz` (файли
  працівників). Файли лежать у `/www/hrm-backups`, доступ лише власнику,
  зберігаються 14 днів (`BACKUP_KEEP_DAYS`).
- **Відновлення:**
  `bash scripts/restore.sh /www/hrm-backups/db_….sql.gz [/www/hrm-backups/media_….tar.gz]`.
  Скрипт зупиняє застосунок, замінює базу (і файли) та піднімає стек знову.
- **Обмеження:** бекапи лежать на тому самому сервері, тож від втрати VPS
  вони не врятують. Наступний крок — копія поза сервером (Hetzner Storage
  Box через `rsync`/`borg`), див. `docs/plan.md`.
