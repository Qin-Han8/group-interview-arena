import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createApiClient,
  getCurrentUser,
  getSafeAuthErrorMessage,
  loginUser,
  logoutUser,
  registerUser,
} from "@/lib/api/client";

import AuthPanel from "./auth-panel";

vi.mock("@/lib/api/client", () => ({
  checkApiHealth: vi.fn(async () => true),
  createApiClient: vi.fn(() => ({ client: "unit-only" })),
  getCurrentUser: vi.fn(),
  getSafeAuthErrorMessage: vi.fn(() => "安全错误提示"),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
}));
vi.mock("@/features/sessions/session-panel", () => ({
  default: () => <div data-testid="session-panel-boundary">讨论会话</div>,
}));

const mockedCreateApiClient = vi.mocked(createApiClient);
const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedGetSafeAuthErrorMessage = vi.mocked(getSafeAuthErrorMessage);
const mockedLoginUser = vi.mocked(loginUser);
const mockedLogoutUser = vi.mocked(logoutUser);
const mockedRegisterUser = vi.mocked(registerUser);
const USER = {
  id: "00000000-0000-4000-8000-000000000001",
  username: "web_user",
};

function unauthenticatedResponse() {
  return {
    error: {
      error: {
        code: "AUTHENTICATION_REQUIRED" as const,
        message: "Authentication is required.",
        request_id: "00000000-0000-4000-8000-000000000002",
      },
    },
    response: new Response(null, { status: 401 }),
  };
}

describe("AuthPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it("loads an unauthenticated state without treating 401 as a UI error", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());

    render(<AuthPanel />);

    expect(screen.getByTestId("entry-shell")).toHaveClass("max-w-3xl");
    expect(screen.getByText("正在检查登录状态…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "登录或注册" }),
    ).toBeInTheDocument();
    expect(screen.getByTestId("entry-shell")).toHaveClass("max-w-3xl");
    expect(
      screen.getByRole("heading", { level: 1, name: "AI 群面训练场" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("API 状态：已连接")).toBeInTheDocument();
    expect(screen.queryByText("安全错误提示")).not.toBeInTheDocument();
    expect(mockedCreateApiClient).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("registers and replaces the form with the authenticated user", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());
    mockedRegisterUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 201 }),
    });

    render(<AuthPanel />);
    await screen.findByRole("heading", { name: "登录或注册" });
    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "Web_User" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "web unit-only password phrase" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建账户" }));

    expect(await screen.findByTestId("current-username")).toHaveTextContent(
      "web_user",
    );
    expect(screen.getByTestId("studio-shell")).toHaveClass("w-full");
    expect(screen.getByTestId("session-panel-boundary")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "退出登录" }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("entry-shell")).not.toBeInTheDocument();
    expect(
      screen.queryByText("Internal validation foundation"),
    ).not.toBeInTheDocument();
    expect(mockedRegisterUser).toHaveBeenCalledWith(expect.anything(), {
      username: "Web_User",
      password: "web unit-only password phrase",
    });
    expect(screen.queryByLabelText("密码")).not.toBeInTheDocument();
  });

  it("shows a safe login error category and clears password state", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());
    mockedLoginUser.mockResolvedValue({
      error: {
        error: {
          code: "INVALID_CREDENTIALS",
          message: "must not be rendered",
          request_id: "00000000-0000-4000-8000-000000000003",
        },
      },
      response: new Response(null, { status: 401 }),
    });

    render(<AuthPanel />);
    await screen.findByRole("heading", { name: "登录或注册" });
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "web_user" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "wrong unit-only password" },
    });
    fireEvent.click(
      screen.getByText("登录", { selector: 'button[type="submit"]' }),
    );

    expect(await screen.findByText("安全错误提示")).toBeInTheDocument();
    expect(screen.queryByText("must not be rendered")).not.toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toHaveValue("");
    expect(mockedGetSafeAuthErrorMessage).toHaveBeenCalled();
  });

  it("restores an authenticated user and logs out", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 200 }),
    });
    mockedLogoutUser.mockResolvedValue({
      data: undefined,
      response: new Response(null, { status: 204 }),
    });

    render(<AuthPanel />);
    expect(await screen.findByTestId("current-username")).toHaveTextContent(
      "web_user",
    );
    expect(screen.getByTestId("studio-shell")).toHaveClass("w-full");
    expect(screen.getByTestId("session-panel-boundary")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "退出登录" }));

    await waitFor(() => {
      expect(
        screen.getByRole("heading", { name: "登录或注册" }),
      ).toBeInTheDocument();
    });
    expect(mockedLogoutUser).toHaveBeenCalledOnce();
  });
});
