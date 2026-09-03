import { expect, test } from "@playwright/test";
import { readFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_P16D_API_ORIGIN ?? "http://localhost:8000";
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
  participant_id?: string;
  floor_grant_id?: string;
  prompt_version_id?: string;
  prompt_version_number?: number;
  prompt_key?: string;
  private_sentinel_index?: number;
  request_metadata?: { schema_version: number; memory_revision: number };
};

test.skip(
  !PROVIDER_CALLS,
  "P1-6D D2-D1 requires its dedicated API/provider/PostgreSQL harness.",
);

test("P1-6D D2-D1 proves the Human plus three-AI memory happy path", async ({
  page,
}) => {
  expect(PROVIDER_CALLS).toBeTruthy();
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

  let submittedHumanGrant: string | null = null;
  await expect
    .poll(
      async () => {
        const snapshot = await fetchSnapshot();
        const grant = snapshot.floor.current_grant;
        if (
          submittedHumanGrant === null &&
          grant?.participant_id === humans[0]?.participant_id
        ) {
          submittedHumanGrant = grant.grant_id;
          const prefix = `P16D_HUMAN_PUBLIC:${grant.phase}:${grant.grant_id}:`;
          await page
            .getByLabel("发言草稿")
            .fill(prefix + "H".repeat(Math.max(1, 2_560 - prefix.length)));
          await page.getByRole("button", { name: "发送发言" }).click();
        }
        const [transcript, calls] = await Promise.all([
          fetchTranscript(),
          readProviderCalls(),
        ]);
        const successfulAiIds = new Set(
          transcript
            .filter((item) => item.actor_kind === "AI")
            .map((item) => item.participant_id),
        );
        const memoryBackedCalls = calls.filter(
          (call) =>
            call.workload === "candidate" &&
            call.prompt_version_id === "56000000-0000-4000-8000-000000000003" &&
            call.prompt_version_number === 3 &&
            call.prompt_key === "AI_CANDIDATE_TURN" &&
            call.request_metadata?.schema_version === 2 &&
            (call.request_metadata.memory_revision ?? 0) > 0,
        );
        return {
          allThreeAi: ais.every((participant) =>
            successfulAiIds.has(participant.participant_id),
          ),
          humanSpoke: submittedHumanGrant !== null,
          semanticInvoke: calls.some((call) => call.workload === "semantic"),
          completedMemoryBackedCall: memoryBackedCalls.some((call) =>
            transcript.some(
              (item) =>
                item.actor_kind === "AI" &&
                item.floor_grant_id === call.floor_grant_id,
            ),
          ),
          waitingForHumanInExploration:
            snapshot.status === "EXPLORATION" &&
            snapshot.floor.current_grant?.participant_id ===
              humans[0]?.participant_id,
        };
      },
      { timeout: 30_000 },
    )
    .toEqual({
      allThreeAi: true,
      humanSpoke: true,
      semanticInvoke: true,
      completedMemoryBackedCall: true,
      waitingForHumanInExploration: true,
    });

  expect(lifecycleEvents).toContain("OPENING_STATEMENTS");
  expect(lifecycleEvents).toContain("EXPLORATION");
  expect(lifecycleEvents.indexOf("OPENING_STATEMENTS")).toBeLessThan(
    lifecycleEvents.indexOf("EXPLORATION"),
  );
  const publicEvidence = JSON.stringify(await fetchTranscript());
  const browserText = await page.locator("body").innerText();
  for (const sentinel of PRIVATE_SENTINELS) {
    expect(publicEvidence).not.toContain(sentinel);
    expect(browserText).not.toContain(sentinel);
  }
});
