import { describe, expect, it } from "vitest";

import { getPublicApiConfig } from "./public-env";

describe("getPublicApiConfig", () => {
  it("treats a missing value as optional configuration", () => {
    expect(getPublicApiConfig(undefined)).toEqual({ status: "missing" });
  });

  it("accepts an explicit HTTP base URL", () => {
    expect(getPublicApiConfig("http://localhost:8000")).toEqual({
      status: "configured",
      baseUrl: "http://localhost:8000",
    });
  });

  it("reports an invalid explicit value", () => {
    expect(getPublicApiConfig("not-a-url")).toEqual({ status: "invalid" });
  });
});
