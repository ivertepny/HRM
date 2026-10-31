import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  BACKEND_URL,
  clearTokens,
  REFRESH_COOKIE,
  refreshTokens,
  writeTokens,
} from "@/lib/server/backend";
import { backendUrl, forwardHeaders, isAllowedOrigin } from "@/lib/server/proxy-utils";

/**
 * BFF-проксі: /api/backend/<шлях Django> → BACKEND_URL/<шлях>.
 * Додає Authorization з httpOnly-cookie; на 401 один раз оновлює токени
 * і повторює запит.
 */
async function handle(request: NextRequest) {
  const { method, nextUrl, headers } = request;
  if (!isAllowedOrigin(method, headers.get("origin"), headers.get("host"))) {
    return NextResponse.json({ detail: "Недозволене джерело запиту." }, { status: 403 });
  }

  const store = await cookies();
  const target = backendUrl(BACKEND_URL, nextUrl.pathname, nextUrl.search);
  // Тіло читаємо один раз: при повторі після refresh його треба надіслати знову
  const body = method === "GET" || method === "HEAD" ? undefined : await request.arrayBuffer();

  const send = (access?: string) =>
    fetch(target, {
      method,
      headers: forwardHeaders(headers, access),
      body,
      cache: "no-store",
      redirect: "manual",
    });

  let response = await send(store.get(ACCESS_COOKIE)?.value);

  if (response.status === 401) {
    const refresh = store.get(REFRESH_COOKIE)?.value;
    const tokens = refresh ? await refreshTokens(refresh) : null;
    if (!tokens) {
      clearTokens(store);
      return NextResponse.json({ detail: "Сесія завершилась. Увійдіть знову." }, { status: 401 });
    }
    writeTokens(store, tokens);
    response = await send(tokens.access);
  }

  // fetch уже розпакував тіло — заголовки стиснення й довжини не пересилаємо
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("content-encoding");
  responseHeaders.delete("content-length");
  responseHeaders.delete("set-cookie");

  return new NextResponse(response.status === 204 ? null : response.body, {
    status: response.status,
    headers: responseHeaders,
  });
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
