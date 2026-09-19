"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import {
  AuthenticatedAppShell,
  ProductEntryShell,
  type ProductShellNavigation,
} from "@/app/product-shell";
import {
  createApiClient,
  getCurrentUser,
  getSafeAuthErrorMessage,
  logoutUser,
  type CurrentUser,
} from "@/lib/api/client";
import {
  DEFAULT_TRAINING_WORKSPACE_LAYOUT,
  readTrainingWorkspaceLayoutPreferenceState,
  resetTrainingWorkspaceLayout,
  type TrainingWorkspaceLayoutPreferenceState,
} from "@/lib/ui/training-workspace-layout";

type AuthState =
  | { status: "loading"; baseUrl: string | null }
  | { status: "unauthenticated"; baseUrl: string }
  | { status: "error"; baseUrl: string }
  | { status: "authenticated"; baseUrl: string; user: CurrentUser };

type SettingsSection = "training" | "account" | "privacy" | "more";

const SETTINGS_SECTIONS: ReadonlyArray<{
  id: SettingsSection;
  label: string;
  description: string;
}> = [
  { id: "training", label: "训练界面", description: "工作区布局与动态效果" },
  { id: "account", label: "账户与会话", description: "当前账户与退出登录" },
  { id: "privacy", label: "隐私与数据", description: "真实的数据使用边界" },
  { id: "more", label: "更多设置", description: "后续能力说明" },
];

function defaultLayoutState(): TrainingWorkspaceLayoutPreferenceState {
  return {
    status: "default",
    layout: { ...DEFAULT_TRAINING_WORKSPACE_LAYOUT },
  };
}

function SettingsEntryState({
  heading,
  message,
}: {
  heading: string;
  message: string;
}) {
  return (
    <ProductEntryShell>
      <section className="auth-task">
        <header className="auth-task-header">
          <p className="auth-task-kicker">Settings</p>
          <h2>{heading}</h2>
          <p>{message}</p>
        </header>
        <Link className="auth-submit block text-center" href="/">
          返回登录
        </Link>
      </section>
    </ProductEntryShell>
  );
}

function TrainingInterfaceSection({
  layoutState,
  onReset,
  resetError,
}: {
  layoutState: TrainingWorkspaceLayoutPreferenceState;
  onReset: () => void;
  resetError: string | undefined;
}) {
  const custom = layoutState.status === "custom";
  return (
    <section
      aria-labelledby="settings-tab-training"
      className="settings-panel"
      id="settings-panel-training"
      role="tabpanel"
    >
      <header className="settings-panel-header">
        <p className="settings-eyebrow">Training interface</p>
        <h3>讨论工作区布局</h3>
        <p>
          桌面训练中可调整“题目与思考”和“训练进程”的宽度。偏好只保存在当前浏览器，不会同步到其他设备。
        </p>
      </header>

      <div className="settings-layout-card">
        <div>
          <span className="settings-status-dot" data-custom={custom} />
          <div>
            <strong>{custom ? "已保存自定义布局" : "默认布局"}</strong>
            <p>
              {custom
                ? `题目与思考：${layoutState.layout.leftWidth}px · 训练进程：${layoutState.layout.rightWidth}px`
                : "题目与思考：280px · 中间讨论区自适应 · 训练进程：280px"}
            </p>
          </div>
        </div>
        <button disabled={!custom} onClick={onReset} type="button">
          恢复默认布局
        </button>
      </div>
      {custom ? (
        <div className="sr-only">
          <span>题目与思考：{layoutState.layout.leftWidth}px</span>
          <span>训练进程：{layoutState.layout.rightWidth}px</span>
        </div>
      ) : null}
      <p className="settings-reset-note">
        重置后，下一次进入训练工作区将使用默认布局；不会改变其他已打开页面中的训练工作区。
      </p>
      {resetError ? (
        <p aria-live="polite" className="settings-inline-error">
          {resetError}
        </p>
      ) : null}

      <article className="settings-information-row">
        <div>
          <strong>减少动态效果</strong>
          <p>界面自动尊重操作系统或浏览器的 prefers-reduced-motion 设置。</p>
        </div>
        <span>跟随系统</span>
      </article>
    </section>
  );
}

function AccountSection({
  logoutPending,
  onLogout,
  username,
}: {
  logoutPending: boolean;
  onLogout: () => void;
  username: string;
}) {
  return (
    <section
      aria-labelledby="settings-tab-account"
      className="settings-panel"
      id="settings-panel-account"
      role="tabpanel"
    >
      <header className="settings-panel-header">
        <p className="settings-eyebrow">Account & session</p>
        <h3>当前账户</h3>
        <p>这里只呈现当前认证系统真实支持的账户信息与会话动作。</p>
      </header>
      <div className="settings-account-card">
        <div>
          <span>用户名</span>
          <strong>{username}</strong>
        </div>
        <button disabled={logoutPending} onClick={onLogout} type="button">
          {logoutPending ? "正在退出…" : "退出当前账户"}
        </button>
      </div>
    </section>
  );
}

function PrivacySection() {
  return (
    <section
      aria-labelledby="settings-tab-privacy"
      className="settings-panel"
      id="settings-panel-privacy"
      role="tabpanel"
    >
      <header className="settings-panel-header">
        <p className="settings-eyebrow">Privacy & data</p>
        <h3>当前数据边界</h3>
        <p>以下说明只描述当前可用功能，不代表尚未提供的数据管理能力。</p>
      </header>
      <div className="settings-information-list">
        <article className="settings-information-row">
          <div>
            <strong>训练数据</strong>
            <p>公开会话与讨论数据用于当前会话恢复与训练报告生成。</p>
          </div>
          <span>服务端会话数据</span>
        </article>
        <article className="settings-information-row">
          <div>
            <strong>浏览器本地偏好</strong>
            <p>讨论工作区左右栏宽只保存在当前浏览器，不跨设备同步。</p>
          </div>
          <span>仅布局宽度</span>
        </article>
        <article className="settings-information-row">
          <div>
            <strong>私人笔记</strong>
            <p>
              私人笔记只保留在当前页面内存，不会发送到 API，也不会写入
              localStorage；刷新后会消失。
            </p>
          </div>
          <span>页面内存</span>
        </article>
      </div>
    </section>
  );
}

function MoreSection() {
  return (
    <section
      aria-labelledby="settings-tab-more"
      className="settings-panel"
      id="settings-panel-more"
      role="tabpanel"
    >
      <header className="settings-panel-header">
        <p className="settings-eyebrow">More</p>
        <h3>更多设置</h3>
        <p>后续版本将逐步提供更多训练与账户偏好。</p>
      </header>
      <div className="settings-future-list">
        {["声音与设备", "训练偏好", "通知"].map((label) => (
          <article key={label}>
            <strong>{label}</strong>
            <span>后续版本</span>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function SettingsPageClient({
  baseUrl,
}: {
  baseUrl: string | null;
}) {
  const router = useRouter();
  const apiClient = useMemo(
    () => (baseUrl ? createApiClient(baseUrl) : null),
    [baseUrl],
  );
  const [authState, setAuthState] = useState<AuthState>({
    status: "loading",
    baseUrl,
  });
  const [activeSection, setActiveSection] =
    useState<SettingsSection>("training");
  const sectionTabRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [layoutState, setLayoutState] =
    useState<TrainingWorkspaceLayoutPreferenceState>(defaultLayoutState);
  const [logoutPending, setLogoutPending] = useState(false);
  const [pageError, setPageError] = useState<string>();
  const [resetError, setResetError] = useState<string>();

  useEffect(() => {
    if (!apiClient) return;
    let active = true;
    void getCurrentUser(apiClient)
      .then((result) => {
        if (!active) return;
        if (result.data) {
          setLayoutState(readTrainingWorkspaceLayoutPreferenceState());
          setAuthState({
            status: "authenticated",
            baseUrl: baseUrl!,
            user: result.data,
          });
          return;
        }
        setAuthState(
          result.response.status === 401
            ? { status: "unauthenticated", baseUrl: baseUrl! }
            : { status: "error", baseUrl: baseUrl! },
        );
      })
      .catch(() => {
        if (active) setAuthState({ status: "error", baseUrl: baseUrl! });
      });
    return () => {
      active = false;
    };
  }, [apiClient, baseUrl]);

  if (!apiClient) {
    return (
      <SettingsEntryState
        heading="设置服务暂不可用"
        message="当前无法连接账户服务，请返回登录页后稍后重试。"
      />
    );
  }

  if (authState.status === "loading" || authState.baseUrl !== baseUrl) {
    return (
      <ProductEntryShell>
        <section aria-live="polite" className="auth-loading-state">
          <span aria-hidden="true" className="auth-loading-dot" />
          <p>正在确认账户…</p>
        </section>
      </ProductEntryShell>
    );
  }

  if (authState.status === "unauthenticated") {
    return (
      <SettingsEntryState
        heading="登录后管理设置"
        message="设置仅对当前已登录账户开放。"
      />
    );
  }

  if (authState.status === "error") {
    return (
      <SettingsEntryState
        heading="暂时无法确认账户"
        message="认证服务暂时不可用，请返回登录页后稍后重试。"
      />
    );
  }

  const authenticatedApiClient = apiClient;
  const navigation: ProductShellNavigation = {
    activeItem: "settings",
    simulation: {
      disabled: false,
      description: "返回训练大厅",
      onActivate: () => router.push("/"),
    },
    report: {
      disabled: true,
      label: "完成训练后可查看",
      description: "请从完成场次打开报告",
      onActivate: () => undefined,
    },
    settings: {
      onActivate: () => undefined,
    },
  };

  async function logout() {
    if (logoutPending) return;
    setLogoutPending(true);
    setPageError(undefined);
    try {
      const result = await logoutUser(authenticatedApiClient);
      if (result.error) {
        setPageError(getSafeAuthErrorMessage(result.error));
        return;
      }
      router.push("/");
    } catch {
      setPageError("无法连接认证服务，请稍后重试。");
    } finally {
      setLogoutPending(false);
    }
  }

  function resetLayout() {
    setResetError(undefined);
    if (!resetTrainingWorkspaceLayout()) {
      setResetError("未能清除浏览器布局偏好，请稍后重试。");
      return;
    }
    setLayoutState(defaultLayoutState());
  }

  function handleSectionKeyDown(
    event: KeyboardEvent<HTMLButtonElement>,
    currentIndex: number,
  ) {
    let nextIndex: number | undefined;
    if (event.key === "ArrowRight") {
      nextIndex = (currentIndex + 1) % SETTINGS_SECTIONS.length;
    } else if (event.key === "ArrowLeft") {
      nextIndex =
        (currentIndex - 1 + SETTINGS_SECTIONS.length) %
        SETTINGS_SECTIONS.length;
    } else if (event.key === "Home") {
      nextIndex = 0;
    } else if (event.key === "End") {
      nextIndex = SETTINGS_SECTIONS.length - 1;
    }
    if (nextIndex === undefined) return;

    event.preventDefault();
    setActiveSection(SETTINGS_SECTIONS[nextIndex].id);
    sectionTabRefs.current[nextIndex]?.focus();
  }

  return (
    <AuthenticatedAppShell
      contentScrollMode="page"
      logoutPending={logoutPending}
      navigation={navigation}
      onLogout={() => void logout()}
      pageTitle="设置"
      username={authState.user.username}
    >
      <div className="settings-page" data-testid="settings-page">
        <header className="settings-page-header">
          <p className="settings-eyebrow">Settings</p>
          <h2>偏好与账户</h2>
          <p>管理训练界面、账户会话与当前数据边界</p>
        </header>
        {pageError ? (
          <p aria-live="polite" className="settings-inline-error">
            {pageError}
          </p>
        ) : null}
        <div className="settings-layout">
          <div
            aria-label="设置分类"
            className="settings-section-tabs"
            role="tablist"
          >
            {SETTINGS_SECTIONS.map((section, index) => (
              <button
                aria-label={section.label}
                aria-controls={`settings-panel-${section.id}`}
                aria-selected={activeSection === section.id}
                id={`settings-tab-${section.id}`}
                key={section.id}
                onClick={() => setActiveSection(section.id)}
                onKeyDown={(event) => handleSectionKeyDown(event, index)}
                ref={(element) => {
                  sectionTabRefs.current[index] = element;
                }}
                role="tab"
                tabIndex={activeSection === section.id ? 0 : -1}
                type="button"
              >
                <strong>{section.label}</strong>
                <span>{section.description}</span>
              </button>
            ))}
          </div>
          <div className="settings-content">
            {activeSection === "training" ? (
              <TrainingInterfaceSection
                layoutState={layoutState}
                onReset={resetLayout}
                resetError={resetError}
              />
            ) : null}
            {activeSection === "account" ? (
              <AccountSection
                logoutPending={logoutPending}
                onLogout={() => void logout()}
                username={authState.user.username}
              />
            ) : null}
            {activeSection === "privacy" ? <PrivacySection /> : null}
            {activeSection === "more" ? <MoreSection /> : null}
          </div>
        </div>
      </div>
    </AuthenticatedAppShell>
  );
}
