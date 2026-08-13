"use client";

import { useEffect, useState } from "react";

import { checkApiHealth } from "@/lib/api/client";
import { getPublicApiConfig } from "@/lib/config/public-env";

type ApiStatus = "unconfigured" | "checking" | "connected" | "failed";

const STATUS_COPY: Record<ApiStatus, string> = {
  unconfigured: "API 状态：未配置",
  checking: "API 状态：正在检查",
  connected: "API 状态：已连接",
  failed: "API 状态：连接失败",
};

export default function HealthStatus() {
  const config = getPublicApiConfig();
  const baseUrl = config.status === "configured" ? config.baseUrl : undefined;
  const [status, setStatus] = useState<ApiStatus>(() => {
    if (config.status === "missing") {
      return "unconfigured";
    }

    return config.status === "invalid" ? "failed" : "checking";
  });

  useEffect(() => {
    if (!baseUrl) {
      return;
    }

    let cancelled = false;

    void checkApiHealth(baseUrl)
      .then((healthy) => {
        if (!cancelled) {
          setStatus(healthy ? "connected" : "failed");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setStatus("failed");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [baseUrl]);

  return <p aria-live="polite">{STATUS_COPY[status]}</p>;
}
