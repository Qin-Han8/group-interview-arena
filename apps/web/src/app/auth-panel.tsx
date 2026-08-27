"use client";

import {
  useEffect,
  useMemo,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";

import SessionPanel from "@/features/sessions/session-panel";
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

type AuthState =
  | { status: "loading" }
  | { status: "unauthenticated" }
  | { status: "authenticated"; user: CurrentUser };

type AuthMode = "login" | "register";

function EntryShell({ children }: { children: ReactNode }) {
  return (
    <div
      className="mx-auto flex min-h-dvh w-full max-w-3xl flex-col justify-center px-6 py-16 sm:px-10 sm:py-24"
      data-testid="entry-shell"
    >
      <p className="mb-8 text-sm font-medium tracking-[0.16em] text-neutral-500 uppercase">
        Internal validation foundation
      </p>

      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">
        AI 群面训练场
      </h1>
      <p className="mt-3 text-xl text-neutral-600 sm:text-2xl">
        Group Interview Arena
      </p>

      <div className="my-10 space-y-2 border-y border-neutral-300 py-6 text-sm sm:flex sm:gap-10 sm:space-y-0">
        <p>Current phase: P1</p>
        <p>Target: V0.1 Internal Validation</p>
      </div>

      <div className="space-y-2 text-sm leading-6 text-neutral-600">
        <p>AI candidates are virtual characters.</p>
        <p>
          Question-bound text sessions are available for internal validation.
        </p>
        <HealthStatus />
      </div>

      {children}
    </div>
  );
}

export default function AuthPanel() {
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

    setPending(true);
    setErrorMessage(undefined);
    try {
      const result =
        mode === "register"
          ? await registerUser(client, { username, password })
          : await loginUser(client, { username, password });

      setPassword("");
      if (result.data) {
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
      <EntryShell>
        <section
          aria-live="polite"
          className="mt-10 border-t border-neutral-300 pt-6"
        >
          <p className="text-sm text-neutral-600">正在检查登录状态…</p>
        </section>
      </EntryShell>
    );
  }

  if (authState.status === "authenticated") {
    return (
      <section
        className="studio-surface min-h-dvh w-full px-4 py-4 sm:px-6 sm:py-5"
        data-testid="studio-shell"
      >
        <div className="mb-4 flex flex-wrap items-center justify-end gap-3 text-sm text-neutral-600">
          <p>
            当前用户：
            <span
              className="font-medium text-neutral-900"
              data-testid="current-username"
            >
              {authState.user.username}
            </span>
          </p>
          <button
            className="rounded-md border border-neutral-300 bg-white px-3 py-1.5 font-medium text-neutral-800 disabled:opacity-50"
            disabled={pending}
            onClick={() => void logout()}
            type="button"
          >
            {pending ? "正在退出…" : "退出登录"}
          </button>
        </div>
        {errorMessage ? (
          <p aria-live="polite" className="mb-3 text-sm text-red-700">
            {errorMessage}
          </p>
        ) : null}
        {client && baseUrl ? (
          <SessionPanel apiClient={client} baseUrl={baseUrl} />
        ) : null}
      </section>
    );
  }

  return (
    <EntryShell>
      <section className="mt-10 border-t border-neutral-300 pt-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-lg font-medium">登录或注册</h2>
          <div aria-label="认证方式" className="flex border border-neutral-300">
            {(["login", "register"] as const).map((candidate) => (
              <button
                aria-pressed={mode === candidate}
                className="px-3 py-1.5 text-sm aria-pressed:bg-neutral-900 aria-pressed:text-white"
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
        </div>

        <form
          className="mt-5 grid gap-4"
          onSubmit={(event) => void submitCredentials(event)}
        >
          <label className="grid gap-1 text-sm" htmlFor="auth-username">
            用户名
            <input
              autoComplete="username"
              className="border border-neutral-300 bg-white px-3 py-2"
              id="auth-username"
              maxLength={32}
              minLength={3}
              onChange={(event) => setUsername(event.target.value)}
              pattern="[A-Za-z][A-Za-z0-9_]{2,31}"
              required
              value={username}
            />
          </label>
          <label className="grid gap-1 text-sm" htmlFor="auth-password">
            密码
            <input
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              className="border border-neutral-300 bg-white px-3 py-2"
              id="auth-password"
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>
          <button
            className="justify-self-start bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
            disabled={pending || !client}
            type="submit"
          >
            {pending ? "正在提交…" : mode === "login" ? "登录" : "创建账户"}
          </button>
        </form>
        {errorMessage ? (
          <p aria-live="polite" className="mt-3 text-sm text-red-700">
            {errorMessage}
          </p>
        ) : null}
      </section>
    </EntryShell>
  );
}
