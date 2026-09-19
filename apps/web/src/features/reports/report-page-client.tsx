"use client";

import { useEffect, useMemo, useState } from "react";
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

import ReportView from "./report-view";

type AuthState =
  | { status: "loading"; baseUrl: string | null }
  | { status: "unauthenticated"; baseUrl: string }
  | { status: "error"; baseUrl: string }
  | { status: "authenticated"; baseUrl: string; user: CurrentUser };

function ReportEntryState({
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
          <p className="auth-task-kicker">Training report</p>
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

export default function ReportPageClient({
  baseUrl,
  sessionId,
}: {
  baseUrl: string | null;
  sessionId: string;
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
  const [logoutPending, setLogoutPending] = useState(false);
  const [logoutError, setLogoutError] = useState<string>();

  useEffect(() => {
    if (!apiClient) return;
    let active = true;
    void getCurrentUser(apiClient)
      .then((result) => {
        if (!active) return;
        if (result.data) {
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
      <ReportEntryState
        heading="报告服务暂不可用"
        message="当前无法连接报告服务，请返回登录页后稍后重试。"
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
      <ReportEntryState
        heading="登录后查看训练报告"
        message="报告仅对本次训练的账户开放。"
      />
    );
  }

  if (authState.status === "error") {
    return (
      <ReportEntryState
        heading="暂时无法确认账户"
        message="认证服务暂时不可用，请返回登录页后稍后重试。"
      />
    );
  }

  const navigation: ProductShellNavigation = {
    activeItem: "report",
    simulation: {
      disabled: false,
      description: "返回训练大厅",
      onActivate: () => router.push("/"),
    },
    report: {
      disabled: true,
      label: "本次训练报告",
      description: "当前页面",
      onActivate: () => undefined,
    },
    settings: {
      onActivate: () => router.push("/settings"),
    },
  };
  const authenticatedApiClient = apiClient;

  async function logout() {
    if (logoutPending) return;
    setLogoutPending(true);
    setLogoutError(undefined);
    try {
      const result = await logoutUser(authenticatedApiClient);
      if (result.error) {
        setLogoutError(getSafeAuthErrorMessage(result.error));
        return;
      }
      router.push("/");
    } catch {
      setLogoutError("无法连接认证服务，请稍后重试。");
    } finally {
      setLogoutPending(false);
    }
  }

  return (
    <AuthenticatedAppShell
      contentScrollMode="page"
      logoutPending={logoutPending}
      navigation={navigation}
      onLogout={() => void logout()}
      pageTitle="训练报告"
      username={authState.user.username}
    >
      {logoutError ? (
        <p
          aria-live="polite"
          className="mx-4 mt-3 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700"
        >
          {logoutError}
        </p>
      ) : null}
      <ReportView
        apiClient={authenticatedApiClient}
        embedded
        sessionId={sessionId}
      />
    </AuthenticatedAppShell>
  );
}
