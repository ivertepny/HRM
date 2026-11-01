import { describe, expect, it } from "vitest";

import type { Unit } from "./employees";
import { buildTree, findNode, subtreeEmployees, subtreeIds } from "./org";

const unit = (id: number, parent: number | null, employees = 0): Unit => ({
  id,
  parent,
  name: `U${id}`,
  employees_count: employees,
});

describe("org tree", () => {
  const flat = [unit(1, null, 2), unit(2, 1, 3), unit(3, 2, 1), unit(4, 1), unit(9, 7)];
  const roots = buildTree(flat);

  it("nests units and promotes orphans to roots", () => {
    expect(roots.map((r) => r.id)).toEqual([1, 9]);
    expect(roots[0].children.map((c) => c.id)).toEqual([2, 4]);
  });

  it("collects subtree ids for move validation", () => {
    expect([...subtreeIds(findNode(roots, 2)!)].sort()).toEqual([2, 3]);
  });

  it("sums employees across the subtree", () => {
    expect(subtreeEmployees(roots[0])).toBe(6);
  });
});
