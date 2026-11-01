import { describe, expect, it } from "vitest";

import { safeNext } from "../safe-redirect";
import { backendUrl, forwardHeaders, isAllowedOrigin } from "./proxy-utils";

describe("backendUrl", () => {
  it("keeps the Django path with its trailing slash and query", () => {
    expect(
      backendUrl("http://api:8000", "/api/backend/api/users/me/", "?page=2"),
    ).toBe("http://api:8000/api/users/me/?page=2");
  });
});

describe("isAllowedOrigin", () => {
  it("lets safe methods through without Origin", () => {
    expect(isAllowedOrigin("GET", null, "hrm.local")).toBe(true);
  });

  it("requires same-origin for unsafe methods", () => {
    expect(isAllowedOrigin("POST", "https://hrm.local", "hrm.local")).toBe(true);
    expect(isAllowedOrigin("POST", "https://evil.example", "hrm.local")).toBe(false);
    expect(isAllowedOrigin("DELETE", null, "hrm.local")).toBe(false);
    expect(isAllowedOrigin("PATCH", "not a url", "hrm.local")).toBe(false);
  });
});

describe("forwardHeaders", () => {
  it("replaces browser credentials with the backend token", () => {
    const source = new Headers({
      cookie: "hrm_access=secret",
      authorization: "Bearer forged",
      host: "hrm.local",
      "content-type": "application/json",
    });

    const headers = forwardHeaders(source, "real-token");

    expect(headers.get("cookie")).toBeNull();
    expect(headers.get("host")).toBeNull();
    expect(headers.get("authorization")).toBe("Bearer real-token");
    expect(headers.get("content-type")).toBe("application/json");
  });

  it("sends no Authorization without a token", () => {
    expect(forwardHeaders(new Headers({ authorization: "x" })).get("authorization")).toBeNull();
  });
});

describe("safeNext", () => {
  it.each([
    ["/profile", "/profile"],
    ["/employees?page=2", "/employees?page=2"],
    ["//evil.example", "/"],
    ["/\\evil.example", "/"],
    ["https://evil.example", "/"],
    [null, "/"],
  ])("%s → %s", (next, expected) => {
    expect(safeNext(next)).toBe(expected);
  });
});
