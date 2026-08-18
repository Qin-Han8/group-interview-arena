import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createSession,
  createApiClient,
  getCurrentUser,
  getQuestion,
  getSessionSnapshot,
  listQuestions,
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
const SESSION = {
  id: "00000000-0000-4000-8000-000000000010",
  question_version_id: "21000000-0000-4000-8000-000000000001",
  status: "CREATED" as const,
  created_at: "2026-08-16T00:00:00Z",
  updated_at: "2026-08-16T00:00:00Z",
  last_sequence: 1,
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

  it("creates a session with credentials and the CSRF marker", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(jsonResponse(SESSION, 201));
    vi.stubGlobal("fetch", fetchMock);

    const result = await createSession(
      createApiClient(BASE_URL),
      SESSION.question_version_id,
    );

    expect(result.data).toEqual(SESSION);
    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof Request)) throw new Error("Expected a Request");
    expect(request.url).toBe(`${BASE_URL}/sessions`);
    expect(request.method).toBe("POST");
    expect(request.credentials).toBe("include");
    expect(request.headers.get("X-GIA-CSRF")).toBe("1");
    expect(await request.clone().json()).toEqual({
      question_version_id: SESSION.question_version_id,
    });
  });

  it("loads safe question list and detail without a CSRF marker", async () => {
    const summary = {
      id: SESSION.question_version_id,
      question_template_id: "20000000-0000-4000-8000-000000000001",
      version_number: 1,
      title: "内部验证题",
      question_type: "RESOURCE_ALLOCATION",
      background_domain: "GENERAL",
      difficulty: "STANDARD",
      estimated_minutes: 25,
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(jsonResponse([summary], 200))
      .mockResolvedValueOnce(
        jsonResponse(
          {
            ...summary,
            scenario: "公开情境",
            objective: "公开目标",
            hard_constraints: [],
            soft_constraints: [],
            stakeholders: [],
            options: [],
          },
          200,
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const client = createApiClient(BASE_URL);

    expect((await listQuestions(client)).data).toEqual([summary]);
    expect((await getQuestion(client, summary.id)).data?.scenario).toBe(
      "公开情境",
    );

    for (const call of fetchMock.mock.calls) {
      const request = call[0];
      if (!(request instanceof Request)) throw new Error("Expected a Request");
      expect(request.method).toBe("GET");
      expect(request.credentials).toBe("include");
      expect(request.headers.has("X-GIA-CSRF")).toBe(false);
    }
  });

  it("loads an authoritative session snapshot without a CSRF marker", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(jsonResponse(SESSION, 200));
    vi.stubGlobal("fetch", fetchMock);

    const result = await getSessionSnapshot(
      createApiClient(BASE_URL),
      SESSION.id,
    );

    expect(result.data).toEqual(SESSION);
    const request = fetchMock.mock.calls[0]?.[0];
    if (!(request instanceof Request)) throw new Error("Expected a Request");
    expect(request.url).toBe(`${BASE_URL}/sessions/${SESSION.id}`);
    expect(request.method).toBe("GET");
    expect(request.credentials).toBe("include");
    expect(request.headers.has("X-GIA-CSRF")).toBe(false);
  });
});
