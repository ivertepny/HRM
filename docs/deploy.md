# Деплой на VPS (Hetzner)

HRM працює на тому ж VPS, що й cosmetology / strava-ai-coach. Схема та сама:
push у `main` → CI → GitHub Actions по SSH запускає `deploy.sh` на сервері.

```
браузер ──HTTPS──▶ Cloudflare ──HTTPS (Origin CA)──▶ nginx хоста
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
| `scripts/offsite_backup.sh` | копія бекапів поза сервером (restic → Hetzner Storage Box) |
| `scripts/setup_backup_cron.sh` | щоденний бекап о 03:00 |
| `scripts/setup_reminders_cron.sh` | Slack-нагадування в робочі дні |
| `.github/workflows/ci.yml` | перевірки на кожен PR і push |
| `.github/workflows/deploy.yml` | push у `main`: CI, потім деплой по SSH (`START`: `0` / `1`) |

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

**Пошта** потрібна для запрошень і скидання пароля. Без `EMAIL_HOST`,
`DEFAULT_FROM_EMAIL` і `FRONTEND_URL` контейнер `api` не стартує.

- **Провайдер:** підійде будь-який SMTP — Brevo, Mailgun, Postmark, Resend,
  Zoho. Hetzner блокує вихідні порти 25 і 465 на нових серверах, тому
  використовуйте порт 587 з TLS (`EMAIL_PORT=587`, `EMAIL_USE_TLS=true`).
- **DNS домену відправника:** додайте записи SPF і DKIM з кабінету провайдера,
  а бажано й DMARC. Без них листи потраплятимуть у «Спам».
- **Перевірка:**
  `docker compose -f docker-compose.server.yml exec api python manage.py sendtestemail you@example.com`.

### 3. Перший запуск

```bash
bash deploy.sh
docker compose -f docker-compose.server.yml exec api python manage.py createsuperuser
bash scripts/setup_backup_cron.sh
```

Контейнер `api` при кожному старті сам виконує `migrate` і `seed_roles`.

### 4. Cloudflare і nginx хоста

Домен працює через Cloudflare (проксі, оранжева хмарка). TLS для браузера
завершує Cloudflare, тож certbot не потрібен. Від Cloudflare до сервера —
окреме HTTPS-з'єднання з сертифікатом **Cloudflare Origin CA**.

**У Cloudflare (dashboard домену):**

- **SSL/TLS → Overview: Full (strict).** Режим Flexible не підходить: у ньому
  трафік від Cloudflare до сервера, разом із паролями й зарплатами, іде
  відкритим текстом.
- **SSL/TLS → Origin Server → Create Certificate** (RSA, 15 років). Сертифікат
  і ключ збережіть на сервері, наприклад у `/etc/ssl/cloudflare/hrm.pem` і
  `hrm.key` (`chmod 600` на ключ).
- **SSL/TLS → Edge Certificates:**
  - *Always Use HTTPS* — увімкнути;
  - *Minimum TLS* — 1.2;
  - *HSTS* — **не вмикати**: заголовок уже ставить `nginx/nginx.conf`, і другий
    дублював би його з іншим `max-age`.
- **Speed → Optimization:** вимкнути *Rocket Loader*. Він підміняє скрипти
  сторінки, а CSP застосунку (`script-src 'self'`) їх заблокує, і сторінки не
  працюватимуть. З тієї ж причини не вмикайте автовставку *Web Analytics*
  (beacon): CSP його відкине, у консолі будуть помилки.
- **Кеш** лишіть за замовчуванням. Правило *Cache Everything* не підходить:
  сторінки й API залежать від користувача. Хешовані `/_next/static/`
  Cloudflare кешує сам.

**Справжній IP клієнта.** Без цього кроку всі запити приходять на сервер з
адрес Cloudflare. Тоді ліміти за IP у `nginx/nginx.conf` (вхід — 10 запитів
за хвилину) стають спільними для всіх користувачів, і вхід зупиниться вже
зранку.

Налаштування `real_ip` діє на весь nginx хоста, тобто на всі сайти сервера,
тож узгодьте його з адміністратором. Діапазони Cloudflare беруться з їхнього
сайту:

```bash
{
  for ip in $(curl -fsS https://www.cloudflare.com/ips-v4) $(curl -fsS https://www.cloudflare.com/ips-v6); do
    echo "set_real_ip_from $ip;"
  done
  echo "real_ip_header CF-Connecting-IP;"
} | sudo tee /etc/nginx/conf.d/cloudflare-realip.conf
```

Діапазони змінюються рідко. Ту саму команду можна раз на кілька місяців
запускати з cron, після неї потрібен `nginx -s reload`. Бажано ще приймати
443-й порт лише з адрес Cloudflare (ufw чи файрвол Hetzner Cloud): так сервер
не обійдуть напряму за IP.

**`/etc/nginx/sites-available/hrm`**, потім `ln -s` у `sites-enabled` і
`sudo nginx -t && sudo nginx -s reload`:

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name hrm.example.com;

    ssl_certificate     /etc/ssl/cloudflare/hrm.pem;
    ssl_certificate_key /etc/ssl/cloudflare/hrm.key;

    client_max_body_size 11m;               # завантаження файлів до 10 МБ

    location / {
        proxy_pass http://127.0.0.12:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        # Після real_ip $remote_addr — справжній клієнт, а не Cloudflare
        proxy_set_header X-Forwarded-For $remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 120s;            # AI-асистент
    }
}
```

Блок для порту 80 не потрібен: на HTTPS переводить Cloudflare (*Always Use
HTTPS*).

`X-Forwarded-Proto https` обов'язковий. Від нього залежать HSTS у
`nginx/nginx.conf` і `SECURE_PROXY_SSL_HEADER` у Django.

**Ліміт 100 секунд.** На безкоштовному й Pro-тарифах Cloudflare обриває
запит, якщо відповіді немає довше 100 с: користувач бачить помилку 524.
Звичайні запити вкладаються з великим запасом. Ризик є лише в довгої відповіді
AI-асистента з кількома викликами моделі. Якщо 524 трапляються, зменште
`AI_RECURSION_LIMIT` або `OPENAI_TIMEOUT_AI` у `config/settings/base.py`.

### 5. Користувач деплою і диспетчер

Схема спільна для всіх проєктів на сервері, як у cosmetology. Її налаштовує
адміністратор сервера.

- GitHub Actions заходить по SSH під користувачем деплою і передає лише назву
  репозиторію (`HRM`).
- Логін-шелом цього користувача є **диспетчер**. Він приймає назву
  репозиторію і запускає відповідний скрипт: для `HRM` це
  `bash /www/hrm/deploy.sh`.
- Інших команд через цей вхід виконати не можна. Тож навіть ключ, що витік,
  дає лише змогу запустити деплой.

Що потрібно від адміністратора:

1. Додати в диспетчер відповідність `HRM` → `/www/hrm/deploy.sh`.
2. Згенерувати окремий ключ для цього проєкту:
   `ssh-keygen -t ed25519 -N "" -C "github-deploy-hrm" -f hrm_deploy`.
   Публічну частину (`hrm_deploy.pub`) він дописує в
   `~<користувач деплою>/.ssh/authorized_keys`.

### 6. Секрети в GitHub

Settings → Secrets and variables → Actions → **Repository secrets**:

| Назва | Значення |
|-------|----------|
| `DEPLOYHOST` | IP або домен сервера |
| `DEPLOYLOGIN` | користувач деплою |
| `DEPLOYKEY` | вміст приватного `hrm_deploy` (після цього файл видалити) |

### 7. Увімкнути деплой

Поки сервер не готовий, у `.github/workflows/deploy.yml` стоїть `START: "0"`:
push у `main` проганяє CI, а крок деплою пропускається.

Коли сервер готовий, поставте `START: "1"` і зробіть push. Після запуску
продакшну `env.START` і `if:` кроку можна прибрати.

Workflow — спільний шаблон сервера, погоджений з адміністратором. У ньому
змінюється лише версія закріпленої дії `appleboy/ssh-action`, і її пропонує
Dependabot.

### 8. Slack (необов'язково)

Бот пише людям в особисті повідомлення:
- нова заявка на відпустку — тим, хто може її розглянути (HR і керівники
  підрозділу та його предків);
- рішення чи скасування — працівнику;
- запрошення — новому користувачу (дублює лист);
- щоденні нагадування (cron).

Людей бот знаходить за робочим email, тож пошта в HRM має збігатися з поштою в
Slack. До нашого сервера Slack не звертається: запити лише вихідні, а Django
лишається закритим. Коментарі до заявок у Slack не потрапляють, лише хто, що,
коли і посилання.

1. **Створити застосунок:** api.slack.com/apps → *Create New App* → *From
   scratch*, у потрібному workspace.
2. **Права бота:** *OAuth & Permissions* → *Bot Token Scopes*: `chat:write`,
   `users:read`, `users:read.email`.
3. **Особисті повідомлення:** *App Home* → *Messages Tab* увімкнути, а також
   «Allow users to send Slash commands and messages from the messages tab».
   Без цього повідомлення бота не відображатимуться в особистих.
4. **Токен:** *Install to Workspace* → скопіювати **Bot User OAuth Token**
   (`xoxb-…`) у `.env` як `SLACK_BOT_TOKEN` і перезапустити стек (`bash deploy.sh`).
5. **Нагадування:** `bash scripts/setup_reminders_cron.sh`. Розклад:
   - о 09:30 пн–пт — скільки заявок чекає розгляду;
   - об 11:00 пн–пт — хто ще не відмітився в табелі (у свята й відпустку — ні).

   Час — серверний, перевірте `timedatectl`. Лог —
   `/www/hrm-backups/reminders.log`.

Перевірка вручну:
`docker compose -f docker-compose.server.yml exec api python manage.py slack_reminders --vacations`.

Сповіщення — best-effort. Якщо Slack недоступний, людини немає у workspace або
процес перезапустився під час надсилання, повідомлення просто не прийде.
Кадрові дії від цього не ламаються, а помилки пишуться в лог і Sentry.
Нагадування того самого виду приходить людині не частіше разу на день.

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
  або 503. Додайте його в будь-який uptime-монітор, наприклад UptimeRobot
  або Hetzner.
- **Помилки:** з `SENTRY_DSN` у `.env` помилки 500 йдуть у Sentry з git SHA
  деплою. Персональних даних там немає: ні тіл запитів, ні локальних змінних,
  ні email чи IP (`apps/core/sentry.py`). Лише тип помилки, стек, URL і метод.
- **Ліміти:**
  - nginx стеку: 10 запитів/с з одного IP, вхід — 10/хв з IP;
  - nginx: скидання пароля і пароль за посиланням — так само, як вхід;
  - Django: 10 спроб входу на годину на один email, 5 листів зі скиданням на
    годину на одну адресу, 600 запитів/хв на користувача, AI-асистент — 10/хв
    і 200/день на користувача;
  - змінюються через `LOGIN_RATE`, `PASSWORD_RESET_RATE`, `AI_CHAT_RATE`,
    `AI_CHAT_DAILY_RATE` у `.env`.
- **HSTS:** коли HTTPS кілька днів працює без проблем, підніміть `max-age` до
  `31536000` у `nginx/nginx.conf` (через коміт) і `SECURE_HSTS_SECONDS` у
  `.env`.

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
- **Обмеження локальних бекапів:** вони лежать на тому самому сервері, тож
  від втрати VPS не врятують. Для цього потрібна копія поза сервером, див.
  нижче.

### Копія поза сервером (Hetzner Storage Box)

Після кожного щоденного бекапу `scripts/offsite_backup.sh` надсилає
`/www/hrm-backups` у Storage Box через restic. Restic працює в Docker, тож на
хості нічого ставити не треба.

- **Шифрування:** restic шифрує дані до відправки, Hetzner бачить лише
  шифротекст.
- **Дедуплікація:** однакові дані зберігаються один раз, тож щоденний архів
  файлів не множить обсяг.
- **Ротація:** 14 щоденних, 8 тижневих, 12 місячних копій.
- **Перевірка:** щодня `restic check`; у неділю ще читається 10 % даних.
- **Захист від видалення:** стерті на сервері файли з копії не зникають, бо
  це не `rsync --delete`. Але ключ сервера дає повний доступ до репозиторію:
  хто захопить сервер, зможе видалити й копію. Від цього захищають лише
  snapshots Storage Box (крок 1).

Перед деплоєм бекап лишається лише локальним: якщо Storage Box недоступний,
деплой від цього не зламається.

1. **Hetzner Console:** замовте Storage Box (BX11 вистачає з запасом). У його
   налаштуваннях увімкніть **SSH support** і **автоматичні snapshots**.
   Snapshots робить сам Hetzner, і сервер їх видалити не може. Тому вони
   рятують навіть тоді, коли зловмисник із ключем видалив репозиторій.
2. **Ключ і `known_hosts`** (на сервері, `u123456` — ваш логін Storage Box):

   ```bash
   sudo mkdir -p /www/hrm-restic && sudo chown deploy:deploy /www/hrm-restic
   chmod 700 /www/hrm-restic && cd /www/hrm-restic
   ssh-keygen -t ed25519 -N "" -C hrm-restic -f id_ed25519
   cat id_ed25519.pub | ssh -p 23 u123456@u123456.your-storagebox.de install-ssh-key
   ssh-keyscan -p 23 -t ed25519 u123456.your-storagebox.de > known_hosts
   ```

3. **`/www/hrm-restic/restic.env`**, `chmod 600`:

   ```bash
   RESTIC_REPOSITORY=sftp:u123456@u123456.your-storagebox.de:hrm
   RESTIC_PASSWORD=          # python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   SFTP_COMMAND="ssh -p 23 -i /restic/id_ed25519 -o UserKnownHostsFile=/restic/known_hosts -o BatchMode=yes u123456@u123456.your-storagebox.de -s sftp"
   ```

   **`RESTIC_PASSWORD` збережіть ще й у менеджері паролів.** Без нього
   відновити копію неможливо. Якщо загине сервер, загине й `restic.env`.
4. **Один раз:** `bash scripts/offsite_backup.sh init`, потім
   `bash scripts/backup.sh` і перевірка
   `bash scripts/offsite_backup.sh snapshots`.
5. **Сповіщення, якщо бекап не відбувся:** створіть check на healthchecks.io
   (період 1 день, grace 2 години). Потім перевстановіть cron з його URL:
   `BACKUP_PING_URL=https://hc-ping.com/<uuid> bash scripts/setup_backup_cron.sh`.
   Пінг іде лише після повністю успішного бекапу, тож про зламаний бекап
   сповістить сам сервіс.

**Відновлення з копії** (наприклад, на новому сервері, після кроків 1–3
вище і копіювання `/www/hrm-restic`):

```bash
RESTORE_DIR=/tmp/hrm-restore bash scripts/offsite_backup.sh snapshots
RESTORE_DIR=/tmp/hrm-restore bash scripts/offsite_backup.sh restore latest --target /restore
bash scripts/restore.sh /tmp/hrm-restore/backups/db_….sql.gz /tmp/hrm-restore/backups/media_….tar.gz
```
