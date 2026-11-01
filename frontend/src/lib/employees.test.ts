import { describe, expect, it } from "vitest";

import { changedFields, fileHref, isFired, unitPath } from "./employees";
import { PEOPLE, plural } from "./format";

describe("employees helpers", () => {
  it("joins unit ancestors into a readable path", () => {
    expect(
      unitPath({
        name: "Backend",
        ancestors: [
          { id: 1, name: "Головний офіс", type: "Офіс" },
          { id: 2, name: "IT", type: "Департамент" },
        ],
      }),
    ).toBe("Головний офіс > IT > Backend");
    expect(unitPath({ name: "HQ", ancestors: [] })).toBe("HQ");
  });

  it("treats future dismissal dates as still working", () => {
    expect(isFired({ date_fired: null }, "2026-11-01")).toBe(false);
    expect(isFired({ date_fired: "2026-12-01" }, "2026-11-01")).toBe(false);
    expect(isFired({ date_fired: "2026-11-01" }, "2026-11-01")).toBe(true);
  });

  it("routes local media through Next and keeps S3 links", () => {
    expect(fileHref("http://api:8000/media/employees/3/documents/a.pdf")).toBe(
      "/media/employees/3/documents/a.pdf",
    );
    const s3 = "https://bucket.s3.eu-north-1.amazonaws.com/employees/3/a.pdf?X-Amz-Signature=x";
    expect(fileHref(s3)).toBe(s3);
    expect(fileHref(null)).toBeUndefined();
  });

  it("keeps only changed fields", () => {
    expect(
      changedFields(
        { position_id: 1, level: "junior", salary: "1000.00" },
        { position_id: 1, level: "middle", salary: "1000.00" },
      ),
    ).toEqual({ level: "middle" });
  });
});


describe("plural", () => {
  it.each([
    [1, "працівник"],
    [3, "працівники"],
    [4, "працівники"],
    [5, "працівників"],
    [11, "працівників"],
    [21, "працівник"],
    [22, "працівники"],
  ])("%i %s", (count, word) => {
    expect(plural(count, PEOPLE)).toBe(word);
  });
});
