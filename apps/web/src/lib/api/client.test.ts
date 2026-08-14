import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  getCurrentUser,
  loginUser,
  logoutUser,
  registerUser,
} from "./client";

const BASE_URL = "http://localhost:8000";
const USER = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "web_user",
};
const CREDENTIALS = {
  username: "web_user",
  password: "web unit-only password phrase",
};

function jsonResponse(body: object, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("browser API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it.each([
    ["register", registerUser, "/auth/register"],
    ["login", loginUser, "/auth/login"],
  ] as const)(
    "sends credentialed %s requests with the CSRF marker",
    async (_, operation, path) => {
      const fetchMock = vi.fn<typeof fetch>();
      fetchMock.mockResolvedValue(
        jsonResponse(USER, path.endsWith("register") ? 201 : 200),
      );
      vi.stubGlobal("fetch", fetchMock);

      const result = await operation(createApiClient(BASE_URL), CREDENTIALS);

      expect(result.data).toEqual(USER);
      const request = fetchMock.mock.calls[0]?.[0];
      expect(request).toBeInstanceOf(Request);
      if (!(request instanceof Request)) throw new Error("Expected a Request");
      expect(request.url).toBe(`${BASE_URL}${path}`);
      expect(request.method).toBe("POST");
      expect(request.credentials).toBe("include");
      expect(request.headers.get("X-GIA-CSRF")).toBe("1");
      expect(await request.clone().json()).toEqual(CREDENTIALS);
    },
  );

  it("does not add the CSRF marker to GET /auth/me", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(jsonResponse(USER, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getCurrentUser(createApiClient(BASE_URL));

    expect(result.data).toEqual(USER);
    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof Request)) throw new Error("Expected a Request");
    expect(request.method).toBe("GET");
    expect(request.credentials).toBe("include");
    expect(request.headers.has("X-GIA-CSRF")).toBe(false);
  });

  it("sends logout with credentials and the CSRF marker", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    const result = await logoutUser(createApiClient(BASE_URL));

    expect(result.error).toBeUndefined();
    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof Request)) throw new Error("Expected a Request");
    expect(request.method).toBe("POST");
    expect(request.credentials).toBe("include");
    expect(request.headers.get("X-GIA-CSRF")).toBe("1");
  });
});
