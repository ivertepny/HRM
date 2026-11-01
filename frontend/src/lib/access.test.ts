import { describe, expect, it } from "vitest";

import { canAnywhere, matches, type Access } from "./access";
import { activeHref, visibleNavigation } from "./navigation";

const noRoles: Access = { is_superuser: false, global: [], scoped: [] };

describe("matches", () => {
  it.each([
    [["employees:read"], "employees:read", true],
    [["employees:read"], "employees:write", false],
    [["employees:*"], "employees:write", true],
    [["employees:*"], "salary:read", false],
    [["*:*"], "salary:write", true],
  ])("%j covers %s → %s", (granted, codename, expected) => {
    expect(matches(granted, codename)).toBe(expected);
  });
});

describe("canAnywhere", () => {
  it("is false while access is not loaded", () => {
    expect(canAnywhere(undefined, "ai:use")).toBe(false);
  });

  it("accepts scoped permissions", () => {
    const access: Access = {
      ...noRoles,
      scoped: [{ unit: { id: 1, name: "IT" }, permissions: ["employees:read"] }],
    };
    expect(canAnywhere(access, "employees:read")).toBe(true);
  });

  it("gives superusers everything", () => {
    expect(canAnywhere({ ...noRoles, is_superuser: true }, "roles:manage")).toBe(true);
  });
});

describe("visibleNavigation", () => {
  const labels = (access: Access) =>
    visibleNavigation(access).flatMap((g) => g.items.map((i) => i.label));

  it("shows only own-data sections to a user without roles", () => {
    expect(labels(noRoles)).toEqual(["Мій профіль", "Мої відпустки"]);
  });

  it("drops groups that end up empty", () => {
    const groups = visibleNavigation(noRoles).map((g) => g.label);
    expect(groups).toEqual(["Я"]);
  });

  it("shows HR sections for scoped HR permissions", () => {
    const hr: Access = {
      ...noRoles,
      global: ["ai:use"],
      scoped: [
        { unit: { id: 3, name: "IT" }, permissions: ["employees:read", "vacations:manage"] },
      ],
    };
    expect(labels(hr)).toEqual([
      "Мій профіль",
      "Мої відпустки",
      "AI-асистент",
      "Працівники",
      "Відпустки команди",
    ]);
  });
});

describe("activeHref", () => {
  it.each([
    ["/vacations", "/vacations"],
    ["/vacations/review", "/vacations/review"],
    ["/profile", "/profile"],
    ["/unknown", undefined],
  ])("%s → %s", (pathname, expected) => {
    expect(activeHref(pathname)).toBe(expected);
  });
});
