import { NextResponse } from "next/server";

import { BACKEND_URL } from "@/lib/server/backend";

/**
 * Для зовнішнього моніторингу: перевіряє весь ланцюжок nginx → Next → Django
 * (→ БД і Redis). Відповідає лише ok / error, без подробиць.
 */
export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/health/`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (response.ok) return NextResponse.json({ status: "ok" });
  } catch {
    // недоступний бекенд — те саме, що помилка
  }
  return NextResponse.json({ status: "error" }, { status: 503 });
}
