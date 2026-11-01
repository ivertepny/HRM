import type { Schemas } from "./api/client";

export type Equipment = Schemas["Equipment"];
export type Assignment = Schemas["EquipmentAssignment"];
export type EquipmentCategory = Schemas["EquipmentCategoryEnum"];
export type EquipmentState = Schemas["EquipmentStateEnum"];

export const CATEGORY_LABELS: Record<EquipmentCategory, string> = {
  laptop: "Ноутбук",
  desktop: "Комп'ютер",
  monitor: "Монітор",
  phone: "Телефон",
  peripheral: "Периферія",
  other: "Інше",
};

export const STATE_LABELS: Record<EquipmentState, string> = {
  in_stock: "На складі",
  assigned: "Видано",
  written_off: "Списано",
};

export type EquipmentAction = "assign" | "return" | "write-off" | "edit" | "delete";

/** Що можна зробити з одиницею (як перевіряє бекенд):
 *  видати й списати — лише зі складу, повернути — лише видане,
 *  видалити — лише без історії видач, списане не редагується. */
export function availableActions(item: Equipment, hasHistory: boolean): EquipmentAction[] {
  switch (item.state) {
    case "in_stock":
      return hasHistory
        ? ["assign", "edit", "write-off"]
        : ["assign", "edit", "write-off", "delete"];
    case "assigned":
      return ["return", "edit"];
    default:
      return [];
  }
}

/** Рядок для журналу: "з 1 березня 2024" або "1 березня — 5 травня 2024". */
export function assignmentPeriod(
  assignment: Pick<Assignment, "date_assigned" | "date_returned">,
  format: (value: string) => string | null,
) {
  const from = format(assignment.date_assigned);
  return assignment.date_returned ? `${from} — ${format(assignment.date_returned)}` : `з ${from}`;
}
