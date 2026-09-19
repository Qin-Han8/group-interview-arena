export const TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY =
  "gia.training.workspace.layout";

export const DEFAULT_TRAINING_WORKSPACE_LAYOUT = {
  leftWidth: 280,
  rightWidth: 280,
} as const;

export const TRAINING_WORKSPACE_LAYOUT_BOUNDS = {
  left: { min: 220, max: 420 },
  right: { min: 220, max: 380 },
  centerMin: 520,
} as const;

export type TrainingWorkspaceLayout = {
  leftWidth: number;
  rightWidth: number;
};

export type TrainingWorkspaceLayoutPreferenceV1 = {
  version: 1;
  leftWidth: number;
  rightWidth: number;
};

export type TrainingWorkspaceLayoutPreferenceState =
  | { status: "default"; layout: TrainingWorkspaceLayout }
  | { status: "custom"; layout: TrainingWorkspaceLayout };

type WorkspaceLayoutStorage = Pick<
  Storage,
  "getItem" | "removeItem" | "setItem"
>;

const PREFERENCE_KEYS = ["leftWidth", "rightWidth", "version"] as const;

function browserStorage(): WorkspaceLayoutStorage | undefined {
  if (typeof window === "undefined") return undefined;
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
}

function defaultLayout(): TrainingWorkspaceLayout {
  return { ...DEFAULT_TRAINING_WORKSPACE_LAYOUT };
}

function hasExactPreferenceKeys(value: Record<string, unknown>): boolean {
  const keys = Object.keys(value).sort();
  return (
    keys.length === PREFERENCE_KEYS.length &&
    PREFERENCE_KEYS.every((key, index) => keys[index] === key)
  );
}

function isWidthWithin(value: unknown, min: number, max: number) {
  return (
    typeof value === "number" &&
    Number.isFinite(value) &&
    value >= min &&
    value <= max
  );
}

function isPreference(
  value: unknown,
): value is TrainingWorkspaceLayoutPreferenceV1 {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return false;
  }
  const record = value as Record<string, unknown>;
  return (
    hasExactPreferenceKeys(record) &&
    record.version === 1 &&
    isWidthWithin(
      record.leftWidth,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.max,
    ) &&
    isWidthWithin(
      record.rightWidth,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.max,
    )
  );
}

function isLayout(value: TrainingWorkspaceLayout): boolean {
  return (
    isWidthWithin(
      value.leftWidth,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.min,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.left.max,
    ) &&
    isWidthWithin(
      value.rightWidth,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.min,
      TRAINING_WORKSPACE_LAYOUT_BOUNDS.right.max,
    )
  );
}

export function readTrainingWorkspaceLayoutPreferenceState(
  storage: WorkspaceLayoutStorage | undefined = browserStorage(),
): TrainingWorkspaceLayoutPreferenceState {
  const fallback = (): TrainingWorkspaceLayoutPreferenceState => ({
    status: "default",
    layout: defaultLayout(),
  });
  if (!storage) return fallback();
  try {
    const serialized = storage.getItem(TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY);
    if (serialized === null) return fallback();
    const parsed: unknown = JSON.parse(serialized);
    if (!isPreference(parsed)) return fallback();
    return {
      status: "custom",
      layout: {
        leftWidth: parsed.leftWidth,
        rightWidth: parsed.rightWidth,
      },
    };
  } catch {
    return fallback();
  }
}

export function readTrainingWorkspaceLayout(
  storage: WorkspaceLayoutStorage | undefined = browserStorage(),
): TrainingWorkspaceLayout {
  return readTrainingWorkspaceLayoutPreferenceState(storage).layout;
}

export function writeTrainingWorkspaceLayout(
  layout: TrainingWorkspaceLayout,
  storage: WorkspaceLayoutStorage | undefined = browserStorage(),
): boolean {
  if (!storage || !isLayout(layout)) return false;
  const preference: TrainingWorkspaceLayoutPreferenceV1 = {
    version: 1,
    leftWidth: layout.leftWidth,
    rightWidth: layout.rightWidth,
  };
  try {
    storage.setItem(
      TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY,
      JSON.stringify(preference),
    );
    return true;
  } catch {
    return false;
  }
}

export function resetTrainingWorkspaceLayout(
  storage: WorkspaceLayoutStorage | undefined = browserStorage(),
): boolean {
  if (!storage) return false;
  try {
    storage.removeItem(TRAINING_WORKSPACE_LAYOUT_STORAGE_KEY);
    return true;
  } catch {
    return false;
  }
}
