import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { createApiClient, getCurrentUser, logoutUser } from "@/lib/api/client";
import { TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY } from "@/lib/ui/training-workspace-layout";

import SettingsPageClient from "./settings-page-client";

vi.mock("@/lib/api/client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/api/client")>(
      "@/lib/api/client",
    );
  return {
    ...actual,
    createApiClient: vi.fn(() => ({ client: "settings-route" })),
    getCurrentUser: vi.fn(),
    logoutUser: vi.fn(),
  };
});

const pushRoute = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: pushRoute }),
}));

const mockedCreateApiClient = vi.mocked(createApiClient);
const mockedGetCurrentUser = vi.mocked(getCurrentUser);
const mockedLogoutUser = vi.mocked(logoutUser);
const user = {
  id: "10000000-0000-4000-8000-000000000001",
  username: "settings_owner",
};

function authenticatedUser() {
  mockedGetCurrentUser.mockResolvedValue({
    data: user,
    response: new Response(null, { status: 200 }),
  });
}

describe("SettingsPageClient", () => {
  beforeEach(() => {
    window.localStorage.clear();
    authenticatedUser();
    mockedLogoutUser.mockResolvedValue({
      data: undefined,
      response: new Response(null, { status: 204 }),
    });
  });

  afterEach(() => {
    cleanup();
    window.localStorage.clear();
    vi.restoreAllMocks();
    vi.clearAllMocks();
  });

  it("requires authentication and renders the real username inside the normal Settings Shell", async () => {
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);

    expect(screen.getByText("正在确认账户…")).toBeVisible();
    expect(await screen.findByTestId("studio-shell")).toHaveAttribute(
      "data-presentation-mode",
      "product",
    );
    expect(screen.getByTestId("current-username")).toHaveTextContent(
      "settings_owner",
    );
    expect(
      screen.getByRole("heading", { level: 1, name: "设置" }),
    ).toBeVisible();
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-content-scroll-mode",
      "page",
    );
    expect(
      within(screen.getByRole("navigation", { name: "桌面主导航" })).getByRole(
        "button",
        { name: "设置" },
      ),
    ).toHaveAttribute("aria-current", "page");
    expect(mockedCreateApiClient).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("shows four accessible local sections and keeps reduced motion informational", async () => {
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByTestId("studio-shell");

    const sections = screen.getByRole("tablist", { name: "设置分类" });
    for (const label of ["训练界面", "账户与会话", "隐私与数据", "更多设置"]) {
      expect(within(sections).getByRole("tab", { name: label })).toBeEnabled();
    }
    expect(
      screen.getByRole("heading", { name: "讨论工作区布局" }),
    ).toBeVisible();
    expect(screen.getByText("默认布局")).toBeVisible();
    expect(screen.getByText("减少动态效果")).toBeVisible();
    expect(screen.getByText(/prefers-reduced-motion/)).toBeVisible();
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("uses roving focus and arrow-key navigation for the settings tablist", async () => {
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByTestId("studio-shell");

    const training = screen.getByRole("tab", { name: "训练界面" });
    const account = screen.getByRole("tab", { name: "账户与会话" });
    const privacy = screen.getByRole("tab", { name: "隐私与数据" });
    const more = screen.getByRole("tab", { name: "更多设置" });

    expect(training).toHaveAttribute("tabindex", "0");
    expect(account).toHaveAttribute("tabindex", "-1");
    training.focus();
    fireEvent.keyDown(training, { key: "ArrowRight" });
    expect(account).toHaveFocus();
    expect(account).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("heading", { name: "当前账户" })).toBeVisible();

    fireEvent.keyDown(account, { key: "End" });
    expect(more).toHaveFocus();
    expect(more).toHaveAttribute("aria-selected", "true");
    fireEvent.keyDown(more, { key: "Home" });
    expect(training).toHaveFocus();
    fireEvent.keyDown(training, { key: "ArrowLeft" });
    expect(more).toHaveFocus();
    fireEvent.keyDown(more, { key: "ArrowLeft" });
    expect(privacy).toHaveFocus();
  });

  it("shows a valid custom browser layout and resets only that preference immediately", async () => {
    window.localStorage.setItem("unrelated.preference", "keep-me");
    window.localStorage.setItem(
      TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY,
      JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
    );
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByTestId("studio-shell");

    expect(screen.getByText("已保存自定义布局")).toBeVisible();
    expect(screen.getByText("题目与思考：356px")).toBeVisible();
    expect(screen.getByText("训练进程：336px")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "恢复默认布局" }));

    expect(screen.getByText("默认布局")).toBeVisible();
    expect(screen.getByRole("button", { name: "恢复默认布局" })).toBeDisabled();
    expect(
      window.localStorage.getItem(TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY),
    ).toBeNull();
    expect(window.localStorage.getItem("unrelated.preference")).toBe("keep-me");
    expect(screen.getByText(/下一次进入训练工作区/)).toBeVisible();
  });

  it("treats malformed storage as default and reports reset failure without false success", async () => {
    window.localStorage.setItem(TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY, "{");
    const rendered = render(
      <SettingsPageClient baseUrl="http://localhost:8000" />,
    );
    await screen.findByTestId("studio-shell");
    expect(screen.getByText("默认布局")).toBeVisible();

    rendered.unmount();
    window.localStorage.setItem(
      TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY,
      JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
    );
    vi.spyOn(Storage.prototype, "removeItem").mockImplementationOnce(() => {
      throw new DOMException("blocked", "SecurityError");
    });
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByText("已保存自定义布局");
    fireEvent.click(screen.getByRole("button", { name: "恢复默认布局" }));

    expect(screen.getByText("已保存自定义布局")).toBeVisible();
    expect(screen.getByText(/未能清除浏览器布局偏好/)).toBeVisible();
    expect(screen.queryByText(/已恢复/)).toBeNull();
  });

  it("uses the existing logout flow from the account section", async () => {
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByTestId("studio-shell");
    fireEvent.click(screen.getByRole("tab", { name: "账户与会话" }));

    expect(
      screen.getByText("settings_owner", { selector: "strong" }),
    ).toBeVisible();
    expect(screen.queryByText(/邮箱|手机号|会员|订阅/)).toBeNull();
    expect(
      screen.queryByRole("button", { name: /修改密码|删除账户/ }),
    ).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "退出当前账户" }));
    await waitFor(() => expect(mockedLogoutUser).toHaveBeenCalledOnce());
    expect(pushRoute).toHaveBeenCalledWith("/");
  });

  it("keeps privacy and future sections truthful and non-interactive", async () => {
    render(<SettingsPageClient baseUrl="http://localhost:8000" />);
    await screen.findByTestId("studio-shell");

    fireEvent.click(screen.getByRole("tab", { name: "隐私与数据" }));
    expect(screen.getByText(/当前可用功能/)).toBeVisible();
    expect(screen.queryByText(/当前 P1/)).toBeNull();
    expect(screen.getByText(/会话恢复与训练报告生成/)).toBeVisible();
    expect(screen.getByText(/私人笔记只保留在当前页面内存/)).toBeVisible();
    expect(screen.getByText(/不会发送到 API/)).toBeVisible();
    expect(screen.queryByRole("button", { name: /下载|删除|清空/ })).toBeNull();

    fireEvent.click(screen.getByRole("tab", { name: "更多设置" }));
    for (const label of ["声音与设备", "训练偏好", "通知"]) {
      expect(screen.getByText(label)).toBeVisible();
    }
    expect(screen.getAllByText("后续版本")).toHaveLength(3);
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("button", { name: /保存/ })).toBeNull();
  });

  it("does not expose authenticated Settings when auth is missing or configuration is unavailable", async () => {
    mockedGetCurrentUser.mockResolvedValueOnce({
      error: {},
      response: new Response(null, { status: 401 }),
    } as Awaited<ReturnType<typeof getCurrentUser>>);
    const rendered = render(
      <SettingsPageClient baseUrl="http://localhost:8000" />,
    );
    expect(
      await screen.findByRole("heading", { name: "登录后管理设置" }),
    ).toBeVisible();
    expect(screen.queryByTestId("studio-shell")).toBeNull();

    rendered.rerender(<SettingsPageClient baseUrl={null} />);
    expect(
      await screen.findByRole("heading", { name: "设置服务暂不可用" }),
    ).toBeVisible();
    expect(screen.queryByRole("tablist", { name: "设置分类" })).toBeNull();
  });
});
