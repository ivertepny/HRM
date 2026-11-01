/** Чисті функції BFF-проксі (без Next.js API) — щоб їх можна було тестувати. */

const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/** Заголовки, які не можна пересилати між з'єднаннями (RFC 9110 §7.6.1) або
 *  які проксі виставляє сам. */
const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "upgrade",
  "proxy-authorization",
  "te",
  "trailer",
  "host",
  "cookie",
  "authorization",
  "content-length",
]);

/** /api/backend/api/users/me/?x=1 → {backend}/api/users/me/?x=1 */
export function backendUrl(backend: string, pathname: string, search: string) {
  const rest = pathname.replace(/^\/api\/backend/, "") || "/";
  return `${backend}${rest}${search}`;
}

/**
 * Захист від CSRF для запитів, що змінюють дані: cookie з SameSite=Lax і
 * так не надсилаються з чужих сайтів, а перевірка Origin закриває решту
 * випадків (старі браузери, піддомени).
 */
export function isAllowedOrigin(method: string, origin: string | null, host: string | null) {
  if (!UNSAFE_METHODS.has(method.toUpperCase())) return true;
  if (!origin || !host) return false;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export function forwardHeaders(source: Headers, accessToken?: string) {
  const headers = new Headers();
  source.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  return headers;
}
