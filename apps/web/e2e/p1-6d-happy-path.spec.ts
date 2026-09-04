import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_P16D_API_ORIGIN ?? "http://localhost:8000";
const API_LOG = process.env.GIA_P16D_API_LOG;
const PROVIDER_CALLS = process.env.GIA_P16D_PROVIDER_CALLS;

type Participant = {
  participant_id: string;
  actor_kind: "AI" | "HUMAN" | "SYSTEM";
  seat_order: number;
};
type CurrentGrant = {
  grant_id: string;
  participant_id: string;
  phase: string;
};
type SessionSnapshot = {
  id: string;
  status: string;
  last_sequence: number;
  floor: {
    participants: Participant[];
    current_grant: CurrentGrant | null;
    latest_event: {
      type: "floor.granted" | "floor.released" | "floor.intervention_requested";
      sequence: number;
    } | null;
  };
};
type TranscriptItem = {
  sequence: number;
  participant_id: string;
  actor_kind: "AI" | "HUMAN";
  floor_grant_id: string;
  phase: string;
  content: string;
};
type ProviderCall = {
  workload: "candidate" | "semantic";
  floor_grant_id?: string;
};

test.skip(
  !PROVIDER_CALLS,
  "P1-6D D2-D1 requires its dedicated API/provider/PostgreSQL harness.",
);

test("P1-6D D2-D2 proves Browser reload recovery", async ({ page }) => {
  expect(API_LOG).toBeTruthy();
  expect(PROVIDER_CALLS).toBeTruthy();
  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    server.onMessage((message) => socket.send(message));
  });

  await page.goto("/");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill(`P16D_D2D1_${Date.now().toString(36)}`);
  await page
    .getByLabel("密码")
    .fill(`P1-6D D2-D1 ${crypto.randomUUID()} phrase`);
  await page.getByRole("button", { name: "创建账户" }).click();
  await expect(page.getByRole("heading", { name: "讨论会话" })).toBeVisible();

  const createResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === `${API_BASE_URL}/sessions` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "创建文字会话" }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status()).toBe(201);
  const sessionId = ((await createResponse.json()) as SessionSnapshot).id;

  const fetchSnapshot = () =>
    page.evaluate(
      async ({ apiBaseUrl, session }) => {
        const response = await fetch(`${apiBaseUrl}/sessions/${session}`, {
          credentials: "include",
        });
        if (!response.ok)
          throw new Error(`snapshot failed: ${response.status}`);
        return (await response.json()) as SessionSnapshot;
      },
      { apiBaseUrl: API_BASE_URL, session: sessionId },
    );
  const fetchTranscript = () =>
    page.evaluate(
      async ({ apiBaseUrl, session }) => {
        const response = await fetch(
          `${apiBaseUrl}/sessions/${session}/utterances?after_sequence=0&limit=200`,
          { credentials: "include" },
        );
        if (!response.ok)
          throw new Error(`transcript failed: ${response.status}`);
        return ((await response.json()) as { items: TranscriptItem[] }).items;
      },
      { apiBaseUrl: API_BASE_URL, session: sessionId },
    );
  const readProviderCalls = async (): Promise<ProviderCall[]> => {
    try {
      return (await readFile(PROVIDER_CALLS!, "utf8"))
        .split(/\r?\n/u)
        .filter(Boolean)
        .map((line) => JSON.parse(line) as ProviderCall);
    } catch {
      return [];
    }
  };
  const readApiLogRecords = async (): Promise<Record<string, unknown>[]> =>
    (await readFile(API_LOG!, "utf8"))
      .split(/\r?\n/u)
      .filter(Boolean)
      .flatMap((line) => {
        try {
          return [JSON.parse(line) as Record<string, unknown>];
        } catch {
          return [];
        }
      });
  const readAcceptedConnectionIds = async (): Promise<Set<string>> => {
    const records = await readApiLogRecords();
    return new Set(
      records.flatMap((record) =>
        record.event === "realtime.connection.accepted" &&
        record.session_id === sessionId &&
        typeof record.connection_id === "string"
          ? [record.connection_id]
          : [],
      ),
    );
  };
  const waitForApiLogRecord = (
    predicate: (record: Record<string, unknown>) => boolean,
  ): Promise<Record<string, unknown>> => {
    let matchingRecord: Record<string, unknown> | undefined;
    return expect
      .poll(
        async () => {
          matchingRecord = (await readApiLogRecords()).find(predicate);
          return matchingRecord !== undefined;
        },
        { timeout: 15_000 },
      )
      .toBe(true)
      .then(() => matchingRecord!);
  };
  const waitForNewAcceptedConnection = (
    knownConnectionIds: ReadonlySet<string>,
  ): Promise<string> =>
    waitForApiLogRecord(
      (record) =>
        record.event === "realtime.connection.accepted" &&
        record.session_id === sessionId &&
        typeof record.connection_id === "string" &&
        !knownConnectionIds.has(record.connection_id),
    ).then((record) => record.connection_id as string);

  const initial = await fetchSnapshot();
  const candidates = initial.floor.participants.filter(
    (participant) => participant.actor_kind !== "SYSTEM",
  );
  const humans = candidates.filter(
    (participant) => participant.actor_kind === "HUMAN",
  );
  const ais = candidates.filter(
    (participant) => participant.actor_kind === "AI",
  );
  expect(candidates).toHaveLength(4);
  expect(humans).toHaveLength(1);
  expect(ais).toHaveLength(3);
  expect(
    new Set(ais.map((participant) => participant.participant_id)).size,
  ).toBe(3);
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await page.getByRole("button", { name: "开始讨论" }).click();

  await expect
    .poll(async () => {
      const snapshot = await fetchSnapshot();
      return {
        active:
          snapshot.status !== "PREPARATION" && snapshot.status !== "COMPLETED",
        durableSequenceAdvanced: snapshot.last_sequence > initial.last_sequence,
        deterministicContinuation:
          snapshot.floor.current_grant !== null ||
          snapshot.floor.latest_event?.type === "floor.intervention_requested",
      };
    })
    .toEqual({
      active: true,
      durableSequenceAdvanced: true,
      deterministicContinuation: true,
    });

  const continuationBoundary = await fetchSnapshot();
  const beforeReloadTranscript = await fetchTranscript();
  const beforeReloadCalls = await readProviderCalls();
  const completedRequestGrantsBeforeReload = new Set(
    beforeReloadCalls
      .filter(
        (call) =>
          call.workload === "candidate" &&
          beforeReloadTranscript.some(
            (item) =>
              item.actor_kind === "AI" &&
              item.floor_grant_id === call.floor_grant_id,
          ),
      )
      .map((call) => call.floor_grant_id),
  );
  const sequenceBeforeReload = continuationBoundary.last_sequence;
  const transcriptCountBeforeReload = beforeReloadTranscript.length;
  const completedRequestCountBeforeReload =
    completedRequestGrantsBeforeReload.size;
  const acceptedBeforeReload = await readAcceptedConnectionIds();
  expect(
    continuationBoundary.floor.current_grant !== null ||
      continuationBoundary.floor.latest_event?.type ===
        "floor.intervention_requested",
  ).toBe(true);
  expect(acceptedBeforeReload.size).toBeGreaterThan(0);
  const reloadAccepted = waitForNewAcceptedConnection(acceptedBeforeReload);
  await page.reload();
  const reloadConnectionId = await reloadAccepted;
  expect(reloadConnectionId).toBeTruthy();
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await waitForApiLogRecord(
    (record) =>
      record.event === "realtime.progression.stopped" &&
      record.session_id === sessionId &&
      record.connection_id === reloadConnectionId &&
      record.exception_category === "progression_next_human_granted",
  );

  const [snapshotAfterReload, transcriptAfterReload, callsAfterReload] =
    await Promise.all([
      fetchSnapshot(),
      fetchTranscript(),
      readProviderCalls(),
    ]);
  const completedRequestGrantsAfterReload = callsAfterReload.filter(
    (call) =>
      call.workload === "candidate" &&
      transcriptAfterReload.some(
        (item) =>
          item.actor_kind === "AI" &&
          item.floor_grant_id === call.floor_grant_id,
      ),
  );
  expect(snapshotAfterReload.id).toBe(continuationBoundary.id);
  expect(snapshotAfterReload.last_sequence).toBeGreaterThanOrEqual(
    sequenceBeforeReload,
  );
  expect(transcriptAfterReload.length).toBeGreaterThanOrEqual(
    transcriptCountBeforeReload,
  );
  expect(
    beforeReloadTranscript.every(
      (item, index) =>
        JSON.stringify(item) === JSON.stringify(transcriptAfterReload[index]),
    ),
  ).toBe(true);
  expect(completedRequestGrantsBeforeReload.size).toBe(
    completedRequestCountBeforeReload,
  );
  expect(
    [...completedRequestGrantsBeforeReload].every(
      (grantId) =>
        completedRequestGrantsAfterReload.filter(
          (call) => call.floor_grant_id === grantId,
        ).length === 1,
    ),
  ).toBe(true);
  expect(
    new Set(transcriptAfterReload.map((item) => item.floor_grant_id)).size,
  ).toBe(transcriptAfterReload.length);
});
