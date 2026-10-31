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

## Типи API

Типи генеруються з OpenAPI-схеми бекенду — після змін в API:

```powershell
npm run api:types
```

## Перевірки

```powershell
npm run typecheck
npm run lint
npm test
npm run build
```
