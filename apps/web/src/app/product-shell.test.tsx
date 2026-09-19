import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  AuthenticatedAppShell,
  ProductEntryShell,
  type ProductShellNavigation,
} from "./product-shell";

function navigation(
  overrides: Partial<ProductShellNavigation> = {},
): ProductShellNavigation {
  return {
    activeItem: "simulation",
    simulation: {
      disabled: false,
      description: null,
      onActivate: vi.fn(),
    },
    report: {
      disabled: false,
      label: "生成 / 查看本次训练报告",
      description: "当前完成场次",
      onActivate: vi.fn(),
    },
    settings: {
      onActivate: vi.fn(),
    },
    ...overrides,
  };
}

describe("ProductShell", () => {
  afterEach(() => {
    cleanup();
  });

  it("places reports with growth and low-frequency actions in a bottom utility group", () => {
    const shellNavigation = navigation();

    render(
      <AuthenticatedAppShell
        contentScrollMode="contained"
        logoutPending={false}
        navigation={shellNavigation}
        onLogout={vi.fn()}
        pageTitle="训练大厅"
        username="web_user"
      >
        <p>真实训练内容</p>
      </AuthenticatedAppShell>,
    );

    const desktopNavigation = screen.getByRole("navigation", {
      name: "桌面主导航",
    });
    expect(within(desktopNavigation).getByText("Training")).toBeInTheDocument();
    expect(within(desktopNavigation).getByText("Growth")).toBeInTheDocument();
    expect(within(desktopNavigation).queryByText("Other")).toBeNull();

    const growthGroup = within(desktopNavigation).getByRole("region", {
      name: "Growth",
    });
    const utilityGroup = within(desktopNavigation).getByRole("region", {
      name: "Utilities",
    });

    const simulation = within(desktopNavigation).getByRole("button", {
      name: "完整模拟",
    });
    const report = within(growthGroup).getByRole("button", {
      name: /训练报告/,
    });
    const settings = within(utilityGroup).getByRole("button", {
      name: "设置",
    });
    expect(
      within(utilityGroup).getByRole("button", {
        name: "场次包（即将开放）",
      }),
    ).toBeDisabled();
    expect(simulation).toHaveAttribute("aria-current", "page");
    fireEvent.click(simulation);
    fireEvent.click(report);
    fireEvent.click(settings);
    expect(shellNavigation.simulation.onActivate).toHaveBeenCalledOnce();
    expect(shellNavigation.report.onActivate).toHaveBeenCalledOnce();
    expect(shellNavigation.settings.onActivate).toHaveBeenCalledOnce();

    for (const label of ["专项训练", "题型训练", "成长中心", "冲刺计划"]) {
      expect(
        within(desktopNavigation).getByRole("button", {
          name: `${label}（即将开放）`,
        }),
      ).toBeDisabled();
    }
    expect(within(desktopNavigation).queryAllByRole("link")).toHaveLength(0);
  });

  it("marks the real Settings destination active without enabling future modules", () => {
    render(
      <AuthenticatedAppShell
        contentScrollMode="page"
        logoutPending={false}
        navigation={navigation({ activeItem: "settings" })}
        onLogout={vi.fn()}
        pageTitle="设置"
        username="web_user"
      >
        <p>设置内容</p>
      </AuthenticatedAppShell>,
    );

    const settings = within(
      screen.getByRole("navigation", { name: "桌面主导航" }),
    ).getByRole("button", { name: "设置" });
    expect(settings).toBeEnabled();
    expect(settings).toHaveAttribute("aria-current", "page");
    expect(
      within(screen.getByRole("navigation", { name: "桌面主导航" })).getByRole(
        "button",
        { name: "场次包（即将开放）" },
      ),
    ).toBeDisabled();
  });

  it("exposes full, icon-rail, and top navigation with equivalent accessible actions", () => {
    render(
      <AuthenticatedAppShell
        contentScrollMode="page"
        logoutPending={false}
        navigation={navigation({ activeItem: "report" })}
        onLogout={vi.fn()}
        pageTitle="训练报告"
        username="web_user"
      >
        <p>报告内容</p>
      </AuthenticatedAppShell>,
    );

    expect(
      screen.getByRole("navigation", { name: "桌面主导航" }),
    ).toHaveAttribute("data-navigation-variant", "full");
    const railNavigation = screen.getByRole("navigation", {
      name: "精简侧边栏导航",
    });
    expect(railNavigation).toHaveAttribute("data-navigation-variant", "rail");
    expect(
      screen.getByRole("navigation", { name: "移动主导航" }),
    ).toHaveAttribute("data-navigation-variant", "top");

    expect(
      within(railNavigation).getByRole("button", {
        name: "训练报告 · 生成 / 查看本次训练报告",
      }),
    ).toHaveAttribute("aria-current", "page");
    expect(
      within(railNavigation).getByRole("button", { name: "设置" }),
    ).toBeEnabled();
    for (const label of [
      "专项训练",
      "题型训练",
      "成长中心",
      "冲刺计划",
      "场次包",
    ]) {
      expect(
        within(railNavigation).getByRole("button", {
          name: `${label}（即将开放）`,
        }),
      ).toBeDisabled();
    }

    expect(screen.getByRole("main")).toHaveAttribute(
      "data-content-scroll-mode",
      "page",
    );
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-scroll-owner",
      "main",
    );
    expect(
      within(screen.getByRole("navigation", { name: "桌面主导航" })).getByRole(
        "button",
        { name: /训练报告/ },
      ),
    ).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("报告内容")).toBeInTheDocument();
  });

  it("keeps truthful disabled report copy visible without invoking its intent", () => {
    const onActivate = vi.fn();
    render(
      <AuthenticatedAppShell
        contentScrollMode="contained"
        logoutPending={false}
        navigation={navigation({
          report: {
            disabled: true,
            label: "本次训练未完成，暂无报告",
            description: "本次训练未完成，暂无报告",
            onActivate,
          },
        })}
        onLogout={vi.fn()}
        pageTitle="训练大厅"
        username="web_user"
      >
        <p>已中止训练</p>
      </AuthenticatedAppShell>,
    );

    const report = within(
      screen.getByRole("navigation", { name: "桌面主导航" }),
    ).getByRole("button", {
      name: "训练报告 · 本次训练未完成，暂无报告",
    });
    expect(report).toBeDisabled();
    fireEvent.click(report);
    expect(onActivate).not.toHaveBeenCalled();
    expect(screen.getByText("本次训练未完成，暂无报告")).toBeVisible();
  });

  it("keeps long report availability copy secondary to the stable navigation label", () => {
    render(
      <AuthenticatedAppShell
        contentScrollMode="page"
        logoutPending={false}
        navigation={navigation()}
        onLogout={vi.fn()}
        pageTitle="训练大厅"
        username="web_user"
      >
        <p>训练内容</p>
      </AuthenticatedAppShell>,
    );

    const desktopNavigation = screen.getByRole("navigation", {
      name: "桌面主导航",
    });
    const report = within(desktopNavigation).getByRole("button", {
      name: "训练报告 · 生成 / 查看本次训练报告",
    });
    expect(report).toBeEnabled();
    expect(within(report).getByText("训练报告")).toBeVisible();
    expect(within(report).getByText("生成 / 查看本次训练报告")).toHaveClass(
      "product-nav-description",
    );
    expect(
      within(report).queryByText("训练报告 · 生成 / 查看本次训练报告"),
    ).toBeNull();
  });

  it("uses a chrome-free viewport composition for focused training", () => {
    render(
      <AuthenticatedAppShell
        contentScrollMode="contained"
        logoutPending={false}
        navigation={navigation()}
        onLogout={vi.fn()}
        pageTitle="训练大厅"
        presentationMode="focused-training"
        username="web_user"
      >
        <section aria-label="专注训练内容">真实讨论工作区</section>
      </AuthenticatedAppShell>,
    );

    expect(screen.getByTestId("studio-shell")).toHaveAttribute(
      "data-presentation-mode",
      "focused-training",
    );
    expect(screen.queryByRole("navigation", { name: "桌面主导航" })).toBeNull();
    expect(
      screen.queryByRole("navigation", { name: "精简侧边栏导航" }),
    ).toBeNull();
    expect(screen.queryByRole("navigation", { name: "移动主导航" })).toBeNull();
    expect(
      screen.queryByRole("heading", { level: 1, name: "训练大厅" }),
    ).toBeNull();
    expect(screen.queryByTestId("current-username")).toBeNull();
    expect(screen.queryByRole("button", { name: "退出登录" })).toBeNull();
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-shell-content",
      "focused-training",
    );
    expect(screen.getByRole("main")).toHaveAttribute(
      "data-scroll-owner",
      "none",
    );
    expect(screen.getByRole("region", { name: "专注训练内容" })).toBeVisible();
  });

  it("keeps entry diagnostics after the primary task content", () => {
    render(
      <ProductEntryShell diagnostic={<p>API 状态：已连接</p>}>
        <section>
          <h2>登录或注册</h2>
        </section>
      </ProductEntryShell>,
    );

    const entry = screen.getByTestId("entry-shell");
    expect(entry).toHaveAttribute("data-entry-layout", "desktop-7-5");
    expect(entry).toHaveAttribute("data-entry-mobile-layout", "single-column");
    expect(screen.getByRole("heading", { name: "登录或注册" })).toBeVisible();
    expect(screen.getByText("API 状态：已连接")).toBeVisible();
    expect(
      screen
        .getByRole("heading", { name: "登录或注册" })
        .compareDocumentPosition(screen.getByText("API 状态：已连接")) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });
});
