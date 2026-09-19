import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useEffect } from "react";
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

const pushRoute = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushRoute }),
}));

type MockSessionPanelProps = {
  onNavigationStateChange: (
    state:
      | { sessionId: null; status: "loading" | "lobby"; reportAvailable: false }
      | { sessionId: string; status: string; reportAvailable: boolean },
  ) => void;
  openSetupRequest: number;
  openCurrentReportRequest?: {
    requestId: number;
    sessionId: string;
  };
  returnToLobbyRequest: number;
};

let latestSessionPanelProps: MockSessionPanelProps | undefined;
let sessionPanelMountCount = 0;

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
  default: function MockSessionPanel(props: MockSessionPanelProps) {
    latestSessionPanelProps = props;
    useEffect(() => {
      sessionPanelMountCount += 1;
    }, []);
    return <div data-testid="session-panel-boundary">讨论会话</div>;
  },
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
const PASSWORD_REQUIREMENT =
  "密码需为 8–128 位，并同时包含大写英文字母、小写英文字母、数字和符号。";

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
    latestSessionPanelProps = undefined;
    sessionPanelMountCount = 0;
    vi.clearAllMocks();
    vi.unstubAllEnvs();
    pushRoute.mockReset();
  });

  it("opens the real Settings route from the authenticated ProductShell", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 200 }),
    });

    render(<AuthPanel />);
    const navigation = await screen.findByRole("navigation", {
      name: "桌面主导航",
    });
    const settings = within(navigation).getByRole("button", { name: "设置" });
    expect(settings).toBeEnabled();

    fireEvent.click(settings);
    expect(pushRoute).toHaveBeenCalledWith("/settings");
  });

  it("makes new-training navigation truthful for lobby, active, and terminal states", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 200 }),
    });

    render(<AuthPanel />);
    await screen.findByTestId("current-username");
    expect(latestSessionPanelProps).toBeDefined();

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: null,
        status: "lobby",
        reportAvailable: false,
      }),
    );
    const previousSetupRequest = latestSessionPanelProps?.openSetupRequest ?? 0;
    fireEvent.click(screen.getAllByRole("button", { name: "完整模拟" })[0]);
    expect(latestSessionPanelProps?.openSetupRequest).toBe(
      previousSetupRequest + 1,
    );

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: "00000000-0000-4000-8000-000000000010",
        status: "EXPLORATION",
        reportAvailable: false,
      }),
    );
    expect(screen.queryByRole("navigation", { name: "桌面主导航" })).toBeNull();
    expect(screen.getByTestId("studio-shell")).toHaveAttribute(
      "data-presentation-mode",
      "focused-training",
    );

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: "00000000-0000-4000-8000-000000000010",
        status: "ABORTED_USER",
        reportAvailable: false,
      }),
    );
    const previousRequest = latestSessionPanelProps?.returnToLobbyRequest ?? 0;
    fireEvent.click(screen.getAllByRole("button", { name: "完整模拟" })[0]);
    expect(latestSessionPanelProps?.returnToLobbyRequest).toBe(
      previousRequest + 1,
    );
  });

  it("projects truthful report availability and emits only a session-bound report intent", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 200 }),
    });

    render(<AuthPanel />);
    await screen.findByTestId("current-username");
    const reportButton = () =>
      within(screen.getByRole("navigation", { name: "桌面主导航" })).getByRole(
        "button",
        { name: /训练报告/ },
      );

    expect(reportButton()).toBeDisabled();
    expect(reportButton()).toHaveAccessibleName("训练报告 · 正在确认训练状态");

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: null,
        status: "lobby",
        reportAvailable: false,
      }),
    );
    expect(reportButton()).toBeDisabled();
    expect(reportButton()).toHaveAccessibleName("训练报告 · 完成训练后可查看");

    for (const status of [
      "CREATED",
      "PREPARATION",
      "OPENING_STATEMENTS",
      "EXPLORATION",
      "CONFLICT_AND_EVALUATION",
      "CONVERGENCE",
      "FINAL_SUMMARY",
    ]) {
      act(() =>
        latestSessionPanelProps?.onNavigationStateChange({
          sessionId: "00000000-0000-4000-8000-000000000010",
          status,
          reportAvailable: false,
        }),
      );
      expect(
        screen.queryByRole("navigation", { name: "桌面主导航" }),
      ).toBeNull();
      expect(screen.getByTestId("studio-shell")).toHaveAttribute(
        "data-presentation-mode",
        "focused-training",
      );
    }

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: "00000000-0000-4000-8000-000000000010",
        status: "ABORTED_USER",
        reportAvailable: false,
      }),
    );
    expect(reportButton()).toBeDisabled();
    expect(reportButton()).toHaveAccessibleName(
      "训练报告 · 本次训练未完成，暂无报告",
    );

    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: "00000000-0000-4000-8000-000000000010",
        status: "COMPLETED",
        reportAvailable: true,
      }),
    );
    expect(reportButton()).toBeEnabled();
    expect(reportButton()).toHaveAccessibleName(
      "训练报告 · 生成 / 查看本次训练报告",
    );
    expect(latestSessionPanelProps?.openCurrentReportRequest).toBeUndefined();

    fireEvent.click(reportButton());

    expect(latestSessionPanelProps?.openCurrentReportRequest).toEqual({
      requestId: 1,
      sessionId: "00000000-0000-4000-8000-000000000010",
    });
  });

  it("maps the exact non-terminal lifecycle to focused presentation without remounting SessionPanel", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue({
      data: USER,
      response: new Response(null, { status: 200 }),
    });

    render(<AuthPanel />);
    await screen.findByTestId("current-username");
    const originalSessionPanel = screen.getByTestId("session-panel-boundary");
    expect(screen.getByTestId("studio-shell")).toHaveAttribute(
      "data-presentation-mode",
      "product",
    );

    for (const status of [
      "CREATED",
      "PREPARATION",
      "OPENING_STATEMENTS",
      "EXPLORATION",
      "CONFLICT_AND_EVALUATION",
      "CONVERGENCE",
      "FINAL_SUMMARY",
    ]) {
      act(() =>
        latestSessionPanelProps?.onNavigationStateChange({
          sessionId: "00000000-0000-4000-8000-000000000010",
          status,
          reportAvailable: false,
        }),
      );

      expect(screen.getByTestId("studio-shell")).toHaveAttribute(
        "data-presentation-mode",
        "focused-training",
      );
      expect(
        screen.queryByRole("navigation", { name: "桌面主导航" }),
      ).toBeNull();
      expect(
        screen.queryByRole("navigation", { name: "移动主导航" }),
      ).toBeNull();
      expect(
        screen.queryByRole("heading", { level: 1, name: "训练大厅" }),
      ).toBeNull();
      expect(screen.queryByTestId("current-username")).toBeNull();
      expect(screen.getByTestId("session-panel-boundary")).toBe(
        originalSessionPanel,
      );
    }

    expect(sessionPanelMountCount).toBe(1);
  });

  it.each(["COMPLETED", "ABORTED_USER"])(
    "restores normal ProductShell presentation for %s",
    async (status) => {
      vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
      mockedGetCurrentUser.mockResolvedValue({
        data: USER,
        response: new Response(null, { status: 200 }),
      });

      render(<AuthPanel />);
      await screen.findByTestId("current-username");
      act(() =>
        latestSessionPanelProps?.onNavigationStateChange({
          sessionId: "00000000-0000-4000-8000-000000000010",
          status,
          reportAvailable: status === "COMPLETED",
        }),
      );

      expect(screen.getByTestId("studio-shell")).toHaveAttribute(
        "data-presentation-mode",
        "product",
      );
      expect(
        screen.getByRole("navigation", { name: "桌面主导航" }),
      ).toBeVisible();
      expect(
        screen.getByRole("heading", { level: 1, name: "训练大厅" }),
      ).toBeVisible();
      expect(screen.getByTestId("current-username")).toHaveTextContent(
        "web_user",
      );
    },
  );

  it("loads an unauthenticated state without treating 401 as a UI error", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());

    render(<AuthPanel />);

    expect(screen.getByTestId("entry-shell")).toHaveAttribute(
      "data-visual-reference",
      "demo-v2",
    );
    expect(screen.getByTestId("entry-shell")).toHaveAttribute(
      "data-entry-layout",
      "desktop-7-5",
    );
    expect(screen.getByTestId("entry-shell")).toHaveAttribute(
      "data-entry-mobile-layout",
      "single-column",
    );
    expect(screen.getByText("正在检查登录状态…")).toBeInTheDocument();
    expect(
      await screen.findByRole("heading", { name: "登录或注册" }),
    ).toBeInTheDocument();
    expect(screen.getByText("AI 群面训练场")).toBeInTheDocument();
    const status = await screen.findByText("API 状态：已连接");
    expect(status.closest("footer")).toHaveClass("product-entry-diagnostic");
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "一个人，也能练一场真正的群面",
      }),
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Internal validation|Current phase|Target:/i),
    ).toBeNull();
    const authHeading = screen.getByRole("heading", { name: "登录或注册" });
    expect(
      authHeading.compareDocumentPosition(status) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    const benefits = screen.getByRole("list", { name: "训练能力" });
    expect(within(benefits).getAllByRole("listitem")).toHaveLength(3);
    expect(within(benefits).getByText("3 位 AI 候选人")).toBeInTheDocument();
    expect(within(benefits).getByText("真实文字讨论")).toBeInTheDocument();
    expect(within(benefits).getByText("证据化复盘")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "登录", pressed: true }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "注册", pressed: false }),
    ).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "账户入口" })).toHaveAttribute(
      "data-auth-task",
      "credentials",
    );
    expect(screen.getByLabelText("用户名")).toHaveAttribute(
      "autocomplete",
      "username",
    );
    expect(screen.getByLabelText("用户名")).toHaveAttribute("required");
    expect(screen.getByLabelText("用户名")).toHaveAttribute("minlength", "3");
    expect(screen.getByLabelText("用户名")).toHaveAttribute("maxlength", "32");
    expect(screen.getByLabelText("用户名")).toHaveAttribute(
      "pattern",
      "[A-Za-z][A-Za-z0-9_]{2,31}",
    );
    expect(screen.getByLabelText("密码")).toHaveAttribute(
      "autocomplete",
      "current-password",
    );
    expect(screen.getByLabelText("密码")).toHaveAttribute("required");
    expect(screen.getByLabelText("密码")).not.toHaveAttribute("minlength");
    expect(screen.getByLabelText("密码")).toHaveAttribute("maxlength", "128");
    expect(screen.queryByText(PASSWORD_REQUIREMENT)).not.toBeInTheDocument();
    expect(screen.queryByText("安全错误提示")).not.toBeInTheDocument();
    expect(mockedCreateApiClient).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("shows the complete registration-only password requirement before submit", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());

    render(<AuthPanel />);
    await screen.findByRole("heading", { name: "登录或注册" });
    fireEvent.click(screen.getByRole("button", { name: "注册" }));

    const password = screen.getByLabelText("密码");
    expect(screen.getByText(PASSWORD_REQUIREMENT)).toBeInTheDocument();
    expect(password).toHaveAttribute("minlength", "8");
    expect(password).toHaveAttribute("maxlength", "128");
    expect(password).toHaveAttribute(
      "aria-describedby",
      "auth-password-requirement",
    );
    expect(password).toHaveAttribute("autocomplete", "new-password");
  });

  it.each([
    "Ab1!xyz",
    "abcdef1!",
    "ABCDEF1!",
    "Abcdefg!",
    "Abcdefg1",
    "Abcd123 ",
    "Abcd123。",
  ])(
    "rejects invalid registration password %s before making a request",
    async (candidate) => {
      vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
      mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());

      render(<AuthPanel />);
      await screen.findByRole("heading", { name: "登录或注册" });
      fireEvent.click(screen.getByRole("button", { name: "注册" }));
      fireEvent.change(screen.getByLabelText("用户名"), {
        target: { value: "Web_User" },
      });
      fireEvent.change(screen.getByLabelText("密码"), {
        target: { value: candidate },
      });
      fireEvent.submit(screen.getByRole("form", { name: "注册账户" }));

      expect(mockedRegisterUser).not.toHaveBeenCalled();
      expect(screen.getByLabelText("密码")).toHaveAttribute(
        "aria-invalid",
        "true",
      );
      expect(screen.getAllByText(PASSWORD_REQUIREMENT)).toHaveLength(2);
    },
  );

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
    expect(
      screen.getByText("邀请码不会保存到本站本地存储，提交后将从表单清除。", {
        exact: false,
      }),
    ).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "Web_User" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "Abcd123!" },
    });
    fireEvent.change(screen.getByLabelText("邀请码"), {
      target: { value: "unit-only-invite-code" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建账户" }));

    expect(await screen.findByTestId("current-username")).toHaveTextContent(
      "web_user",
    );
    expect(screen.getByTestId("studio-shell")).toHaveClass("product-shell");
    expect(
      screen.getByRole("heading", { level: 1, name: "训练大厅" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("navigation", { name: "桌面主导航" }),
    ).toBeInTheDocument();
    act(() =>
      latestSessionPanelProps?.onNavigationStateChange({
        sessionId: null,
        status: "lobby",
        reportAvailable: false,
      }),
    );
    expect(
      screen.getAllByRole("button", { name: "完整模拟" })[0],
    ).toBeEnabled();
    expect(
      screen.getAllByRole("button", { name: /专项训练/ })[0],
    ).toBeDisabled();
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
      password: "Abcd123!",
      invite_code: "unit-only-invite-code",
    });
    expect(screen.queryByLabelText("密码")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("邀请码")).not.toBeInTheDocument();
  });

  it("clears the invitation secret after a generic enrollment failure", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());
    mockedRegisterUser.mockResolvedValue({
      error: {
        error: {
          code: "ENROLLMENT_UNAVAILABLE",
          message: "must not be rendered",
          request_id: "00000000-0000-4000-8000-000000000004",
        },
      },
      response: new Response(null, { status: 409 }),
    });

    render(<AuthPanel />);
    await screen.findByRole("heading", { name: "登录或注册" });
    fireEvent.click(screen.getByRole("button", { name: "注册" }));
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "Web_User" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "Abcd123!" },
    });
    fireEvent.change(screen.getByLabelText("邀请码"), {
      target: { value: "unit-only-invite-code" },
    });
    fireEvent.click(screen.getByRole("button", { name: "创建账户" }));

    expect(await screen.findByText("安全错误提示")).toBeVisible();
    expect(screen.getByLabelText("邀请码")).toHaveValue("");
    expect(window.localStorage).toHaveLength(0);
    expect(window.sessionStorage).toHaveLength(0);
    expect(screen.queryByText("must not be rendered")).toBeNull();
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

    const error = await screen.findByText("安全错误提示");
    expect(error).toHaveAttribute("id", "auth-error");
    expect(error).toHaveAttribute("aria-live", "polite");
    expect(screen.getByLabelText("用户名")).toHaveAttribute(
      "aria-describedby",
      "auth-error",
    );
    expect(screen.getByLabelText("密码")).toHaveAttribute(
      "aria-describedby",
      "auth-error",
    );
    expect(screen.queryByText("must not be rendered")).not.toBeInTheDocument();
    expect(screen.getByLabelText("密码")).toHaveValue("");
    expect(mockedGetSafeAuthErrorMessage).toHaveBeenCalled();
  });

  it("keeps mode-specific submit feedback visible while authentication is pending", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedGetCurrentUser.mockResolvedValue(unauthenticatedResponse());
    let resolveLogin:
      ((value: Awaited<ReturnType<typeof loginUser>>) => void) | undefined;
    mockedLoginUser.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLogin = resolve;
        }),
    );

    render(<AuthPanel />);
    await screen.findByRole("heading", { name: "登录或注册" });
    fireEvent.change(screen.getByLabelText("用户名"), {
      target: { value: "web_user" },
    });
    fireEvent.change(screen.getByLabelText("密码"), {
      target: { value: "web unit-only password phrase" },
    });
    fireEvent.submit(screen.getByRole("form", { name: "登录账户" }));

    expect(screen.getByRole("button", { name: "正在登录…" })).toBeDisabled();

    resolveLogin?.({
      data: USER,
      response: new Response(null, { status: 200 }),
    });
    expect(await screen.findByTestId("current-username")).toHaveTextContent(
      "web_user",
    );
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
    expect(screen.getByTestId("studio-shell")).toHaveClass("product-shell");
    expect(
      screen.getByRole("heading", { level: 1, name: "训练大厅" }),
    ).toBeInTheDocument();
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
