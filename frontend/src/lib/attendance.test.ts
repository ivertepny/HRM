import { describe, expect, it } from "vitest";

import { formatHours, monthRange, nowTime, shiftMonth, shortTime } from "./attendance";

describe("attendance helpers", () => {
  it("shortTime обрізає секунди", () => {
    expect(shortTime("09:05:00")).toBe("09:05");
    expect(shortTime(null)).toBeNull();
  });

  it("nowTime — години й хвилини з нулями", () => {
    expect(nowTime(new Date(2026, 10, 2, 8, 7))).toBe("08:07");
  });

  it("shiftMonth переходить через рік", () => {
    expect(shiftMonth("2026-01", -1)).toBe("2025-12");
    expect(shiftMonth("2026-12", 1)).toBe("2027-01");
  });

  it("monthRange знає довжину місяця", () => {
    expect(monthRange("2028-02")).toEqual({ from: "2028-02-01", to: "2028-02-29" });
  });

  it("formatHours — українська кома", () => {
    expect(formatHours(8.5)).toBe("8,5 год");
    expect(formatHours(null)).toBeNull();
  });
});
