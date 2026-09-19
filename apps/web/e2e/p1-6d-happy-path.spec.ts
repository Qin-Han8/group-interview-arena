import { expect, test } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_P16D_API_ORIGIN ?? "http://localhost:8000";
const API_LOG = process.env.GIA_P16D_API_LOG;
const API_RESTART_READY = process.env.GIA_P16D_API_RESTART_READY;
const API_RESTART_REQUEST = process.env.GIA_P16D_API_RESTART_REQUEST;
const PROVIDER_CALLS = process.env.GIA_P16D_PROVIDER_CALLS;
const INTERNAL_VALIDATION_QUESTION_VERSION_ID =
  "21000000-0000-4000-8000-000000000001";
const QUESTION_TYPE_LABELS = {
  ORDERING_SELECTION: "排序选择型",
  RESOURCE_ALLOCATION: "资源分配型",
  PLAN_DESIGN: "方案策划型",
} as const;

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

test("P1-6D D2-D2B proves Browser reload and API restart recovery", async ({
  page,
}) => {
  expect(API_LOG).toBeTruthy();
  expect(API_RESTART_READY).toBeTruthy();
  expect(API_RESTART_REQUEST).toBeTruthy();
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
  await expect(
    page.getByRole("heading", { name: "下一场完整模拟" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "开始选题" }).click();
  await expect(
    page.getByRole("heading", { name: "选择本次训练题目" }),
  ).toBeVisible();

  const discovery = await page.evaluate(async (apiBaseUrl) => {
    const response = await fetch(`${apiBaseUrl}/questions`, {
      credentials: "include",
    });
    return { status: response.status, body: await response.json() };
  }, API_BASE_URL);
  expect(discovery.status).toBe(200);
  const targetQuestion = discovery.body.find(
    (item: { id: string; question_type: string; title: string }) =>
      item.id === INTERNAL_VALIDATION_QUESTION_VERSION_ID,
  ) as
    | {
        id: string;
        question_type: keyof typeof QUESTION_TYPE_LABELS;
        title: string;
      }
    | undefined;
  expect(targetQuestion).toBeDefined();
  expect(QUESTION_TYPE_LABELS[targetQuestion!.question_type]).toBeDefined();
  await page
    .getByRole("tab", {
      name: new RegExp(
        `^${QUESTION_TYPE_LABELS[targetQuestion!.question_type]}`,
      ),
    })
    .click();
  const targetQuestionCard = page.getByRole("radio", {
    name: targetQuestion!.title,
  });
  await targetQuestionCard.focus();
  await targetQuestionCard.press("Space");
  await expect(targetQuestionCard).toBeChecked();

  const createResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === `${API_BASE_URL}/sessions` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "创建文字会话" }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status()).toBe(201);
  expect(createResponse.request().postDataJSON()).toEqual({
    question_version_id: targetQuestion!.id,
  });
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
  const waitForEvidenceFile = async (path: string): Promise<void> => {
    await expect
      .poll(
        async () => {
          try {
            await readFile(path, "utf8");
            return true;
          } catch {
            return false;
          }
        },
        { timeout: 15_000 },
      )
      .toBe(true);
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
        noPublicDeadlineIntervention:
          snapshot.floor.latest_event?.type !== "floor.intervention_requested",
      };
    })
    .toEqual({
      active: true,
      durableSequenceAdvanced: true,
      noPublicDeadlineIntervention: true,
    });

  await expect
    .poll(async () => (await fetchSnapshot()).floor.current_grant !== null, {
      timeout: 15_000,
    })
    .toBe(true);

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
  expect(continuationBoundary.floor.current_grant).not.toBeNull();
  expect(continuationBoundary.floor.latest_event?.type).not.toBe(
    "floor.intervention_requested",
  );
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
      record.exception_category === "progression_no_work",
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

  const humanParticipantId = humans[0]!.participant_id;
  const submitHumanTurn = async (
    snapshot: SessionSnapshot,
    evidenceLabel: string,
  ): Promise<string> => {
    const grant = snapshot.floor.current_grant;
    expect(grant?.participant_id).toBe(humanParticipantId);
    expect(grant).not.toBeNull();
    const prefix = `${evidenceLabel}:${grant!.phase}:${grant!.grant_id}:`;
    await page
      .getByLabel("发言草稿")
      .fill(prefix + "H".repeat(Math.max(1, 1_200 - prefix.length)));
    await page.getByRole("button", { name: "发送发言" }).click();
    return grant!.grant_id;
  };

  await submitHumanTurn(snapshotAfterReload, "P16D_D2D2B_PRE_RESTART");
  await expect
    .poll(async () => {
      const [snapshot, transcript, calls] = await Promise.all([
        fetchSnapshot(),
        fetchTranscript(),
        readProviderCalls(),
      ]);
      const completedAiGrants = new Set(
        calls
          .filter(
            (call) =>
              call.workload === "candidate" &&
              transcript.some(
                (item) =>
                  item.actor_kind === "AI" &&
                  item.floor_grant_id === call.floor_grant_id,
              ),
          )
          .map((call) => call.floor_grant_id),
      );
      return {
        completedAi: completedAiGrants.size > 0,
        stableHumanBoundary:
          snapshot.floor.current_grant?.participant_id === humanParticipantId,
      };
    })
    .toEqual({ completedAi: true, stableHumanBoundary: true });

  const beforeRestartSnapshot = await fetchSnapshot();
  const beforeRestartTranscript = await fetchTranscript();
  const beforeRestartCalls = await readProviderCalls();
  const completedAiGrantsBeforeRestart = new Set(
    beforeRestartCalls
      .filter(
        (call) =>
          call.workload === "candidate" &&
          beforeRestartTranscript.some(
            (item) =>
              item.actor_kind === "AI" &&
              item.floor_grant_id === call.floor_grant_id,
          ),
      )
      .map((call) => call.floor_grant_id),
  );
  expect(completedAiGrantsBeforeRestart.size).toBeGreaterThan(0);
  const acceptedBeforeRestart = await readAcceptedConnectionIds();
  await writeFile(
    API_RESTART_REQUEST!,
    JSON.stringify({
      session_id: sessionId,
      last_sequence: beforeRestartSnapshot.last_sequence,
    }),
    "utf8",
  );
  await waitForEvidenceFile(API_RESTART_READY!);
  const restartedConnectionId = await waitForNewAcceptedConnection(
    acceptedBeforeRestart,
  );
  expect(restartedConnectionId).toBeTruthy();
  await expect(page.getByText("连接正常").first()).toBeVisible();

  const [snapshotAfterRestart, transcriptAfterRestart, callsAfterRestart] =
    await Promise.all([
      fetchSnapshot(),
      fetchTranscript(),
      readProviderCalls(),
    ]);
  expect(snapshotAfterRestart.id).toBe(sessionId);
  expect(new URL(page.url()).searchParams.get("session_id")).toBe(sessionId);
  expect(snapshotAfterRestart.last_sequence).toBeGreaterThanOrEqual(
    beforeRestartSnapshot.last_sequence,
  );
  expect(
    beforeRestartTranscript.every(
      (item, index) =>
        JSON.stringify(item) === JSON.stringify(transcriptAfterRestart[index]),
    ),
  ).toBe(true);
  expect(
    [...completedAiGrantsBeforeRestart].every(
      (grantId) =>
        callsAfterRestart.filter(
          (call) =>
            call.workload === "candidate" && call.floor_grant_id === grantId,
        ).length === 1,
    ),
  ).toBe(true);
  expect(
    new Set(transcriptAfterRestart.map((item) => item.floor_grant_id)).size,
  ).toBe(transcriptAfterRestart.length);

  const progressionStopsBeforeContinuation = (await readApiLogRecords()).filter(
    (record) =>
      record.event === "realtime.progression.stopped" &&
      record.session_id === sessionId &&
      record.connection_id === restartedConnectionId,
  ).length;
  const postRestartHumanGrant = await submitHumanTurn(
    snapshotAfterRestart,
    "P16D_D2D2B_POST_RESTART",
  );
  await expect
    .poll(async () => {
      const [snapshot, transcript, records] = await Promise.all([
        fetchSnapshot(),
        fetchTranscript(),
        readApiLogRecords(),
      ]);
      return {
        durableSequenceAdvanced:
          snapshot.last_sequence > snapshotAfterRestart.last_sequence,
        humanTurnDurable: transcript.some(
          (item) => item.floor_grant_id === postRestartHumanGrant,
        ),
        progressionContinued:
          records.filter(
            (record) =>
              record.event === "realtime.progression.stopped" &&
              record.session_id === sessionId &&
              record.connection_id === restartedConnectionId,
          ).length > progressionStopsBeforeContinuation,
      };
    })
    .toEqual({
      durableSequenceAdvanced: true,
      humanTurnDurable: true,
      progressionContinued: true,
    });
});
