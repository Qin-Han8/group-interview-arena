"use client";

import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

import SessionPanel, {
  type OpenCurrentReportRequest,
  type SessionNavigationState,
} from "@/features/sessions/session-panel";
import {
  createApiClient,
  getCurrentUser,
  getSafeAuthErrorMessage,
  loginUser,
  logoutUser,
  registerUser,
  type CurrentUser,
} from "@/lib/api/client";
import { getPublicApiConfig } from "@/lib/config/public-env";

import HealthStatus from "./health-status";
import {
  AuthenticatedAppShell,
  ProductEntryShell,
  type ProductShellNavigation,
} from "./product-shell";

type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "authenticated"; user: CurrentUser };

type AuthMode = "login" | "register";

const REGISTRATION_PASSWORD_REQUIREMENT =
  "密码需为 8–128 位，并同时包含大写英文字母、小写英文字母、数字和符号。";
const ASCII_PUNCTUATION = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";

function isValidRegistrationPassword(password: string) {
  const characters = [...password];
  return (
    characters.length >= 8 &&
    characters.length <= 128 &&
    characters.some((character) => character >= "A" && character <= "Z") &&
    characters.some((character) => character >= "a" && character <= "z") &&
    characters.some((character) => character >= "0" && character <= "9") &&
    characters.some((character) => ASCII_PUNCTUATION.includes(character))
  );
}

function usesFocusedTrainingPresentation(state: SessionNavigationState) {
  if (state.sessionId === null) return false;

  switch (state.status) {
    case "CREATED":
    case "PREPARATION":
    case "OPENING_STATEMENTS":
    case "EXPLORATION":
    case "CONFLICT_AND_EVALUATION":
    case "CONVERGENCE":
    case "FINAL_SUMMARY":
      return true;
    case "COMPLETED":
    case "ABORTED_USER":
      return false;
  }
}

export default function AuthPanel() {
  const router = useRouter();
  const config = getPublicApiConfig();
  const baseUrl = config.status === "configured" ? config.baseUrl : undefined;
  const client = useMemo(
    () => (baseUrl ? createApiClient(baseUrl) : undefined),
    [baseUrl],
  );
  const [authState, setAuthState] = useState<AuthState>({ status: "loading" });
  const [mode, setMode] = useState<AuthMode>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>();
  const [sessionNavigationState, setSessionNavigationState] =
    useState<SessionNavigationState>({
      sessionId: null,
      status: "loading",
      reportAvailable: false,
    });
  const [openSetupRequest, setOpenSetupRequest] = useState(0);
  const [returnToLobbyRequest, setReturnToLobbyRequest] = useState(0);
  const [openCurrentReportRequest, setOpenCurrentReportRequest] =
    useState<OpenCurrentReportRequest>();

  function startNewTraining() {
    if (sessionNavigationState.status === "lobby") {
      setOpenSetupRequest((request) => request + 1);
      return;
    }
    if (
      sessionNavigationState.status === "COMPLETED" ||
      sessionNavigationState.status === "ABORTED_USER"
    ) {
      setReturnToLobbyRequest((request) => request + 1);
    }
  }

  const hasActiveSession =
    sessionNavigationState.sessionId !== null &&
    sessionNavigationState.status !== "COMPLETED" &&
    sessionNavigationState.status !== "ABORTED_USER";
  const hasTerminalSession =
    sessionNavigationState.status === "COMPLETED" ||
    sessionNavigationState.status === "ABORTED_USER";
  const presentationMode = usesFocusedTrainingPresentation(
    sessionNavigationState,
  )
    ? "focused-training"
    : "product";

  const reportNavigation = (() => {
    if (sessionNavigationState.status === "loading") {
      return {
        disabled: true,
        label: "正在确认训练状态",
        description: "正在确认报告是否可用",
      };
    }
    if (sessionNavigationState.status === "lobby") {
      return {
        disabled: true,
        label: "完成训练后可查看",
        description: "完成一次训练后生成报告",
      };
    }
    if (sessionNavigationState.status === "ABORTED_USER") {
      return {
        disabled: true,
        label: "本次训练未完成，暂无报告",
        description: "开始新训练后再试一次",
      };
    }
    if (
      sessionNavigationState.status === "COMPLETED" &&
      sessionNavigationState.reportAvailable
    ) {
      return {
        disabled: false,
        label: "生成 / 查看本次训练报告",
        description: "基于当前完成场次",
      };
    }
    return {
      disabled: true,
      label: "训练完成后生成报告",
      description: "完成当前训练后可查看",
    };
  })();

  const navigation: ProductShellNavigation = {
    activeItem: "simulation",
    simulation: {
      disabled: sessionNavigationState.status === "loading" || hasActiveSession,
      description: hasActiveSession
        ? "请先结束当前训练"
        : hasTerminalSession
          ? "返回训练大厅"
          : null,
      onActivate: startNewTraining,
    },
    report: {
      ...reportNavigation,
      onActivate: () => {
        if (
          sessionNavigationState.sessionId === null ||
          sessionNavigationState.status !== "COMPLETED" ||
          !sessionNavigationState.reportAvailable
        ) {
          return;
        }
        const sessionId = sessionNavigationState.sessionId;
        setOpenCurrentReportRequest((request) => ({
          requestId: (request?.requestId ?? 0) + 1,
          sessionId,
        }));
      },
    },
    settings: {
      onActivate: () => router.push("/settings"),
    },
  };

  useEffect(() => {
    let active = true;

    async function loadCurrentUser() {
      if (!client) {
        if (active) {
          setAuthState({ status: "unauthenticated" });
          setErrorMessage("API 地址未正确配置。");
        }
        return;
      }

      try {
        const { data, error, response } = await getCurrentUser(client);
        if (!active) return;

        if (data) {
          setAuthState({ status: "authenticated", user: data });
          return;
        }

        setAuthState({ status: "unauthenticated" });
        if (response.status !== 401) {
          setErrorMessage(getSafeAuthErrorMessage(error));
        }
      } catch {
        if (active) {
          setAuthState({ status: "unauthenticated" });
          setErrorMessage("无法连接认证服务，请稍后重试。");
        }
      }
    }

    void loadCurrentUser();
    return () => {
      active = false;
    };
  }, [client]);

  async function submitCredentials(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!client || pending) return;

    if (mode === "register" && !isValidRegistrationPassword(password)) {
      setErrorMessage(REGISTRATION_PASSWORD_REQUIREMENT);
      return;
    }

    setPending(true);
    setErrorMessage(undefined);
    try {
      const result =
        mode === "register"
          ? await registerUser(client, { username, password })
          : await loginUser(client, { username, password });

      setPassword("");
      if (result.data) {
        setSessionNavigationState({
          sessionId: null,
          status: "loading",
          reportAvailable: false,
        });
        setAuthState({ status: "authenticated", user: result.data });
      } else {
        setErrorMessage(getSafeAuthErrorMessage(result.error));
      }
    } catch {
      setPassword("");
      setErrorMessage("无法连接认证服务，请稍后重试。");
    } finally {
      setPending(false);
    }
  }

  async function logout() {
    if (!client || pending) return;

    setPending(true);
    setErrorMessage(undefined);
    try {
      const { error } = await logoutUser(client);
      if (error) {
        setErrorMessage(getSafeAuthErrorMessage(error));
        return;
      }
      setAuthState({ status: "unauthenticated" });
      setSessionNavigationState({
        sessionId: null,
        status: "loading",
        reportAvailable: false,
      });
      setUsername("");
      setPassword("");
    } catch {
      setErrorMessage("无法连接认证服务，请稍后重试。");
    } finally {
      setPending(false);
    }
  }

  if (authState.status === "loading") {
    return (
      <ProductEntryShell diagnostic={<HealthStatus />}>
        <section aria-live="polite" className="auth-loading-state">
          <span aria-hidden="true" className="auth-loading-dot" />
          <p>正在检查登录状态…</p>
        </section>
      </ProductEntryShell>
    );
  }

  if (authState.status === "authenticated") {
    return (
      <AuthenticatedAppShell
        contentScrollMode="contained"
        logoutPending={pending}
        navigation={navigation}
        onLogout={() => void logout()}
        pageTitle="训练大厅"
        presentationMode={presentationMode}
        username={authState.user.username}
      >
        {errorMessage ? (
          <p
            aria-live="polite"
            className="mx-4 mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
          >
            {errorMessage}
          </p>
        ) : null}
        {client && baseUrl ? (
          <SessionPanel
            apiClient={client}
            baseUrl={baseUrl}
            onNavigationStateChange={setSessionNavigationState}
            openCurrentReportRequest={openCurrentReportRequest}
            openSetupRequest={openSetupRequest}
            returnToLobbyRequest={returnToLobbyRequest}
          />
        ) : null}
      </AuthenticatedAppShell>
    );
  }

  const hasRegistrationPasswordError =
    mode === "register" && errorMessage === REGISTRATION_PASSWORD_REQUIREMENT;

  return (
    <ProductEntryShell diagnostic={<HealthStatus />}>
      <section className="auth-task">
        <header className="auth-task-header">
          <p className="auth-task-kicker">Welcome back</p>
          <h2>登录或注册</h2>
          <p>
            {mode === "login"
              ? "继续你的下一场完整模拟。"
              : "创建账户，开始第一次文字群面。"}
          </p>
        </header>
        <div aria-label="认证方式" className="auth-mode-switch">
          {(["login", "register"] as const).map((candidate) => (
            <button
              aria-pressed={mode === candidate}
              key={candidate}
              onClick={() => {
                setMode(candidate);
                setErrorMessage(undefined);
                setPassword("");
              }}
              type="button"
            >
              {candidate === "login" ? "登录" : "注册"}
            </button>
          ))}
        </div>

        <form
          aria-label={mode === "login" ? "登录账户" : "注册账户"}
          className="auth-form"
          onSubmit={(event) => void submitCredentials(event)}
        >
          <label className="auth-field" htmlFor="auth-username">
            <span>用户名</span>
            <input
              aria-describedby={
                errorMessage && !hasRegistrationPasswordError
                  ? "auth-error"
                  : undefined
              }
              autoComplete="username"
              id="auth-username"
              maxLength={32}
              minLength={3}
              onChange={(event) => setUsername(event.target.value)}
              pattern="[A-Za-z][A-Za-z0-9_]{2,31}"
              required
              value={username}
            />
          </label>
          <label className="auth-field" htmlFor="auth-password">
            <span>密码</span>
            <input
              aria-label="密码"
              aria-describedby={
                mode === "register"
                  ? errorMessage
                    ? "auth-password-requirement auth-error"
                    : "auth-password-requirement"
                  : errorMessage
                    ? "auth-error"
                    : undefined
              }
              aria-invalid={hasRegistrationPasswordError || undefined}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              id="auth-password"
              maxLength={128}
              minLength={mode === "register" ? 8 : undefined}
              onChange={(event) => {
                setPassword(event.target.value);
                if (hasRegistrationPasswordError) {
                  setErrorMessage(undefined);
                }
              }}
              onInvalid={(event) => {
                if (mode === "register") {
                  event.preventDefault();
                  setErrorMessage(REGISTRATION_PASSWORD_REQUIREMENT);
                }
              }}
              required
              type="password"
              value={password}
            />
            {mode === "register" ? (
              <small className="auth-field-hint" id="auth-password-requirement">
                {REGISTRATION_PASSWORD_REQUIREMENT}
              </small>
            ) : null}
          </label>
          <button
            className="auth-submit"
            disabled={pending || !client}
            type="submit"
          >
            {pending
              ? mode === "login"
                ? "正在登录…"
                : "正在创建…"
              : mode === "login"
                ? "登录"
                : "创建账户"}
          </button>
        </form>
        {errorMessage ? (
          <p aria-live="polite" className="auth-error" id="auth-error">
            {errorMessage}
          </p>
        ) : null}
      </section>
    </ProductEntryShell>
  );
}
