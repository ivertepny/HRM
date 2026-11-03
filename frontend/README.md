# Кадри — веб-клієнт HRM

Next.js 16 (App Router) + TypeScript, Tailwind 4 + shadcn/ui (Base UI), TanStack Query.

## Запуск

```powershell
npm install
copy .env.example .env.local   # BACKEND_URL — адреса Django API
npm run dev                    # http://localhost:3000
```

Бекенд має бути запущений (`.\dev.ps1 run` у корені репозиторію).

## Як влаштована автентифікація (BFF)

Браузер не бачить JWT. Next.js працює як backend-for-frontend:

- `POST /api/auth/login` — логін у Django, токени кладуться в httpOnly-cookie;
- `/api/backend/<шлях Django>` — проксі до API: додає `Authorization`,
  на 401 один раз оновлює токени і повторює запит;
- `POST /api/auth/logout` — відкликає refresh-токен на бекенді, чистить cookie;
- `src/proxy.ts` — без сесії сторінки перенаправляють на `/login`.

Запити, що змінюють дані, приймаються лише з того ж Origin (захист від CSRF).

Файли працівників (`/media/…`) віддає маршрут Next від імені сесії; доступ
перевіряє Django (`MediaView`) за тими ж правами, що й API. `/api/health` —
для моніторингу всього ланцюжка (Next → Django → БД, Redis).

Заголовки безпеки (CSP, `X-Frame-Options`, `Referrer-Policy`,
`Permissions-Policy`) задано в `next.config.ts`. Усе завантажується з власного
домену; нове зовнішнє джерело (шрифт, скрипт, API) треба додати в CSP.

## Типи API

Типи генеруються з OpenAPI-схеми бекенду — після змін в API:

```powershell
npm run api:types
```

## Docker

Сервіс `frontend` у кореневому `docker-compose.yml` збирає продакшн-образ
(`output: "standalone"`) і ходить у Django всередині мережі compose
(`BACKEND_URL=http://api:8000`). Порти задаються змінними `FRONTEND_PORT` (3000)
і `API_PORT` (8000) — зручно, якщо 8000 на машині вже зайнятий.

`COOKIE_SECURE=false` — для стенда по HTTP не на `localhost`; у продакшні
(за HTTPS) змінну не задавати.

## Перевірки

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```

## e2e (Playwright)

Тести ганяються проти ізольованого стенда `docker-compose.e2e.yml`: власна БД у
пам'яті, демо-дані з `seed_demo`, фронтенд на порту 13000 — dev-базу не чіпає.

```powershell
npm run e2e:stack   # збирає й піднімає стенд, чекає готовності
npm run e2e         # локально — у встановленому Chrome
npm run e2e:down
```

Демо-користувачі: `admin@`, `hr@`, `olena@`, `petro@`, `maria@example.com`,
пароль `Demo-pass-2026` (лише для локального стенда).
