import { describe, expect, it } from "vitest";

import { catalogRows, cellState, generatePassword, toggle } from "./admin";

const catalog = [
  { codename: "*:*", resource: "*", action: "*", description: "" },
  { codename: "employees:*", resource: "employees", action: "*", description: "" },
  { codename: "employees:read", resource: "employees", action: "read", description: "" },
  { codename: "employees:write", resource: "employees", action: "write", description: "" },
  { codename: "ai:use", resource: "ai", action: "use", description: "" },
  { codename: "users:delete", resource: "users", action: "delete", description: "" },
  { codename: "users:read", resource: "users", action: "read", description: "" },
];

describe("permission matrix", () => {
  it("groups catalog by resource in a stable order without wildcards", () => {
    expect(catalogRows(catalog)).toEqual([
      { resource: "users", label: "Облікові записи", actions: ["read", "delete"] },
      { resource: "employees", label: "Працівники", actions: ["read", "write"] },
      { resource: "ai", label: "AI-асистент", actions: ["use"] },
    ]);
  });

  it("distinguishes explicit and wildcard-implied permissions", () => {
    expect(cellState(["employees:read"], "employees:read")).toBe("on");
    expect(cellState(["employees:*"], "employees:write")).toBe("implied");
    expect(cellState(["*:*"], "ai:use")).toBe("implied");
    expect(cellState(["employees:read"], "employees:write")).toBe("off");
  });

  it("toggles permissions keeping the list sorted", () => {
    expect(toggle(["users:read"], "ai:use")).toEqual(["ai:use", "users:read"]);
    expect(toggle(["ai:use", "users:read"], "ai:use")).toEqual(["users:read"]);
  });
});

describe("generatePassword", () => {
  it("creates long random passwords without look-alike characters", () => {
    const password = generatePassword();
    expect(password).toHaveLength(16);
    expect(password).not.toMatch(/[0O1lI]/);
    expect(generatePassword()).not.toBe(password);
  });
});
