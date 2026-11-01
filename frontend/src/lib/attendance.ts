import type { Schemas } from "./api/client";
import { parseDate, toISODate } from "./vacations";

export type AttendanceRecord = Schemas["AttendanceRecord"];
export type AttendanceStatus = Schemas["AttendanceStatusEnum"];
export type ReportRow = Schemas["ReportRow"];

export const STATUS_LABELS: Record<AttendanceStatus, string> = {
  office: "В офісі",
  remote: "Віддалено",
  off: "Не працюю",
};

/** "09:00:00" → "09:00"; порожньо — null. */
export function shortTime(value?: string | null) {
  return value ? value.slice(0, 5) : null;
}

/** Поточний час "HH:MM" — для кнопок «Почати» / «Завершити». */
export function nowTime(now = new Date()) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(now.getHours())}:${pad(now.getMinutes())}`;
}

/** "2026-11-01" → "2026-11". */
export function monthOf(iso: string) {
  return iso.slice(0, 7);
}

/** shiftMonth("2026-01", -1) → "2025-12". */
export function shiftMonth(month: string, delta: number) {
  const [year, m] = month.split("-").map(Number);
  const date = new Date(year, m - 1 + delta, 1);
  return toISODate(date).slice(0, 7);
}

/** Перший і останній день місяця — для фільтрів date_from / date_to. */
export function monthRange(month: string) {
  const [year, m] = month.split("-").map(Number);
  return { from: `${month}-01`, to: toISODate(new Date(year, m, 0)) };
}

const monthFormat = new Intl.DateTimeFormat("uk-UA", { month: "long", year: "numeric" });

/** "2026-11" → "листопад 2026 р." */
export function monthLabel(month: string) {
  return monthFormat.format(parseDate(`${month}-01`));
}

const dayFormat = new Intl.DateTimeFormat("uk-UA", {
  weekday: "short",
  day: "numeric",
  month: "short",
});

/** "2026-11-02" → "пн, 2 лист." */
export function dayLabel(iso: string) {
  return dayFormat.format(parseDate(iso));
}

/** Години з комою: 8.5 → "8,5 год". */
export function formatHours(hours?: number | null) {
  if (hours == null) return null;
  return `${new Intl.NumberFormat("uk-UA", { maximumFractionDigits: 2 }).format(hours)} год`;
}
