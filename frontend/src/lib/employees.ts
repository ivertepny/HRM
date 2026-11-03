import type { Schemas } from "./api/client";

export type Employee = Schemas["Employee"];
export type Unit = Schemas["StructuralUnit"];

export const EVENT_LABELS: Record<NonNullable<Schemas["CareerHistory"]["event"]>, string> = {
  hired: "Прийом на роботу",
  changed: "Кадрова зміна",
  fired: "Звільнення",
};

export const DOCUMENT_LABELS: Record<NonNullable<Schemas["EmployeeDocument"]["document_type"]>, string> = {
  cv: "CV",
  nda: "NDA",
  contract: "Договір",
  other: "Інше",
};

export const CURRENCIES = ["UAH", "USD", "EUR"] as const;

/** Розширення й ліміт — як на бекенді (EmployeeDocument.ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_MB). */
export const DOCUMENT_ACCEPT = ".pdf,.doc,.docx,.odt,.jpg,.jpeg,.png";
export const MAX_UPLOAD_MB = 10;

/** «Головний офіс > IT > Backend» — як full_name на бекенді. */
export function unitPath(unit: Pick<Unit, "name" | "ancestors">) {
  return [...(unit.ancestors ?? []).map((a) => a.name), unit.name].join(" > ");
}

/**
 * Посилання на файл: локальні /media/ бекенду — через маршрут Next (з перевіркою
 * сесії і прав на бекенді); інші абсолютні URL — як є.
 */
export function fileHref(url?: string | null) {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.pathname.startsWith("/media/") ? parsed.pathname + parsed.search : url;
  } catch {
    return url;
  }
}

/** Звільнений на сьогодні (дата звільнення вже настала). */
export function isFired(employee: Pick<Employee, "date_fired">, today: string) {
  return !!employee.date_fired && employee.date_fired <= today;
}

/** Лише змінені поля — щоб у кадровий журнал не потрапляли «зміни» без змін. */
export function changedFields<T extends Record<string, unknown>>(initial: T, next: T) {
  return Object.fromEntries(
    Object.entries(next).filter(([key, value]) => value !== initial[key]),
  ) as Partial<T>;
}
