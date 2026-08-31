import { expect, test } from "@playwright/test";
import { access, readFile, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_P16D_API_ORIGIN ?? "http://localhost:8000";
const API_LOG = process.env.GIA_P16D_API_LOG;
const API_RESTART_REQUEST = process.env.GIA_P16D_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_P16D_API_RESTART_READY;
const PRE_RESTART_ARM = process.env.GIA_P16D_PRE_RESTART_ARM;
const PRE_RESTART_QUIESCENT = process.env.GIA_P16D_PRE_RESTART_QUIESCENT;
const CANCELLATION_ARM = process.env.GIA_P16D_CANCELLATION_ARM;
const POST_RESTART_SUCCESS = process.env.GIA_P16D_POST_RESTART_SUCCESS;
const PROVIDER_RUNNING = process.env.GIA_P16D_PROVIDER_RUNNING;
const PROVIDER_CANCELLED = process.env.GIA_P16D_PROVIDER_CANCELLED;
const CANCELLATION_RELOAD = process.env.GIA_P16D_CANCELLATION_RELOAD;
const PROVIDER_CALLS = process.env.GIA_P16D_PROVIDER_CALLS;
const PRIVATE_SENTINELS = [
  "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
];

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
  occurred_at: number;
  participant_id?: string;
  floor_grant_id?: string;
  prompt_version_id?: string;
  prompt_version_number?: number;
  prompt_key?: string;
  private_sentinel_index?: number;
  request_metadata?: {
    schema_version: number;
    context_mode: string;
    memory_revision: number;
    memory_source_through_sequence: number;
    context_source_through_sequence: number;
  };
};

const lifecycleOrder = [
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
  "COMPLETED",
];

test.setTimeout(240_000);

test("P1-6D completes Human plus three AI with memory, restart and cancellation recovery", async ({
  page,
}) => {
  for (const requiredPath of [
    API_LOG,
    API_RESTART_REQUEST,
    API_RESTART_READY,
    PRE_RESTART_ARM,
    PRE_RESTART_QUIESCENT,
    CANCELLATION_ARM,
    POST_RESTART_SUCCESS,
    PROVIDER_RUNNING,
    PROVIDER_CANCELLED,
    CANCELLATION_RELOAD,
    PROVIDER_CALLS,
  ]) {
    expect(requiredPath).toBeTruthy();
  }

  const lifecycleEvents: string[] = [];
  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    server.onMessage((message) => {
      const raw = message.toString();
      try {
        const event = JSON.parse(raw) as {
          type?: string;
          payload?: { status?: string };
        };
        if (
          event.type === "session.state_changed" &&
          typeof event.payload?.status === "string"
        ) {
          lifecycleEvents.push(event.payload.status);
        }
      } finally {
        socket.send(message);
      }
    });
  });

  const username = `P16D_${Date.now().toString(36)}`;
  const password = `P1-6D browser ${crypto.randomUUID()} phrase`;
  await page.goto("/");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
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
  const created = (await createResponse.json()) as SessionSnapshot;
  const sessionId = created.id;
  const countAcceptedSessionConnections = async () => {
    try {
      return (await readFile(API_LOG!, "utf8"))
        .split(/\r?\n/u)
        .filter(Boolean)
        .reduce((count, line) => {
          try {
            const record = JSON.parse(line) as {
              event?: string;
              session_id?: string;
            };
            return record.event === "realtime.connection.accepted" &&
              record.session_id === sessionId
              ? count + 1
              : count;
          } catch {
            return count;
          }
        }, 0);
    } catch {
      return 0;
    }
  };

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
        const body = (await response.json()) as { items: TranscriptItem[] };
        return body.items;
      },
      { apiBaseUrl: API_BASE_URL, session: sessionId },
    );
  const readProviderCalls = async () => {
    try {
      return (await readFile(PROVIDER_CALLS!, "utf8"))
        .split(/\r?\n/u)
        .filter(Boolean)
        .map((line) => JSON.parse(line) as ProviderCall);
    } catch {
      return [];
    }
  };
  const submittedHumanGrants = new Set<string>();
  const driveHumanTurn = async (snapshot: SessionSnapshot) => {
    const human = snapshot.floor.participants.find(
      (participant) => participant.actor_kind === "HUMAN",
    );
    const grant = snapshot.floor.current_grant;
    if (
      !human ||
      !grant ||
      grant.participant_id !== human.participant_id ||
      submittedHumanGrants.has(grant.grant_id)
    ) {
      return;
    }
    submittedHumanGrants.add(grant.grant_id);
    const prefix = `P16D_HUMAN_PUBLIC:${grant.phase}:${grant.grant_id}:`;
    const contribution =
      prefix + "H".repeat(Math.max(1, 2_560 - prefix.length));
    await page.getByLabel("发言草稿").fill(contribution);
    await page.getByRole("button", { name: "发送发言" }).click();
  };
  const fileExists = async (path: string) => {
    try {
      await access(path);
      return true;
    } catch {
      return false;
    }
  };

  const initialSnapshot = await fetchSnapshot();
  const candidates = initialSnapshot.floor.participants.filter(
    (participant) => participant.actor_kind !== "SYSTEM",
  );
  const humanParticipants = candidates.filter(
    (participant) => participant.actor_kind === "HUMAN",
  );
  const aiParticipants = candidates.filter(
    (participant) => participant.actor_kind === "AI",
  );
  expect(candidates).toHaveLength(4);
  expect(humanParticipants).toHaveLength(1);
  expect(aiParticipants).toHaveLength(3);
  expect(
    new Set(aiParticipants.map((participant) => participant.participant_id))
      .size,
  ).toBe(3);
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await page.getByRole("button", { name: "开始讨论" }).click();

  await expect
    .poll(
      async () => {
        const snapshot = await fetchSnapshot();
        await driveHumanTurn(snapshot);
        const [transcript, calls] = await Promise.all([
          fetchTranscript(),
          readProviderCalls(),
        ]);
        const successfulAiIds = new Set(
          transcript
            .filter((item) => item.actor_kind === "AI")
            .map((item) => item.participant_id),
        );
        const memoryBacked = calls.some(
          (call) =>
            call.workload === "candidate" &&
            call.prompt_version_id === "56000000-0000-4000-8000-000000000003" &&
            call.prompt_version_number === 3 &&
            call.prompt_key === "AI_CANDIDATE_TURN" &&
            call.request_metadata?.schema_version === 2 &&
            (call.request_metadata?.memory_revision ?? 0) > 0,
        );
        return {
          allThreeAi: aiParticipants.every((participant) =>
            successfulAiIds.has(participant.participant_id),
          ),
          semanticInvoke: calls.some((call) => call.workload === "semantic"),
          memoryBacked,
          activeHuman: submittedHumanGrants.size > 0,
        };
      },
      { timeout: 30_000, intervals: [100, 200, 500] },
    )
    .toEqual({
      allThreeAi: true,
      semanticInvoke: true,
      memoryBacked: true,
      activeHuman: true,
    });

  const beforeReload = await fetchTranscript();
  await writeFile(
    PRE_RESTART_ARM!,
    JSON.stringify({ occurred_at: Date.now() / 1_000 }),
    "utf8",
  );
  const restartTriggerPage = await page.context().newPage();
  await restartTriggerPage.goto(page.url());
  await expect
    .poll(() => fileExists(PRE_RESTART_QUIESCENT!), { timeout: 20_000 })
    .toBe(true);
  await page.reload();
  await expect(page.getByText("连接正常").first()).toBeVisible();
  await expect
    .poll(async () => (await fetchTranscript()).length)
    .toBeGreaterThanOrEqual(beforeReload.length);
  await restartTriggerPage.close();

  const acceptedBeforeRestart = await countAcceptedSessionConnections();
  expect(acceptedBeforeRestart).toBeGreaterThan(0);

  await writeFile(API_RESTART_REQUEST!, "restart", "utf8");
  await expect
    .poll(() => fileExists(API_RESTART_READY!), { timeout: 20_000 })
    .toBe(true);
  await expect
    .poll(countAcceptedSessionConnections, { timeout: 20_000 })
    .toBeGreaterThan(acceptedBeforeRestart);
  await expect(page.getByText("连接正常").first()).toBeVisible({
    timeout: 20_000,
  });
  await expect
    .poll(
      async () => {
        const snapshot = await fetchSnapshot();
        await driveHumanTurn(snapshot);
        return fileExists(POST_RESTART_SUCCESS!);
      },
      { timeout: 60_000, intervals: [100, 200, 500] },
    )
    .toBe(true);

  await writeFile(
    CANCELLATION_ARM!,
    JSON.stringify({ occurred_at: Date.now() / 1_000 }),
    "utf8",
  );
  await expect
    .poll(
      async () => {
        const snapshot = await fetchSnapshot();
        await driveHumanTurn(snapshot);
        return fileExists(PROVIDER_RUNNING!);
      },
      { timeout: 35_000, intervals: [100, 200, 500] },
    )
    .toBe(true);
  await writeFile(
    CANCELLATION_RELOAD!,
    JSON.stringify({ occurred_at: Date.now() / 1_000 }),
    "utf8",
  );
  await page.reload();
  await expect
    .poll(() => fileExists(PROVIDER_CANCELLED!), { timeout: 20_000 })
    .toBe(true);
  await expect(page.getByText("连接正常").first()).toBeVisible({
    timeout: 20_000,
  });

  await expect
    .poll(
      async () => {
        const snapshot = await fetchSnapshot();
        await driveHumanTurn(snapshot);
        return snapshot.status;
      },
      { timeout: 110_000, intervals: [100, 200, 500] },
    )
    .toBe("COMPLETED");
  await expect(page.getByText("已完成", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByText("讨论已完成", { exact: true }).first(),
  ).toBeVisible();

  const finalSnapshot = await fetchSnapshot();
  const finalTranscript = await fetchTranscript();
  expect(finalSnapshot.status).toBe("COMPLETED");
  expect(finalSnapshot.floor.current_grant).toBeNull();
  expect(finalTranscript.some((item) => item.actor_kind === "HUMAN")).toBe(
    true,
  );
  expect(
    aiParticipants.every((participant) =>
      finalTranscript.some(
        (item) =>
          item.actor_kind === "AI" &&
          item.participant_id === participant.participant_id,
      ),
    ),
  ).toBe(true);
  const publicEvidence = JSON.stringify({ finalSnapshot, finalTranscript });
  const body = (await page.locator("body").textContent()) ?? "";
  for (const sentinel of PRIVATE_SENTINELS) {
    expect(publicEvidence).not.toContain(sentinel);
    expect(body).not.toContain(sentinel);
  }

  const completedLifecycle = lifecycleEvents.filter(
    (status, index, statuses) => statuses.indexOf(status) === index,
  );
  expect(completedLifecycle).toEqual(lifecycleOrder);
});
