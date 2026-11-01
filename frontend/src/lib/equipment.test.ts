import { describe, expect, it } from "vitest";

import { assignmentPeriod, availableActions, type Equipment } from "./equipment";
import { formatDate } from "./format";

const item = (state: Equipment["state"]): Equipment => ({
  id: 1,
  name: "ThinkPad",
  serial_number: "SN-1",
  state,
});

describe("availableActions", () => {
  it("на складі без історії — усе, включно з видаленням", () => {
    expect(availableActions(item("in_stock"), false)).toEqual([
      "assign",
      "edit",
      "write-off",
      "delete",
    ]);
  });

  it("з історією видач не видаляється — лише списується", () => {
    expect(availableActions(item("in_stock"), true)).not.toContain("delete");
    expect(availableActions(item("in_stock"), true)).toContain("write-off");
  });

  it("видане — лише повернути або відредагувати", () => {
    expect(availableActions(item("assigned"), true)).toEqual(["return", "edit"]);
  });

  it("списане — нічого", () => {
    expect(availableActions(item("written_off"), true)).toEqual([]);
  });
});

describe("assignmentPeriod", () => {
  it("активна видача — з дати", () => {
    expect(assignmentPeriod({ date_assigned: "2024-03-01", date_returned: null }, formatDate)).toBe(
      "з 1 березня 2024 р.",
    );
  });

  it("закрита — діапазон", () => {
    expect(
      assignmentPeriod({ date_assigned: "2024-03-01", date_returned: "2024-05-05" }, formatDate),
    ).toBe("1 березня 2024 р. — 5 травня 2024 р.");
  });
});
