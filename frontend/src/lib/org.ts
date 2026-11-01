import type { Unit } from "./employees";

export type UnitNode = Unit & { children: UnitNode[] };

/**
 * Плаский список у порядку обходу дерева → вузли з дітьми. Підрозділ, чий
 * батько поза областю доступу, стає коренем (scoped-ролі бачать піддерево).
 */
export function buildTree(units: Unit[]): UnitNode[] {
  const nodes = new Map<number, UnitNode>();
  const roots: UnitNode[] = [];
  for (const unit of units) nodes.set(unit.id!, { ...unit, children: [] });
  for (const node of nodes.values()) {
    const parent = node.parent != null ? nodes.get(node.parent) : undefined;
    (parent ? parent.children : roots).push(node);
  }
  return roots;
}

/** id підрозділу та всіх його нащадків — їх не можна обрати новим батьком. */
export function subtreeIds(node: UnitNode): Set<number> {
  const ids = new Set<number>([node.id!]);
  const stack = [...node.children];
  while (stack.length) {
    const current = stack.pop()!;
    ids.add(current.id!);
    stack.push(...current.children);
  }
  return ids;
}

export function findNode(roots: UnitNode[], id: number): UnitNode | undefined {
  const stack = [...roots];
  while (stack.length) {
    const node = stack.pop()!;
    if (node.id === id) return node;
    stack.push(...node.children);
  }
  return undefined;
}

/** Працівники в піддереві (employees_count — лише безпосередньо в підрозділі). */
export function subtreeEmployees(node: UnitNode): number {
  return node.children.reduce((sum, child) => sum + subtreeEmployees(child), node.employees_count ?? 0);
}

export const HISTORY_LABELS: Record<string, string> = {
  created: "Створено",
  updated: "Змінено",
  deleted: "Закрито",
};

export const FIELD_LABELS: Record<string, string> = {
  name: "назва",
  custom_type: "тип",
  parent: "батьківський підрозділ",
  is_active: "активний",
};
