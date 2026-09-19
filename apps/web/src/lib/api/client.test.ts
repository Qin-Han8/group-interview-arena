import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createSession,
  createApiClient,
  getCurrentUser,
  getSafeAuthErrorMessage,
  getQuestion,
  getSessionSnapshot,
  listQuestions,
  loadSessionTranscript,
  loginUser,
  logoutUser,
  registerUser,
  type TranscriptUtterance,
} from "./client";

const BASE_URL = "http://localhost:8000";
const USER = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "web_user",
};
const CREDENTIALS = {
  username: "web_user",
  password: "Abcd123!",
};
const SESSION = {
  id: "00000000-0000-4000-8000-000000000010",
  question_version_id: "21000000-0000-4000-8000-000000000001",
  status: "CREATED" as const,
  created_at: "2026-08-16T00:00:00Z",
  updated_at: "2026-08-16T00:00:00Z",
  last_sequence: 1,
};
const TRANSCRIPT_ITEM: TranscriptUtterance = {
  utterance_id: "00000000-0000-4000-8000-000000000021",
  sequence: 5,
  occurred_at: "2026-08-25T01:04:05Z",
  action_id: "00000000-0000-4000-8000-000000000022",
  participant_id: "00000000-0000-4000-8000-000000000023",
  actor_kind: "HUMAN",
  floor_grant_id: "00000000-0000-4000-8000-000000000024",
  phase: "OPENING_STATEMENTS",
  content: "  exact contribution\nsecond line  ",
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

  it("maps registration password rejection to the actionable public rule", () => {
    expect(
      getSafeAuthErrorMessage({
        error: {
          code: "INVALID_PASSWORD",
          message: "must not be rendered",
          request_id: "00000000-0000-4000-8000-000000000099",
        },
      }),
    ).toBe(
      "密码需为 8–128 位，并同时包含大写英文字母、小写英文字母、数字和符号。",
    );
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

  it("loads an empty transcript page and stops on a null cursor", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      jsonResponse({ items: [], next_after_sequence: null }, 200),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadSessionTranscript(
      createApiClient(BASE_URL),
      SESSION.id,
    );

    expect(result).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("preserves exact transcript content from a one-page response", async () => {
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock.mockResolvedValue(
      jsonResponse(
        { items: [TRANSCRIPT_ITEM], next_after_sequence: null },
        200,
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadSessionTranscript(
      createApiClient(BASE_URL),
      SESSION.id,
    );

    expect(result).toEqual([TRANSCRIPT_ITEM]);
    expect(result[0]?.content).toBe("  exact contribution\nsecond line  ");
  });

  it("loads every transcript page with an exclusive advancing cursor", async () => {
    const secondItem: TranscriptUtterance = {
      ...TRANSCRIPT_ITEM,
      utterance_id: "00000000-0000-4000-8000-000000000025",
      sequence: 12,
      action_id: null,
      actor_kind: "AI",
    };
    const thirdItem: TranscriptUtterance = {
      ...TRANSCRIPT_ITEM,
      utterance_id: "00000000-0000-4000-8000-000000000026",
      sequence: 27,
    };
    const fetchMock = vi.fn<typeof fetch>();
    fetchMock
      .mockResolvedValueOnce(
        jsonResponse({ items: [TRANSCRIPT_ITEM], next_after_sequence: 5 }, 200),
      )
      .mockResolvedValueOnce(
        jsonResponse({ items: [secondItem], next_after_sequence: 12 }, 200),
      )
      .mockResolvedValueOnce(
        jsonResponse({ items: [thirdItem], next_after_sequence: null }, 200),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await loadSessionTranscript(
      createApiClient(BASE_URL),
      SESSION.id,
    );

    expect(result).toEqual([TRANSCRIPT_ITEM, secondItem, thirdItem]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(
      fetchMock.mock.calls.map((call) => {
        const request = call[0];
        if (!(request instanceof Request))
          throw new Error("Expected a Request");
        expect(request.method).toBe("GET");
        expect(request.credentials).toBe("include");
        expect(request.headers.has("X-GIA-CSRF")).toBe(false);
        return new URL(request.url).searchParams;
      }),
    ).toEqual([
      new URLSearchParams({ after_sequence: "0", limit: "200" }),
      new URLSearchParams({ after_sequence: "5", limit: "200" }),
      new URLSearchParams({ after_sequence: "12", limit: "200" }),
    ]);
  });

  it.each([
    ["equal", 5, 5],
    ["lower", 5, 4],
    ["unsafe", 0, Number.MAX_SAFE_INTEGER + 1],
    ["non-integer", 0, 1.5],
  ])(
    "rejects a %s non-null transcript cursor without requesting another page",
    async (_, afterSequence, nextAfterSequence) => {
      const fetchMock = vi.fn<typeof fetch>();
      if (afterSequence > 0) {
        fetchMock.mockResolvedValueOnce(
          jsonResponse({ items: [], next_after_sequence: afterSequence }, 200),
        );
      }
      fetchMock.mockResolvedValueOnce(
        jsonResponse(
          { items: [], next_after_sequence: nextAfterSequence },
          200,
        ),
      );
      vi.stubGlobal("fetch", fetchMock);

      const operation = loadSessionTranscript(
        createApiClient(BASE_URL),
        SESSION.id,
      );

      await expect(operation).rejects.toBeInstanceOf(Error);
      expect(fetchMock).toHaveBeenCalledTimes(afterSequence > 0 ? 2 : 1);
    },
  );

  it.each([
    ["missing data", new Response(null, { status: 204 })],
    [
      "API error",
      jsonResponse(
        {
          error: {
            code: "INTERNAL_ERROR",
            message: "not exposed by loader",
            request_id: "00000000-0000-4000-8000-000000000027",
          },
        },
        500,
      ),
    ],
  ])(
    "rejects %s without continuing transcript pagination",
    async (_, response) => {
      const fetchMock = vi.fn<typeof fetch>();
      fetchMock.mockResolvedValue(response);
      vi.stubGlobal("fetch", fetchMock);

      const operation = loadSessionTranscript(
        createApiClient(BASE_URL),
        SESSION.id,
      );

      await expect(operation).rejects.toBeInstanceOf(Error);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    },
  );
});
