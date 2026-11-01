import "server-only";

/**
 * Серверна частина BFF: Next.js тримає JWT бекенду в httpOnly-cookie
 * і сам додає Authorization до запитів у Django. Браузер токенів не бачить.
 */

export const BACKEND_URL = (process.env.BACKEND_URL ?? "http://localhost:8000").replace(
  /\/$/,
  "",
);

export const ACCESS_COOKIE = "hrm_access";
export const REFRESH_COOKIE = "hrm_refresh";

// Збігаються з SIMPLE_JWT на бекенді (access 30 хв, refresh 7 днів)
const ACCESS_MAX_AGE = 30 * 60;
const REFRESH_MAX_AGE = 7 * 24 * 60 * 60;

export type TokenPair = { access: string; refresh: string };

type CookieWriter = {
  set(name: string, value: string, options: Record<string, unknown>): unknown;
  delete(name: string): unknown;
};

function cookieOptions(maxAge: number) {
  return {
    httpOnly: true,
    // COOKIE_SECURE=false — для локального стенда по HTTP не на localhost
    secure: process.env.COOKIE_SECURE
      ? process.env.COOKIE_SECURE === "true"
      : process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export function writeTokens(cookies: CookieWriter, tokens: Partial<TokenPair>) {
  if (tokens.access) {
    cookies.set(ACCESS_COOKIE, tokens.access, cookieOptions(ACCESS_MAX_AGE));
  }
  if (tokens.refresh) {
    cookies.set(REFRESH_COOKIE, tokens.refresh, cookieOptions(REFRESH_MAX_AGE));
  }
}

export function clearTokens(cookies: CookieWriter) {
  cookies.delete(ACCESS_COOKIE);
  cookies.delete(REFRESH_COOKIE);
}

/** Новий access (і refresh — бекенд ротує його) або null, якщо refresh недійсний. */
export async function refreshTokens(refresh: string): Promise<TokenPair | null> {
  const response = await fetch(`${BACKEND_URL}/api/users/token/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
    cache: "no-store",
  });
  if (!response.ok) return null;
  const body = (await response.json()) as Partial<TokenPair>;
  return body.access ? { access: body.access, refresh: body.refresh ?? refresh } : null;
}
