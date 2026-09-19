import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_TRAINING_WORKSPACE_LAYOUT,
  TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY,
  readTrainingWorkspaceLayout,
  readTrainingWorkspaceLayoutPreferenceState,
  resetTrainingWorkspaceLayout,
  writeTrainingWorkspaceLayout,
} from "./training-workspace-layout";

type StorageDouble = Pick<Storage, "getItem" | "removeItem" | "setItem">;

function storageWith(value: string | null): StorageDouble {
  return {
    getItem: vi.fn(() => value),
    removeItem: vi.fn(),
    setItem: vi.fn(),
  };
}

describe("training workspace layout preference", () => {
  it("uses the 280 / 280 default when no preference exists", () => {
    expect(readTrainingWorkspaceLayout(storageWith(null))).toEqual({
      leftWidth: 280,
      rightWidth: 280,
    });
    expect(DEFAULT_TRAINING_WORKSPACE_LAYOUT).toEqual({
      leftWidth: 280,
      rightWidth: 280,
    });
  });

  it("loads only an exact valid v1 preference", () => {
    const storage = storageWith(
      JSON.stringify({ version: 1, leftWidth: 360, rightWidth: 340 }),
    );

    expect(readTrainingWorkspaceLayout(storage)).toEqual({
      leftWidth: 360,
      rightWidth: 340,
    });
    expect(storage.getItem).toHaveBeenCalledWith(
      "gia.training.workspace.layout",
    );
  });

  it("distinguishes a valid custom preference from a default fallback", () => {
    expect(
      readTrainingWorkspaceLayoutPreferenceState(
        storageWith(
          JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
        ),
      ),
    ).toEqual({
      status: "custom",
      layout: { leftWidth: 356, rightWidth: 336 },
    });
    expect(
      readTrainingWorkspaceLayoutPreferenceState(storageWith("{")),
    ).toEqual({
      status: "default",
      layout: { leftWidth: 280, rightWidth: 280 },
    });
  });

  it("makes the next read use defaults after clearing the preference", () => {
    let value: string | null = JSON.stringify({
      version: 1,
      leftWidth: 356,
      rightWidth: 336,
    });
    const storage: StorageDouble = {
      getItem: vi.fn(() => value),
      setItem: vi.fn((_key, nextValue) => {
        value = nextValue;
      }),
      removeItem: vi.fn(() => {
        value = null;
      }),
    };

    expect(resetTrainingWorkspaceLayout(storage)).toBe(true);
    expect(readTrainingWorkspaceLayout(storage)).toEqual({
      leftWidth: 280,
      rightWidth: 280,
    });
  });

  it.each([
    ["malformed JSON", "{"],
    ["null", "null"],
    ["array", "[]"],
    ["missing width", JSON.stringify({ version: 1, leftWidth: 300 })],
    [
      "unsupported version",
      JSON.stringify({ version: 2, leftWidth: 300, rightWidth: 300 }),
    ],
    [
      "string width",
      JSON.stringify({ version: 1, leftWidth: "300", rightWidth: 300 }),
    ],
    ["non-finite width", '{"version":1,"leftWidth":1e400,"rightWidth":300}'],
    [
      "left below range",
      JSON.stringify({ version: 1, leftWidth: 219, rightWidth: 300 }),
    ],
    [
      "left above range",
      JSON.stringify({ version: 1, leftWidth: 421, rightWidth: 300 }),
    ],
    [
      "right below range",
      JSON.stringify({ version: 1, leftWidth: 300, rightWidth: 219 }),
    ],
    [
      "right above range",
      JSON.stringify({ version: 1, leftWidth: 300, rightWidth: 381 }),
    ],
    [
      "extra business field",
      JSON.stringify({
        version: 1,
        leftWidth: 300,
        rightWidth: 300,
        sessionId: "private-session",
      }),
    ],
  ])("falls back entirely for %s", (_label, value) => {
    expect(readTrainingWorkspaceLayout(storageWith(value))).toEqual({
      leftWidth: 280,
      rightWidth: 280,
    });
  });

  it("falls back when storage cannot be read", () => {
    const storage = storageWith(null);
    vi.mocked(storage.getItem).mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });

    expect(readTrainingWorkspaceLayout(storage)).toEqual({
      leftWidth: 280,
      rightWidth: 280,
    });
  });

  it("writes only the frozen v1 fields", () => {
    const storage = storageWith(null);

    expect(
      writeTrainingWorkspaceLayout(
        { leftWidth: 320, rightWidth: 336 },
        storage,
      ),
    ).toBe(true);
    expect(storage.setItem).toHaveBeenCalledTimes(1);
    expect(storage.setItem).toHaveBeenCalledWith(
      TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY,
      '{"version":1,"leftWidth":320,"rightWidth":336}',
    );
    const serialized = vi.mocked(storage.setItem).mock.calls[0][1];
    expect(Object.keys(JSON.parse(serialized))).toEqual([
      "version",
      "leftWidth",
      "rightWidth",
    ]);
    expect(serialized).not.toMatch(
      /user|account|session|question|transcript|participant|draft|report|note|phase|websocket/i,
    );
  });

  it("does not throw when writes or resets are unavailable", () => {
    const storage = storageWith(null);
    vi.mocked(storage.setItem).mockImplementation(() => {
      throw new DOMException("full", "QuotaExceededError");
    });
    vi.mocked(storage.removeItem).mockImplementation(() => {
      throw new DOMException("blocked", "SecurityError");
    });

    expect(
      writeTrainingWorkspaceLayout(
        { leftWidth: 320, rightWidth: 336 },
        storage,
      ),
    ).toBe(false);
    expect(resetTrainingWorkspaceLayout(storage)).toBe(false);
  });

  it("clears only the workspace layout preference", () => {
    const storage = storageWith(null);

    expect(resetTrainingWorkspaceLayout(storage)).toBe(true);
    expect(storage.removeItem).toHaveBeenCalledWith(
      "gia.training.workspace.layout",
    );
    expect(storage.removeItem).toHaveBeenCalledTimes(1);
  });
});
