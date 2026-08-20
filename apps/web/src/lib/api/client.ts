import createClient from "openapi-fetch";

import type { components, paths } from "./generated/schema";

export const CSRF_HEADER_NAME = "X-GIA-CSRF";
export const CSRF_HEADER_VALUE = "1";

export type ApiClient = ReturnType<typeof createApiClient>;
export type CurrentUser = components["schemas"]["CurrentUserResponse"];
export type ErrorResponse = components["schemas"]["ErrorResponse"];
export type LoginRequest = components["schemas"]["LoginRequest"];
export type RegisterRequest = components["schemas"]["RegisterRequest"];
export type QuestionDetail = components["schemas"]["QuestionDetailResponse"];
export type QuestionSummary = components["schemas"]["QuestionSummaryResponse"];
export type SessionSnapshot = components["schemas"]["SessionSnapshotResponse"];

export function createApiClient(baseUrl: string) {
  return createClient<paths>({ baseUrl, credentials: "include" });
}

export async function checkApiHealth(baseUrl: string): Promise<boolean> {
  const { data, error } = await createApiClient(baseUrl).GET("/health");

  return error === undefined && data?.status === "ok";
}

export function getCurrentUser(client: ApiClient) {
  return client.GET("/auth/me");
}

export function registerUser(client: ApiClient, body: RegisterRequest) {
  return client.POST("/auth/register", {
    body,
    params: { header: { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE } },
  });
}

export function loginUser(client: ApiClient, body: LoginRequest) {
  return client.POST("/auth/login", {
    body,
    params: { header: { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE } },
  });
}

export function logoutUser(client: ApiClient) {
  return client.POST("/auth/logout", {
    params: { header: { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE } },
  });
}

export function listQuestions(client: ApiClient) {
  return client.GET("/questions");
}

export function getQuestion(client: ApiClient, questionVersionId: string) {
  return client.GET("/questions/{question_version_id}", {
    params: { path: { question_version_id: questionVersionId } },
  });
}

export function createSession(client: ApiClient, questionVersionId: string) {
  return client.POST("/sessions", {
    body: { question_version_id: questionVersionId },
    params: { header: { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE } },
  });
}

export function startSession(
  client: ApiClient,
  sessionId: string,
  actionId: string,
) {
  return client.POST("/sessions/{session_id}/start", {
    body: { action_id: actionId },
    params: {
      path: { session_id: sessionId },
      header: { [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE },
    },
  });
}

export function getSessionSnapshot(client: ApiClient, sessionId: string) {
  return client.GET("/sessions/{session_id}", {
    params: { path: { session_id: sessionId } },
  });
}

function isErrorResponse(value: unknown): value is ErrorResponse {
  if (typeof value !== "object" || value === null || !("error" in value)) {
    return false;
  }
  const error = value.error;
  return typeof error === "object" && error !== null && "code" in error;
}

export function getSafeAuthErrorMessage(error: unknown) {
  if (!isErrorResponse(error)) {
    return "请求暂时无法完成，请稍后重试。";
  }

  switch (error.error.code) {
    case "INVALID_USERNAME":
      return "用户名格式不符合要求。";
    case "INVALID_PASSWORD":
      return "密码不符合当前安全要求。";
    case "USERNAME_UNAVAILABLE":
      return "该用户名不可用。";
    case "INVALID_CREDENTIALS":
      return "用户名或密码不正确。";
    case "CSRF_REJECTED":
      return "浏览器安全校验失败，请刷新后重试。";
    default:
      return "请求暂时无法完成，请稍后重试。";
  }
}
