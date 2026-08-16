import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createSession,
  getSessionSnapshot,
  type ApiClient,
  type SessionSnapshot,
} from "@/lib/api/client";
import {
  createSessionRealtimeClient,
  type RealtimeConnectionState,
} from "@/lib/realtime/client";
import type { FormalSessionEvent } from "@/lib/realtime/contract";

import SessionPanel from "./session-panel";

vi.mock("@/lib/api/client", () => ({
  createSession: vi.fn(),
  getSessionSnapshot: vi.fn(),
}));
vi.mock("@/lib/realtime/client", () => ({
  createSessionRealtimeClient: vi.fn(),
}));

const SESSION_ID = "00000000-0000-4000-8000-000000000010";
const ACTION_ID = "00000000-0000-4000-8000-000000000011";
const CREATED: SessionSnapshot = {
  id: SESSION_ID,
  status: "CREATED",
  created_at: "2026-08-16T00:00:00Z",
  updated_at: "2026-08-16T00:00:00Z",
  last_sequence: 1,
};
const ABORTED: SessionSnapshot = {
  ...CREATED,
  status: "ABORTED_USER",
  updated_at: "2026-08-16T00:00:01Z",
  last_sequence: 2,
};
const API_CLIENT = { unit: true } as unknown as ApiClient;

const mockedCreateSession = vi.mocked(createSession);
const mockedGetSessionSnapshot = vi.mocked(getSessionSnapshot);
const mockedCreateRealtime = vi.mocked(createSessionRealtimeClient);

function installRealtimeDouble() {
  const start = vi.fn();
  const abort = vi.fn(() => ACTION_ID);
  const stop = vi.fn();
  let options: Parameters<typeof createSessionRealtimeClient>[0] | undefined;
  mockedCreateRealtime.mockImplementation((candidate) => {
    options = candidate;
    return { start, abort, stop };
  });
  return {
    start,
    abort,
    stop,
    options: () => {
      if (!options) throw new Error("Realtime client was not created");
      return options;
    },
  };
}

describe("SessionPanel", () => {
  afterEach(() => {
    cleanup();
    window.history.replaceState({}, "", "/");
    vi.clearAllMocks();
  });

  it("creates, connects, and aborts a minimal session", async () => {
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await screen.findByRole("button", { name: "创建文字会话" });
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));

    expect(await screen.findByText("已创建")).toBeInTheDocument();
    expect(mockedCreateSession).toHaveBeenCalledWith(API_CLIENT);
    expect(new URL(window.location.href).searchParams.get("session_id")).toBe(
      SESSION_ID,
    );
    expect(realtime.start).toHaveBeenCalledOnce();

    realtime
      .options()
      .onConnectionChange("connected" satisfies RealtimeConnectionState);
    fireEvent.click(await screen.findByRole("button", { name: "结束会话" }));
    expect(realtime.abort).toHaveBeenCalledOnce();

    realtime.options().onEvent({
      schema_version: 1,
      type: "session.state_changed",
      session_id: SESSION_ID,
      sequence: 2,
      occurred_at: "2026-08-16T00:00:01Z",
      action_id: ACTION_ID,
      payload: { previous_status: "CREATED", status: "ABORTED_USER" },
    } satisfies FormalSessionEvent);
    expect(await screen.findByText("已由用户结束")).toBeInTheDocument();
    expect(screen.getByTestId("session-sequence")).toHaveTextContent("2");
  });

  it("reloads the authoritative REST snapshot from the session URL", async () => {
    window.history.replaceState({}, "", `/?session_id=${SESSION_ID}`);
    mockedGetSessionSnapshot.mockResolvedValue({
      data: ABORTED,
      response: new Response(null, { status: 200 }),
    });
    const realtime = installRealtimeDouble();

    render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );

    expect(await screen.findByText("已由用户结束")).toBeInTheDocument();
    expect(mockedGetSessionSnapshot).toHaveBeenCalledWith(
      API_CLIENT,
      SESSION_ID,
    );
    expect(mockedCreateRealtime).toHaveBeenCalledWith(
      expect.objectContaining({ snapshot: ABORTED }),
    );
    expect(realtime.start).toHaveBeenCalledOnce();
  });

  it("shows safe realtime errors and closes the connection on unmount", async () => {
    mockedCreateSession.mockResolvedValue({
      data: CREATED,
      response: new Response(null, { status: 201 }),
    });
    const realtime = installRealtimeDouble();
    const rendered = render(
      <SessionPanel apiClient={API_CLIENT} baseUrl="http://localhost:8000" />,
    );
    await screen.findByRole("button", { name: "创建文字会话" });
    fireEvent.click(screen.getByRole("button", { name: "创建文字会话" }));
    await waitFor(() => expect(realtime.start).toHaveBeenCalledOnce());

    realtime.options().onError("实时连接暂时不可用，请稍后重试。");
    expect(
      await screen.findByText("实时连接暂时不可用，请稍后重试。"),
    ).toBeInTheDocument();

    rendered.unmount();
    expect(realtime.stop).toHaveBeenCalledOnce();
  });
});
