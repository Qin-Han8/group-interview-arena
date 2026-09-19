import type { ReactNode } from "react";

export type ProductShellNavigation = {
  activeItem: "simulation" | "report" | "settings";
  simulation: {
    disabled: boolean;
    description: string | null;
    onActivate: () => void;
  };
  report: {
    disabled: boolean;
    label: string;
    description: string | null;
    onActivate: () => void;
  };
  settings: {
    onActivate: () => void;
  };
};

export type AuthenticatedAppShellProps = {
  pageTitle: string;
  username: string;
  logoutPending: boolean;
  onLogout: () => void;
  navigation: ProductShellNavigation;
  contentScrollMode: "contained" | "page";
  presentationMode?: "product" | "focused-training";
  children: ReactNode;
};

type ProductEntryShellProps = {
  children: ReactNode;
  diagnostic?: ReactNode;
};

type NavigationItem = {
  label: string;
  icon:
    | "simulation"
    | "drill"
    | "type"
    | "growth"
    | "sprint"
    | "report"
    | "store"
    | "settings";
};

type NavigationVariant = "full" | "rail" | "top";

const TRAINING_FUTURE_ITEMS: readonly NavigationItem[] = [
  { label: "专项训练", icon: "drill" },
  { label: "题型训练", icon: "type" },
];

const GROWTH_FUTURE_ITEMS: readonly NavigationItem[] = [
  { label: "成长中心", icon: "growth" },
  { label: "冲刺计划", icon: "sprint" },
];

const UTILITY_FUTURE_ITEMS: readonly NavigationItem[] = [
  { label: "场次包", icon: "store" },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="product-brand">
      <span aria-hidden="true" className="product-brand-mark">
        AI
      </span>
      <span className={compact ? "sr-only" : undefined}>AI 群面训练场</span>
    </div>
  );
}

function NavIcon({ kind }: { kind: NavigationItem["icon"] }) {
  const paths: Record<NavigationItem["icon"], ReactNode> = {
    simulation: <path d="M5 6.5h14v12H5zM8 3.5h8M9 10h6M9 14h4" />,
    drill: <path d="M12 3v18M3 12h18M6.5 6.5l11 11M17.5 6.5l-11 11" />,
    type: <path d="M5 5h14M5 12h14M5 19h9" />,
    growth: <path d="m4 17 5-5 3 3 7-8M15 7h4v4" />,
    sprint: <path d="m13 2-8 12h7l-1 8 8-13h-7z" />,
    report: <path d="M6 3h12v18H6zM9 8h6M9 12h6M9 16h4" />,
    store: <path d="M4 9h16l-1 12H5zM8 9a4 4 0 0 1 8 0" />,
    settings: (
      <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-5v2m0 14v2M3 12h2m14 0h2M5.6 5.6 7 7m10 10 1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4" />
    ),
  };
  return (
    <svg
      aria-hidden="true"
      className="size-[1.125rem] shrink-0"
      fill="none"
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      viewBox="0 0 24 24"
    >
      {paths[kind]}
    </svg>
  );
}

function RealNavigationButton({
  accessibleLabel,
  active,
  description,
  disabled,
  icon,
  label,
  onActivate,
  variant,
}: {
  accessibleLabel?: string;
  active: boolean;
  description: string | null;
  disabled: boolean;
  icon: NavigationItem["icon"];
  label: string;
  onActivate: () => void;
  variant: NavigationVariant;
}) {
  const fullAccessibleLabel = accessibleLabel ?? label;

  return (
    <button
      aria-current={active ? "page" : undefined}
      aria-label={fullAccessibleLabel}
      className="product-nav-item"
      disabled={disabled}
      onClick={onActivate}
      title={variant === "rail" ? fullAccessibleLabel : undefined}
      type="button"
    >
      <NavIcon kind={icon} />
      <span className={variant === "rail" ? "sr-only" : undefined}>
        {label}
      </span>
      {variant === "full" && description ? (
        <small className="product-nav-description">{description}</small>
      ) : null}
    </button>
  );
}

function FutureNavigationButton({
  item,
  variant,
}: {
  item: NavigationItem;
  variant: NavigationVariant;
}) {
  const accessibleLabel = `${item.label}（即将开放）`;

  return (
    <button
      aria-label={accessibleLabel}
      className="product-nav-item product-nav-item-future"
      disabled
      title={variant === "rail" ? `${item.label} · 即将开放` : undefined}
      type="button"
    >
      <NavIcon kind={item.icon} />
      <span className={variant === "rail" ? "sr-only" : undefined}>
        {item.label}
      </span>
      {variant === "full" ? <small>即将开放</small> : null}
    </button>
  );
}

function ProductNavigation({
  navigation,
  variant,
}: {
  navigation: ProductShellNavigation;
  variant: NavigationVariant;
}) {
  const navigationLabel = {
    full: "桌面主导航",
    rail: "精简侧边栏导航",
    top: "移动主导航",
  }[variant];

  return (
    <nav
      aria-label={navigationLabel}
      className={`product-nav product-nav-${variant}${variant === "top" ? " product-nav-compact" : ""}`}
      data-navigation-variant={variant}
    >
      <section aria-label="Training" className="product-nav-group">
        {variant === "full" ? (
          <p className="product-nav-caption">Training</p>
        ) : null}
        <RealNavigationButton
          active={navigation.activeItem === "simulation"}
          description={navigation.simulation.description}
          disabled={navigation.simulation.disabled}
          icon="simulation"
          label="完整模拟"
          onActivate={navigation.simulation.onActivate}
          variant={variant}
        />
        {TRAINING_FUTURE_ITEMS.map((item) => (
          <FutureNavigationButton
            item={item}
            key={item.label}
            variant={variant}
          />
        ))}
      </section>
      <section aria-label="Growth" className="product-nav-group">
        {variant === "full" ? (
          <p className="product-nav-caption">Growth</p>
        ) : null}
        <RealNavigationButton
          accessibleLabel={`训练报告 · ${navigation.report.label}`}
          active={navigation.activeItem === "report"}
          description={navigation.report.label}
          disabled={navigation.report.disabled}
          icon="report"
          label="训练报告"
          onActivate={navigation.report.onActivate}
          variant={variant}
        />
        {GROWTH_FUTURE_ITEMS.map((item) => (
          <FutureNavigationButton
            item={item}
            key={item.label}
            variant={variant}
          />
        ))}
      </section>
      <section
        aria-label="Utilities"
        className="product-nav-group product-nav-utilities"
        data-navigation-placement="bottom"
      >
        {UTILITY_FUTURE_ITEMS.map((item) => (
          <FutureNavigationButton
            item={item}
            key={item.label}
            variant={variant}
          />
        ))}
        <RealNavigationButton
          active={navigation.activeItem === "settings"}
          description={null}
          disabled={false}
          icon="settings"
          label="设置"
          onActivate={navigation.settings.onActivate}
          variant={variant}
        />
      </section>
    </nav>
  );
}

export function ProductEntryShell({
  children,
  diagnostic,
}: ProductEntryShellProps) {
  return (
    <div
      className="product-entry-shell"
      data-entry-layout="desktop-7-5"
      data-entry-mobile-layout="single-column"
      data-visual-reference="demo-v2"
      data-testid="entry-shell"
    >
      <header className="product-entry-header">
        <Brand />
        <p>文字群面 · 随时开练</p>
      </header>
      <div className="product-entry-layout">
        <section className="product-entry-value">
          <p className="product-entry-kicker">低压力练习 · 真实讨论</p>
          <h1>
            一个人，也能练一场
            <span>真正的群面</span>
          </h1>
          <p className="product-entry-summary">
            和 3 位不同风格的 AI
            候选人进行文字讨论，练习表达、回应、协作与收敛。
          </p>
          <ul className="product-entry-benefits" aria-label="训练能力">
            <li>
              <strong>3 位 AI 候选人</strong>
              <span>不同立场与讨论节奏</span>
            </li>
            <li>
              <strong>真实文字讨论</strong>
              <span>完整经历阶段推进</span>
            </li>
            <li>
              <strong>证据化复盘</strong>
              <span>回到公开发言证据</span>
            </li>
          </ul>
        </section>
        <section
          aria-label="账户入口"
          className="product-entry-card"
          data-auth-task="credentials"
        >
          {children}
          {diagnostic ? (
            <footer className="product-entry-diagnostic">{diagnostic}</footer>
          ) : null}
        </section>
      </div>
    </div>
  );
}

export function AuthenticatedAppShell({
  children,
  contentScrollMode,
  logoutPending,
  navigation,
  onLogout,
  pageTitle,
  presentationMode = "product",
  username,
}: AuthenticatedAppShellProps) {
  const focusedTraining = presentationMode === "focused-training";

  return (
    <section
      className="product-shell"
      data-presentation-mode={presentationMode}
      data-testid="studio-shell"
    >
      {!focusedTraining ? (
        <aside
          aria-label="完整侧边栏"
          className="product-sidebar product-sidebar-full"
          key="product-sidebar-full"
        >
          <Brand />
          <ProductNavigation navigation={navigation} variant="full" />
          <p className="product-sidebar-note">AI 候选人均为虚拟角色</p>
        </aside>
      ) : null}
      {!focusedTraining ? (
        <aside
          aria-label="精简侧边栏"
          className="product-sidebar product-sidebar-rail"
          key="product-sidebar-rail"
        >
          <Brand compact />
          <ProductNavigation navigation={navigation} variant="rail" />
        </aside>
      ) : null}
      <div className="product-shell-body" key="product-content-host">
        {!focusedTraining ? (
          <header className="product-topbar" key="product-topbar">
            <div>
              <p>AI Group Interview Arena</p>
              <h1>{pageTitle}</h1>
            </div>
            <div className="product-account">
              <span aria-hidden="true" className="product-avatar">
                {username.slice(0, 1).toUpperCase()}
              </span>
              <span data-testid="current-username">{username}</span>
              <button disabled={logoutPending} onClick={onLogout} type="button">
                {logoutPending ? "正在退出…" : "退出登录"}
              </button>
            </div>
          </header>
        ) : null}
        {!focusedTraining ? (
          <div className="product-mobile-navigation" key="product-mobile-nav">
            <Brand compact />
            <ProductNavigation navigation={navigation} variant="top" />
          </div>
        ) : null}
        <main
          className="product-main"
          data-content-scroll-mode={contentScrollMode}
          data-scroll-owner={contentScrollMode === "page" ? "main" : "none"}
          data-shell-content={presentationMode}
          key="product-main"
        >
          <div className="product-content-canvas">{children}</div>
        </main>
      </div>
    </section>
  );
}
