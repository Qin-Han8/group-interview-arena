import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { checkApiHealth } from "@/lib/api/client";

import HealthStatus from "./health-status";

vi.mock("@/lib/api/client", () => ({
  checkApiHealth: vi.fn(),
}));

const mockedCheckApiHealth = vi.mocked(checkApiHealth);

describe("HealthStatus", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.unstubAllEnvs();
  });

  it("shows an unconfigured state when the public API URL is missing", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "");

    render(<HealthStatus />);

    expect(screen.getByText("API 状态：未配置")).toBeInTheDocument();
    expect(mockedCheckApiHealth).not.toHaveBeenCalled();
  });

  it("shows a checking state while the health request is pending", () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedCheckApiHealth.mockReturnValue(new Promise<boolean>(() => undefined));

    render(<HealthStatus />);

    expect(screen.getByText("API 状态：正在检查")).toBeInTheDocument();
  });

  it("shows a connected state after a successful health response", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedCheckApiHealth.mockResolvedValue(true);

    render(<HealthStatus />);

    expect(await screen.findByText("API 状态：已连接")).toBeInTheDocument();
    expect(mockedCheckApiHealth).toHaveBeenCalledWith("http://localhost:8000");
  });

  it("shows a failed state after a network error", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000");
    mockedCheckApiHealth.mockRejectedValue(new Error("network unavailable"));

    render(<HealthStatus />);

    expect(await screen.findByText("API 状态：连接失败")).toBeInTheDocument();
  });
});
