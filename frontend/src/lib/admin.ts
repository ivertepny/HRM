import { matches } from "./access";
import type { Schemas } from "./api/client";

export type CatalogPermission = Schemas["Permission"];

export const RESOURCE_LABELS: Record<string, string> = {
  users: "Облікові записи",
  employees: "Працівники",
  salary: "Зарплати",
  documents: "Документи працівників",
  company: "Оргструктура",
  vacations: "Відпустки",
  equipment: "Обладнання",
  attendance: "Присутність",
  roles: "Ролі та доступ",
  ai: "AI-асистент",
};

export const ACTION_ORDER = ["read", "write", "delete", "manage", "use"] as const;

export const ACTION_LABELS: Record<string, string> = {
  read: "Перегляд",
  write: "Зміни",
  delete: "Видалення",
  manage: "Керування",
  use: "Користування",
};

export const FULL_ACCESS = "*:*";

export type ResourceRow = { resource: string; label: string; actions: string[] };

/** Каталог → рядки матриці «ресурс × дія» (wildcard-и окремо). */
export function catalogRows(catalog: CatalogPermission[]): ResourceRow[] {
  const byResource = new Map<string, Set<string>>();
  for (const { resource, action } of catalog) {
    if (resource === "*" || action === "*") continue;
    byResource.set(resource, (byResource.get(resource) ?? new Set()).add(action));
  }
  const order = Object.keys(RESOURCE_LABELS);
  return [...byResource.entries()]
    .sort(([a], [b]) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99))
    .map(([resource, actions]) => ({
      resource,
      label: RESOURCE_LABELS[resource] ?? resource,
      actions: ACTION_ORDER.filter((a) => actions.has(a)),
    }));
}

export type CellState = "off" | "on" | "implied";

/** "implied" — дозвіл дає wildcard (resource:* чи *:*), окремо його не зняти. */
export function cellState(granted: string[], codename: string): CellState {
  if (granted.includes(codename)) return "on";
  return matches(granted, codename) ? "implied" : "off";
}

export function toggle(granted: string[], codename: string): string[] {
  return granted.includes(codename)
    ? granted.filter((c) => c !== codename)
    : [...granted, codename].sort();
}
