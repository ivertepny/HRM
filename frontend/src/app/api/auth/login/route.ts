import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import { BACKEND_URL, writeTokens, type TokenPair } from "@/lib/server/backend";
import { isAllowedOrigin } from "@/lib/server/proxy-utils";

/** Логін через Django; токени лишаються в httpOnly-cookie, браузеру — лише user. */
export async function POST(request: NextRequest) {
  if (!isAllowedOrigin("POST", request.headers.get("origin"), request.headers.get("host"))) {
    return NextResponse.json({ detail: "Недозволене джерело запиту." }, { status: 403 });
  }

  const response = await fetch(`${BACKEND_URL}/api/users/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: await request.text(),
    cache: "no-store",
  });
  const body = await response.json();

  if (!response.ok) {
    return NextResponse.json(body, { status: response.status });
  }

  writeTokens(await cookies(), body.token as TokenPair);
  return NextResponse.json({ user: body.user });
}
