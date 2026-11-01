import type { Schemas } from "./api/client";

export type Vacation = Schemas["VacationRequest"];
export type VacationStatus = NonNullable<Vacation["status"]>;
export type VacationType = NonNullable<Vacation["vacation_type"]>;

export const TYPE_LABELS: Record<VacationType, string> = {
  annual: "Щорічна відпустка",
  sick: "Лікарняний",
  unpaid: "За власний рахунок",
  other: "Інше",
};

export const STATUS_LABELS: Record<VacationStatus, string> = {
  pending: "На розгляді",
  approved: "Схвалено",
  rejected: "Відхилено",
  cancelled: "Скасовано",
};

/** Типи, які не можна почати в минулому (як на бекенді). */
export const PLANNED_TYPES: VacationType[] = ["annual", "unpaid"];

// --- календарні дати без часових зон -------------------------------------------

/** "2026-11-10" → Date опівночі за місцевим часом. */
export function parseDate(value: string) {
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return new Date(year, month - 1, day);
}

export function toISODate(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function todayISO() {
  return toISODate(new Date());
}

/** Календарні дні включно з обома межами; 0, якщо кінець раніше початку. */
export function daysInclusive(start: string, end: string) {
  const diff = Math.round((parseDate(end).getTime() - parseDate(start).getTime()) / 86_400_000);
  return diff < 0 ? 0 : diff + 1;
}

const dayMonthYear = new Intl.DateTimeFormat("uk-UA", {
  day: "numeric",
  month: "long",
  year: "numeric",
});
const dayMonth = new Intl.DateTimeFormat("uk-UA", { day: "numeric", month: "long" });

/** «10–14 листопада 2026», «28 жовтня – 3 листопада 2026», «30 грудня 2026 – 2 січня 2027». */
export function formatRange(start: string, end: string) {
  const from = parseDate(start);
  const to = parseDate(end);
  if (start === end) return dayMonthYear.format(from).replace(" р.", "");
  const year = to.getFullYear();
  if (from.getFullYear() !== year) {
    return `${dayMonthYear.format(from).replace(" р.", "")} – ${dayMonthYear.format(to).replace(" р.", "")}`;
  }
  if (from.getMonth() === to.getMonth()) {
    return `${from.getDate()}–${dayMonth.format(to)} ${year}`;
  }
  return `${dayMonth.format(from)} – ${dayMonth.format(to)} ${year}`;
}

export function dayWord(count: number) {
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return "дні";
  return "днів";
}

/** «1 календарний день», «3 календарні дні», «5 календарних днів». */
export function calendarDays(count: number) {
  const word = dayWord(count);
  const adjective = { день: "календарний", дні: "календарні", днів: "календарних" }[word];
  return `${count} ${adjective} ${word}`;
}

/** Як Model.cancel() на бекенді: на розгляді або схвалена, що ще не почалась. */
export function isCancellable(vacation: Vacation, today = todayISO()) {
  return (
    vacation.status === "pending" ||
    (vacation.status === "approved" && vacation.date_start > today)
  );
}

/** Використані дні щорічної відпустки в календарному році (схвалені заявки). */
export function annualDaysUsed(vacations: Vacation[], year: number) {
  return vacations
    .filter((v) => v.status === "approved" && v.vacation_type === "annual")
    .reduce((total, v) => {
      const start = v.date_start > `${year}-01-01` ? v.date_start : `${year}-01-01`;
      const end = v.date_end < `${year}-12-31` ? v.date_end : `${year}-12-31`;
      return total + daysInclusive(start, end);
    }, 0);
}

// --- календар місяця -----------------------------------------------------------

export type MonthDay = { iso: string; day: number; weekend: boolean; today: boolean };

export function monthDays(year: number, month: number, today = todayISO()): MonthDay[] {
  const count = new Date(year, month + 1, 0).getDate();
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(year, month, i + 1);
    const iso = toISODate(date);
    return { iso, day: i + 1, weekend: date.getDay() === 0 || date.getDay() === 6, today: iso === today };
  });
}

export type CalendarSegment = {
  vacation: Vacation;
  /** Колонка першого дня в межах місяця (1-based, для grid-column). */
  column: number;
  span: number;
  continuesBefore: boolean;
  continuesAfter: boolean;
};

export type CalendarRow = { employeeId: number; name: string; segments: CalendarSegment[] };

/**
 * Рядок на працівника, смуги відпусток у межах місяця. Скасовані й відхилені
 * не показуються — календар про те, хто буде відсутній.
 */
export function calendarRows(vacations: Vacation[], year: number, month: number): CalendarRow[] {
  const first = toISODate(new Date(year, month, 1));
  const last = toISODate(new Date(year, month + 1, 0));
  const rows = new Map<number, CalendarRow>();

  for (const vacation of vacations) {
    if (vacation.status !== "approved" && vacation.status !== "pending") continue;
    if (vacation.date_end < first || vacation.date_start > last || !vacation.employee) continue;

    const start = vacation.date_start < first ? first : vacation.date_start;
    const end = vacation.date_end > last ? last : vacation.date_end;
    const row = rows.get(vacation.employee.id) ?? {
      employeeId: vacation.employee.id,
      name: vacation.employee.name,
      segments: [],
    };
    row.segments.push({
      vacation,
      column: parseDate(start).getDate(),
      span: daysInclusive(start, end),
      continuesBefore: vacation.date_start < first,
      continuesAfter: vacation.date_end > last,
    });
    rows.set(vacation.employee.id, row);
  }

  return [...rows.values()].sort((a, b) => a.name.localeCompare(b.name, "uk"));
}
