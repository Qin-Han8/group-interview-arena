import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const API_BASE_URL =
  process.env.GIA_P16D_D2D3_API_ORIGIN ?? "http://localhost:8000";
const API_LOG = process.env.GIA_P16D_D2D3_API_LOG;
const PROVIDER_BLOCKED = process.env.GIA_P16D_D2D3_PROVIDER_BLOCKED;
const PROVIDER_CALLS = process.env.GIA_P16D_D2D3_PROVIDER_CALLS;
const PROVIDER_CANCELLED = process.env.GIA_P16D_D2D3_PROVIDER_CANCELLED;
const PRIVATE_SENTINELS = [
  "P16D_D2D3_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
  "P16D_D2D3_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
  "P16D_D2D3_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
];

type Participant = {
  participant_id: string;
  actor_kind: "AI" | "HUMAN" | "SYSTEM";
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
  };
};
type TranscriptItem = {
  sequence: number;
  actor_kind: "AI" | "HUMAN";
  floor_grant_id: string;
  content: string;
};
type ProviderEvidence = {
  generation_request_id: string;
  floor_grant_id: string;
  request_status?: string;
};
type ProviderCall = {
  workload: "candidate";
  generation_request_id: string;
  floor_grant_id: string;
  participant_id: string;
};

test.skip(
  !PROVIDER_BLOCKED || !PROVIDER_CANCELLED || !PROVIDER_CALLS,
  "P1-6D D2-D3 requires its dedicated API/provider/PostgreSQL harness.",
);

test("P1-6D D2-D3 proves durable cancellation and recovery", async ({
  page,
}) => {
  expect(API_LOG).toBeTruthy();
  const publicEvents: string[] = [];
  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    server.onMessage((message) => {
      const raw = message.toString();
      publicEvents.push(raw);
      socket.send(message);
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill(`P16D_D2D3_${Date.now().toString(36)}`);
  await page
    .getByLabel("密码")
    .fill(`P1-6D D2-D3 ${crypto.randomUUID()} phrase`);
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
  const readJsonLines = async <T>(path: string): Promise<T[]> => {
    try {
      return (await readFile(path, "utf8"))
        .split(/\r?\n/u)
        .filter(Boolean)
        .map((line) => JSON.parse(line) as T);
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
  const readAcceptedConnectionIds = async (): Promise<Set<string>> =>
    new Set(
      (await readApiLogRecords()).flatMap((record) =>
        record.event === "realtime.connection.accepted" &&
        record.session_id === sessionId &&
        typeof record.connection_id === "string"
          ? [record.connection_id]
          : [],
      ),
    );
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
  const waitForEvidence = async <T>(path: string): Promise<T> => {
    let evidence: T | undefined;
    await expect
      .poll(
        async () => {
          try {
            evidence = JSON.parse(await readFile(path, "utf8")) as T;
            return true;
          } catch {
            return false;
          }
        },
        { timeout: 15_000 },
      )
      .toBe(true);
    return evidence!;
  };

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
  const humanParticipantId = humans[0]!.participant_id;

  await expect(page.getByText("连接正常").first()).toBeVisible();
  await page.getByRole("button", { name: "开始讨论" }).click();
  await expect
    .poll(
      async () => (await fetchSnapshot()).floor.current_grant?.participant_id,
      {
        timeout: 15_000,
      },
    )
    .toBe(humanParticipantId);

  const humanGrant = (await fetchSnapshot()).floor.current_grant;
  expect(humanGrant).not.toBeNull();
  const humanPrefix = `P16D_D2D3_HUMAN_PUBLIC:${humanGrant!.grant_id}:`;
  await page
    .getByLabel("发言草稿")
    .fill(humanPrefix + "H".repeat(Math.max(1, 1_200 - humanPrefix.length)));
  await page.getByRole("button", { name: "发送发言" }).click();

  const blocked = await waitForEvidence<ProviderEvidence>(PROVIDER_BLOCKED!);
  expect(blocked.request_status).toBe("RUNNING");
  const snapshotBeforeCancellation = await fetchSnapshot();
  const transcriptBeforeCancellation = await fetchTranscript();
  const acceptedBeforeCancellation = await readAcceptedConnectionIds();
  const reconnectAccepted = waitForNewAcceptedConnection(
    acceptedBeforeCancellation,
  );

  await page.reload();

  const cancelled = await waitForEvidence<ProviderEvidence>(
    PROVIDER_CANCELLED!,
  );
  expect(cancelled).toMatchObject({
    generation_request_id: blocked.generation_request_id,
    floor_grant_id: blocked.floor_grant_id,
  });
  const recoveryConnectionId = await reconnectAccepted;
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await expect
    .poll(
      () =>
        publicEvents.filter((raw) => {
          const event = JSON.parse(raw) as {
            type?: string;
            payload?: { grant_id?: string; reason_code?: string };
          };
          return (
            event.type === "floor.released" &&
            event.payload?.grant_id === blocked.floor_grant_id &&
            event.payload.reason_code === "INTERRUPTED"
          );
        }).length,
      { timeout: 15_000 },
    )
    .toBe(1);
  await waitForApiLogRecord(
    (record) =>
      record.event === "realtime.progression.stopped" &&
      record.session_id === sessionId &&
      record.connection_id === recoveryConnectionId,
  );

  const snapshotAfterRecovery = await fetchSnapshot();
  const transcriptAfterRecovery = await fetchTranscript();
  expect(snapshotAfterRecovery.id).toBe(sessionId);
  expect(snapshotAfterRecovery.last_sequence).toBeGreaterThanOrEqual(
    snapshotBeforeCancellation.last_sequence,
  );
  expect(
    transcriptBeforeCancellation.every(
      (item, index) =>
        JSON.stringify(item) === JSON.stringify(transcriptAfterRecovery[index]),
    ),
  ).toBe(true);
  expect(
    transcriptAfterRecovery.filter(
      (item) => item.floor_grant_id === blocked.floor_grant_id,
    ),
  ).toHaveLength(0);

  const acceptedBeforeReplay = await readAcceptedConnectionIds();
  const replayAccepted = waitForNewAcceptedConnection(acceptedBeforeReplay);
  await page.reload();
  const replayConnectionId = await replayAccepted;
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await waitForApiLogRecord(
    (record) =>
      record.event === "realtime.progression.stopped" &&
      record.session_id === sessionId &&
      record.connection_id === replayConnectionId,
  );

  const [finalSnapshot, finalTranscript, providerCalls] = await Promise.all([
    fetchSnapshot(),
    fetchTranscript(),
    readJsonLines<ProviderCall>(PROVIDER_CALLS!),
  ]);
  expect(finalSnapshot.id).toBe(sessionId);
  expect(finalSnapshot.status).not.toBe("PREPARATION");
  expect(finalSnapshot.status).not.toBe("COMPLETED");
  expect(finalSnapshot.last_sequence).toBeGreaterThanOrEqual(
    snapshotAfterRecovery.last_sequence,
  );
  expect(
    providerCalls.filter(
      (call) => call.floor_grant_id === blocked.floor_grant_id,
    ),
  ).toHaveLength(1);
  expect(
    finalTranscript.filter(
      (item) => item.floor_grant_id === blocked.floor_grant_id,
    ),
  ).toHaveLength(0);
  expect(new Set(finalTranscript.map((item) => item.floor_grant_id)).size).toBe(
    finalTranscript.length,
  );

  const publicEvidence = JSON.stringify(publicEvents);
  const transcriptEvidence = JSON.stringify(finalTranscript);
  const cancellationEvidence = JSON.stringify(cancelled);
  const browserText = await page.locator("body").innerText();
  for (const sentinel of PRIVATE_SENTINELS) {
    expect(publicEvidence).not.toContain(sentinel);
    expect(transcriptEvidence).not.toContain(sentinel);
    expect(cancellationEvidence).not.toContain(sentinel);
    expect(browserText).not.toContain(sentinel);
  }
});
