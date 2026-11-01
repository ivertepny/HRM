import { describe, expect, it } from "vitest";

import {
  annualDaysUsed,
  calendarRows,
  calendarDays,
  dayWord,
  daysInclusive,
  formatRange,
  isCancellable,
  monthDays,
  type Vacation,
} from "./vacations";

const vacation = (overrides: Partial<Vacation>): Vacation => ({
  id: 1,
  employee: { id: 7, name: "Коваль Олена" },
  vacation_type: "annual",
  status: "approved",
  date_start: "2026-11-10",
  date_end: "2026-11-14",
  ...overrides,
});

describe("dates", () => {
  it("counts days inclusively", () => {
    expect(daysInclusive("2026-11-10", "2026-11-14")).toBe(5);
    expect(daysInclusive("2026-11-10", "2026-11-10")).toBe(1);
    expect(daysInclusive("2026-11-10", "2026-11-09")).toBe(0);
  });

  it("counts across DST change without off-by-one", () => {
    expect(daysInclusive("2026-10-24", "2026-10-26")).toBe(3);
  });

  it.each([
    ["2026-11-10", "2026-11-14", "10–14 листопада 2026"],
    ["2026-10-28", "2026-11-03", "28 жовтня – 3 листопада 2026"],
    ["2026-12-30", "2027-01-02", "30 грудня 2026 – 2 січня 2027"],
    ["2026-11-10", "2026-11-10", "10 листопада 2026"],
  ])("formats %s…%s as «%s»", (start, end, expected) => {
    expect(formatRange(start, end)).toBe(expected);
  });

  it.each([
    [1, "день"],
    [3, "дні"],
    [5, "днів"],
    [11, "днів"],
    [12, "днів"],
    [21, "день"],
    [24, "дні"],
  ])("%i %s", (count, word) => {
    expect(dayWord(count)).toBe(word);
  });
});

it.each([
  [1, "1 календарний день"],
  [3, "3 календарні дні"],
  [5, "5 календарних днів"],
])("calendarDays(%i)", (count, text) => {
  expect(calendarDays(count)).toBe(text);
});

describe("isCancellable", () => {
  const today = "2026-11-01";

  it("allows pending and future approved", () => {
    expect(isCancellable(vacation({ status: "pending", date_start: "2026-10-01" }), today)).toBe(true);
    expect(isCancellable(vacation({ status: "approved" }), today)).toBe(true);
  });

  it("forbids started approved and closed requests", () => {
    expect(isCancellable(vacation({ date_start: "2026-11-01" }), today)).toBe(false);
    expect(isCancellable(vacation({ status: "rejected" }), today)).toBe(false);
    expect(isCancellable(vacation({ status: "cancelled" }), today)).toBe(false);
  });
});

describe("annualDaysUsed", () => {
  it("sums approved annual days clipped to the year", () => {
    const list = [
      vacation({}),
      vacation({ date_start: "2025-12-29", date_end: "2026-01-02" }), // 2 дні в 2026
      vacation({ status: "pending" }),
      vacation({ vacation_type: "sick" }),
    ];
    expect(annualDaysUsed(list, 2026)).toBe(7);
  });
});

describe("calendar", () => {
  it("builds month days with weekends and today", () => {
    const days = monthDays(2026, 10, "2026-11-07");
    expect(days).toHaveLength(30);
    expect(days[6]).toMatchObject({ day: 7, weekend: true, today: true });
    expect(days[8].weekend).toBe(false);
  });

  it("places and clips segments, skipping closed requests", () => {
    const rows = calendarRows(
      [
        vacation({ id: 1 }),
        vacation({ id: 2, date_start: "2026-10-28", date_end: "2026-11-03" }),
        vacation({ id: 3, status: "rejected" }),
        vacation({ id: 4, employee: { id: 9, name: "Бондар Ігор" }, date_start: "2026-11-30", date_end: "2026-12-05", status: "pending" }),
        vacation({ id: 5, date_start: "2026-12-01", date_end: "2026-12-02" }),
      ],
      2026,
      10,
    );

    expect(rows.map((r) => r.name)).toEqual(["Бондар Ігор", "Коваль Олена"]);
    const olena = rows[1].segments.map(({ column, span, continuesBefore }) => ({ column, span, continuesBefore }));
    expect(olena).toEqual([
      { column: 10, span: 5, continuesBefore: false },
      { column: 1, span: 3, continuesBefore: true },
    ]);
    expect(rows[0].segments[0]).toMatchObject({ column: 30, span: 1, continuesAfter: true });
  });
});
