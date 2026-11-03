import { execFileSync } from "node:child_process";
import path from "node:path";

const COMPOSE_FILE = path.resolve(__dirname, "../../docker-compose.e2e.yml");

/**
 * Останнє посилання з листа на `to`. e2e-стенд пише листи у файли контейнера
 * api (EMAIL_BACKEND=filebased, EMAIL_FILE_PATH=/tmp/emails).
 */
export function lastLink(to: string, pathname: "/invite" | "/reset-password"): string {
  const dump = execFileSync(
    "docker",
    ["compose", "-f", COMPOSE_FILE, "exec", "-T", "api", "sh", "-c", "cat /tmp/emails/* 2>/dev/null"],
    { encoding: "utf8" },
  );
  // Листи розділені рядком з дефісів; беремо останній адресований `to`
  const message = dump
    .split(/^-{79}$/m)
    .filter((m) => m.split("\n").some((line) => line.trim() === `To: ${to}`))
    .at(-1);
  if (!message) throw new Error(`Немає листа для ${to}`);
  const match = message.match(new RegExp(String.raw`https?://\S+${pathname}\?\S+`));
  if (!match) throw new Error(`У листі для ${to} немає посилання ${pathname}`);
  const url = new URL(match[0]);
  // Відносна адреса: стенд може слухати інший порт, ніж FRONTEND_URL
  return `${url.pathname}${url.search}`;
}
