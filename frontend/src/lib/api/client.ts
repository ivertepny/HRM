import createClient, { type Middleware } from "openapi-fetch";

import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

/** Помилка API з тілом відповіді DRF (помилки по полях або {detail}). */
export class ApiError extends Error {
  constructor(
    public status: number,
    public body: unknown,
  ) {
    super(ApiError.describe(status, body));
  }

  /** Помилки по полях для форм: {email: ["..."]} → {email: "..."} */
  get fieldErrors(): Record<string, string> {
    if (!this.body || typeof this.body !== "object") return {};
    return Object.fromEntries(
      Object.entries(this.body as Record<string, unknown>)
        .filter(([key]) => key !== "detail")
        .map(([key, value]) => [key, Array.isArray(value) ? String(value[0]) : String(value)]),
    );
  }

  static describe(status: number, body: unknown) {
    const detail =
      body && typeof body === "object" && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : null;
    if (detail) return detail;
    // Помилки рівня об'єкта (напр. перетин дат) — без прив'язки до поля
    const general =
      body && typeof body === "object" && "non_field_errors" in body
        ? (body as { non_field_errors: unknown[] }).non_field_errors
        : null;
    if (Array.isArray(general) && general.length) return String(general[0]);
    if (status === 403) return "Недостатньо прав для цієї дії.";
    if (status === 409) return "Дію не виконано: дані змінились або використовуються.";
    if (status >= 500) return "Сервер тимчасово недоступний. Спробуйте пізніше.";
    return "Перевірте введені дані.";
  }
}

const sessionGuard: Middleware = {
  onResponse({ response }) {
    // Проксі вже спробував оновити токен — сесія справді завершилась
    if (response.status === 401 && typeof window !== "undefined") {
      const next = window.location.pathname + window.location.search;
      // Повне перезавантаження: у пам'яті не лишається даних попередньої сесії
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign(`/login?next=${encodeURIComponent(next)}`);
    }
    return response;
  },
};

/** Типізований клієнт Django API через BFF-проксі Next.js. */
export const api = createClient<paths>({
  // Абсолютна адреса: Request поза браузером (тести) не приймає відносних URL
  baseUrl:
    typeof window === "undefined" ? "/api/backend" : `${window.location.origin}/api/backend`,
  // Беремо fetch у момент запиту, а не при імпорті модуля
  fetch: (request) => globalThis.fetch(request),
});
api.use(sessionGuard);

export const NETWORK_ERROR = "Немає з'єднання з сервером. Перевірте мережу і спробуйте ще раз.";

/** Повертає data або кидає ApiError — зручно для TanStack Query. */
export async function unwrap<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  let result: { data?: T; error?: unknown; response: Response };
  try {
    result = await request;
  } catch {
    // fetch кидає TypeError без відповіді (мережа, CORS) — текст браузера англійський
    throw new ApiError(0, { detail: NETWORK_ERROR });
  }
  const { data, error, response } = result;
  if (!response.ok) throw new ApiError(response.status, error);
  return data as T;
}
