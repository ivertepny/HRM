import { NextResponse, type NextRequest } from "next/server";

// Не імпортуємо lib/server/backend: Proxy виконується окремо від коду рендеру
const REFRESH_COOKIE = "hrm_refresh";
// Посилання з листів (скидання, запрошення) відкриваються і з чужою сесією
// на цьому пристрої: людина могла не вийти, а пароль ставить собі
const PUBLIC_PATHS = new Set(["/login", "/forgot-password", "/reset-password", "/invite"]);

/**
 * Сторінки: без сесії — на /login (з поверненням назад), з сесією — геть з /login.
 * Справжню перевірку токена робить бекенд; тут лише швидкий редирект.
 */
export function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  // skipTrailingSlashRedirect вимкнув це глобально — повертаємо для сторінок
  if (pathname.length > 1 && pathname.endsWith("/")) {
    const url = request.nextUrl.clone();
    url.pathname = pathname.replace(/\/+$/, "");
    return NextResponse.redirect(url, 308);
  }

  const hasSession = request.cookies.has(REFRESH_COOKIE);
  const isPublic = PUBLIC_PATHS.has(pathname);

  if (!hasSession && !isPublic) {
    const url = new URL("/login", request.url);
    if (pathname !== "/") url.searchParams.set("next", `${pathname}${search}`);
    return NextResponse.redirect(url);
  }
  if (hasSession && pathname === "/login") {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|.*\\.[a-z0-9]+$).*)"],
};
