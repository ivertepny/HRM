import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import {
  ACCESS_COOKIE,
  BACKEND_URL,
  clearTokens,
  REFRESH_COOKIE,
} from "@/lib/server/backend";
import { isAllowedOrigin } from "@/lib/server/proxy-utils";

/** Відкликає refresh-токен на бекенді (blacklist) і прибирає cookie. */
export async function POST(request: NextRequest) {
  if (!isAllowedOrigin("POST", request.headers.get("origin"), request.headers.get("host"))) {
    return NextResponse.json({ detail: "Недозволене джерело запиту." }, { status: 403 });
  }

  const store = await cookies();
  const access = store.get(ACCESS_COOKIE)?.value;
  const refresh = store.get(REFRESH_COOKIE)?.value;

  if (refresh) {
    // Навіть якщо бекенд недоступний чи токен уже прострочений — виходимо локально
    await fetch(`${BACKEND_URL}/api/users/logout/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(access ? { Authorization: `Bearer ${access}` } : {}),
      },
      body: JSON.stringify({ refresh }),
      cache: "no-store",
    }).catch(() => undefined);
  }

  clearTokens(store);
  return new NextResponse(null, { status: 204 });
}
