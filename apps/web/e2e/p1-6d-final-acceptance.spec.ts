import { expect, test } from "@playwright/test";
import { access, readFile, writeFile } from "node:fs/promises";

const API_BASE_URL =
  process.env.GIA_P16D_FINAL_API_ORIGIN ?? "http://localhost:8000";
const OWNER_INVITE_CODE = process.env.GIA_P16D_FINAL_INVITE_CODE;
const OTHER_INVITE_CODE = process.env.GIA_P17E_OTHER_INVITE_CODE;
const API_LOG = process.env.GIA_P16D_FINAL_API_LOG;
const API_RESTART_REQUEST = process.env.GIA_P16D_FINAL_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_P16D_FINAL_API_RESTART_READY;
const PROVIDER_CALLS = process.env.GIA_P16D_FINAL_PROVIDER_CALLS;
const CANCELLATION_ARM = process.env.GIA_P16D_FINAL_CANCELLATION_ARM;
const PROVIDER_BLOCKED = process.env.GIA_P16D_FINAL_PROVIDER_BLOCKED;
const PROVIDER_CANCELLED = process.env.GIA_P16D_FINAL_PROVIDER_CANCELLED;
const P17E_FINAL_COMPOSITION = process.env.GIA_P17E_FINAL_COMPOSITION === "1";
const REPORT_API_RESTART_REQUEST =
  process.env.GIA_P17E_REPORT_API_RESTART_REQUEST;
const REPORT_API_RESTART_READY = process.env.GIA_P17E_REPORT_API_RESTART_READY;
const INTERNAL_VALIDATION_QUESTION_VERSION_ID =
  "21000000-0000-4000-8000-000000000001";
const QUESTION_TYPE_LABELS = {
  ORDERING_SELECTION: "排序选择型",
  RESOURCE_ALLOCATION: "资源分配型",
  PLAN_DESIGN: "方案策划型",
} as const;
const PRIVATE_SENTINELS = [
  "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
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
    latest_event?: { type?: string } | null;
  };
};
type TranscriptItem = {
  utterance_id: string;
  sequence: number;
  participant_id: string;
  actor_kind: "AI" | "HUMAN";
  floor_grant_id: string;
  phase: string;
  content: string;
};
type ReportEvidence = {
  kind: "STRENGTH" | "IMPROVEMENT";
  source_participant_id: string;
  source_utterance_id: string;
  source_event_sequence: number;
  phase: string;
  quote: string;
  interpretation: string;
  confidence: string | number;
};
type ReportView = {
  report: {
    report_id: string;
    session_id: string;
    status: string;
    report_schema_version: number;
    derivation_version: string;
    source_through_sequence: number;
    created_at: string;
    completed_at: string | null;
  };
  content: {
    overview: {
      session_status: string;
      question: { id: string };
      participant_count: number;
      human_utterance_count: number;
      ai_utterance_count: number;
      total_utterance_count: number;
      covered_phases: string[];
      summary: string;
    };
    strengths: ReportEvidence[];
    improvements: ReportEvidence[];
    priority_improvement: string;
  } | null;
};
type ProviderCall = {
  workload: "candidate" | "semantic";
  participant_id?: string;
  floor_grant_id?: string;
  prompt_version_id?: string;
  prompt_version_number?: number;
  prompt_key?: string;
  request_metadata?: {
    schema_version?: number;
    memory_revision?: number;
  };
};
type ProviderEvidence = {
  generation_request_id: string;
  floor_grant_id: string;
  request_status: "RUNNING";
};

test.skip(
  !API_LOG ||
    !API_RESTART_REQUEST ||
    !API_RESTART_READY ||
    !PROVIDER_CALLS ||
    !CANCELLATION_ARM ||
    !PROVIDER_BLOCKED ||
    !PROVIDER_CANCELLED ||
    (P17E_FINAL_COMPOSITION &&
      (!REPORT_API_RESTART_REQUEST || !REPORT_API_RESTART_READY)),
  "P1-6D D2-D4 requires its dedicated API/provider/PostgreSQL harness.",
);

test.describe.serial("P1-6D final integrated acceptance", () => {
  let finishLifecycle: (() => Promise<void>) | undefined;
  let closeBrowserContext: (() => Promise<void>) | undefined;

  test.afterAll(async () => {
    await closeBrowserContext?.();
  });

  test("composes happy path, reload, restart, and cancellation", async ({
    browser,
  }) => {
    const context = await browser.newContext();
    closeBrowserContext = () => context.close();
    const page = await context.newPage();
    const publicEvents: string[] = [];
    await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
      const server = socket.connectToServer();
      socket.onMessage((message) => server.send(message));
      server.onMessage((message) => {
        publicEvents.push(message.toString());
        socket.send(message);
      });
    });

    await page.goto("/");
    await page.getByRole("button", { name: "注册" }).click();
    await page
      .getByLabel("用户名")
      .fill(`P16D_FINAL_${Date.now().toString(36)}`);
    await page
      .getByLabel("密码")
      .fill(`P1-6D final ${crypto.randomUUID()} phrase`);
    expect(OWNER_INVITE_CODE).toBeTruthy();
    await page.getByLabel("邀请码").fill(OWNER_INVITE_CODE ?? "");
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

    if (P17E_FINAL_COMPOSITION) {
      const activeReportAttempt = await page.evaluate(
        async ({ apiBaseUrl, session }) => {
          const response = await fetch(
            `${apiBaseUrl}/sessions/${session}/report`,
            {
              method: "POST",
              credentials: "include",
              headers: { "X-GIA-CSRF": "1" },
            },
          );
          return { status: response.status, body: await response.json() };
        },
        { apiBaseUrl: API_BASE_URL, session: sessionId },
      );
      expect(activeReportAttempt.status).toBe(409);
      expect(activeReportAttempt.body).toMatchObject({
        error: { code: "INVALID_SESSION_STATE" },
      });
    }

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
    const readJsonLines = async <T>(path: string): Promise<T[]> =>
      (await readFile(path, "utf8"))
        .split(/\r?\n/u)
        .filter(Boolean)
        .flatMap((line) => {
          try {
            return [JSON.parse(line) as T];
          } catch {
            return [];
          }
        });
    const readApiLogRecords = (): Promise<Record<string, unknown>[]> =>
      readJsonLines<Record<string, unknown>>(API_LOG!);
    const readProviderCalls = async (): Promise<ProviderCall[]> => {
      try {
        return await readJsonLines<ProviderCall>(PROVIDER_CALLS!);
      } catch {
        return [];
      }
    };
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
    const waitForNewAcceptedConnection = async (
      knownConnectionIds: ReadonlySet<string>,
    ): Promise<string> => {
      let acceptedConnectionId: string | undefined;
      await expect
        .poll(
          async () => {
            const accepted = await readAcceptedConnectionIds();
            acceptedConnectionId = [...accepted].find(
              (connectionId) => !knownConnectionIds.has(connectionId),
            );
            return acceptedConnectionId !== undefined;
          },
          { timeout: 15_000 },
        )
        .toBe(true);
      return acceptedConnectionId!;
    };
    const waitForFile = async <T>(path: string): Promise<T> => {
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
    const fileExists = async (path: string): Promise<boolean> => {
      try {
        await access(path);
        return true;
      } catch {
        return false;
      }
    };

    const initial = await fetchSnapshot();
    const candidates = initial.floor.participants.filter(
      (participant) => participant.actor_kind !== "SYSTEM",
    );
    const human = candidates.find(
      (participant) => participant.actor_kind === "HUMAN",
    );
    const ais = candidates.filter(
      (participant) => participant.actor_kind === "AI",
    );
    expect(candidates).toHaveLength(4);
    expect(human).toBeDefined();
    expect(ais).toHaveLength(3);
    expect(
      new Set(ais.map((participant) => participant.participant_id)).size,
    ).toBe(3);

    const submittedHumanGrants = new Set<string>();
    const driveHumanTurn = async (snapshot: SessionSnapshot): Promise<void> => {
      const grant = snapshot.floor.current_grant;
      if (
        !grant ||
        grant.participant_id !== human!.participant_id ||
        submittedHumanGrants.has(grant.grant_id)
      ) {
        return;
      }
      submittedHumanGrants.add(grant.grant_id);
      const prefix = `P16D_FINAL_HUMAN_PUBLIC:${grant.phase}:${grant.grant_id}:`;
      await page
        .getByLabel("发言草稿")
        .fill(prefix + "H".repeat(Math.max(1, 1_200 - prefix.length)));
      await page.getByRole("button", { name: "发送发言" }).click();
    };

    await expect(page.getByText("连接正常").first()).toBeVisible();
    await page.getByRole("button", { name: "开始讨论" }).click();
    await expect
      .poll(async () => {
        const snapshot = await fetchSnapshot();
        return (
          snapshot.floor.current_grant !== null ||
          snapshot.floor.latest_event?.type === "floor.intervention_requested"
        );
      })
      .toBe(true);
    const beforeReloadSnapshot = await fetchSnapshot();
    const beforeReloadTranscript = await fetchTranscript();
    const acceptedBeforeBootstrap = await readAcceptedConnectionIds();
    const bootstrapAccepted = waitForNewAcceptedConnection(
      acceptedBeforeBootstrap,
    );
    await page.reload();
    await bootstrapAccepted;
    await expect(page.getByText("连接正常").first()).toBeVisible();
    const afterReloadSnapshot = await fetchSnapshot();
    const afterReloadTranscript = await fetchTranscript();
    expect(afterReloadSnapshot.id).toBe(sessionId);
    expect(afterReloadSnapshot.last_sequence).toBeGreaterThanOrEqual(
      beforeReloadSnapshot.last_sequence,
    );
    expect(
      beforeReloadTranscript.every(
        (item, index) =>
          JSON.stringify(item) === JSON.stringify(afterReloadTranscript[index]),
      ),
    ).toBe(true);
    await expect
      .poll(
        async () => (await fetchSnapshot()).floor.current_grant?.participant_id,
        { timeout: 15_000 },
      )
      .toBe(human!.participant_id);
    await expect
      .poll(
        async () => {
          const snapshot = await fetchSnapshot();
          const [transcript, calls] = await Promise.all([
            fetchTranscript(),
            readProviderCalls(),
          ]);
          const spokenAiIds = new Set(
            transcript
              .filter((item) => item.actor_kind === "AI")
              .map((item) => item.participant_id),
          );
          const evidence = {
            human: transcript.some((item) => item.actor_kind === "HUMAN"),
            threeAi: ais.every((participant) =>
              spokenAiIds.has(participant.participant_id),
            ),
            semantic: calls.some((call) => call.workload === "semantic"),
            candidateV4WithMemory: calls.some(
              (call) =>
                call.workload === "candidate" &&
                call.prompt_version_number === 4 &&
                call.prompt_key === "AI_CANDIDATE_TURN" &&
                call.request_metadata?.schema_version === 2 &&
                (call.request_metadata.memory_revision ?? 0) > 0,
            ),
          };
          const happyEvidenceComplete = Object.values(evidence).every(Boolean);
          if (!happyEvidenceComplete) {
            await driveHumanTurn(snapshot);
          }
          return {
            ...evidence,
            stableHumanBoundary:
              happyEvidenceComplete &&
              snapshot.floor.current_grant?.participant_id ===
                human!.participant_id,
          };
        },
        { timeout: 15_000 },
      )
      .toEqual({
        human: true,
        threeAi: true,
        semantic: true,
        candidateV4WithMemory: true,
        stableHumanBoundary: true,
      });

    const beforeRestartSnapshot = await fetchSnapshot();
    const durableHumanGrant = beforeRestartSnapshot.floor.current_grant;
    expect(durableHumanGrant?.participant_id).toBe(human!.participant_id);
    const beforeRestartTranscript = await fetchTranscript();
    const acceptedBeforeRestart = await readAcceptedConnectionIds();
    await writeFile(API_RESTART_REQUEST!, "restart", "utf8");
    await expect
      .poll(() => fileExists(API_RESTART_READY!), { timeout: 15_000 })
      .toBe(true);
    await waitForNewAcceptedConnection(acceptedBeforeRestart);
    await expect(page.getByText("连接正常").first()).toBeVisible();
    let afterRestartSnapshot: SessionSnapshot | undefined;
    await expect
      .poll(
        async () => {
          afterRestartSnapshot = await fetchSnapshot();
          return afterRestartSnapshot.floor.current_grant?.grant_id;
        },
        { timeout: 15_000 },
      )
      .toBe(durableHumanGrant!.grant_id);
    const afterRestartTranscript = await fetchTranscript();
    expect(afterRestartSnapshot!.id).toBe(sessionId);
    expect(afterRestartSnapshot!.floor.current_grant?.participant_id).toBe(
      human!.participant_id,
    );
    expect(afterRestartSnapshot!.last_sequence).toBeGreaterThanOrEqual(
      beforeRestartSnapshot.last_sequence,
    );
    expect(
      beforeRestartTranscript.every(
        (item, index) =>
          JSON.stringify(item) ===
          JSON.stringify(afterRestartTranscript[index]),
      ),
    ).toBe(true);

    await writeFile(CANCELLATION_ARM!, "armed", "utf8");
    await driveHumanTurn(afterRestartSnapshot!);
    await expect
      .poll(() => fileExists(PROVIDER_BLOCKED!), { timeout: 15_000 })
      .toBe(true);
    const blocked = await waitForFile<ProviderEvidence>(PROVIDER_BLOCKED!);
    expect(blocked.request_status).toBe("RUNNING");
    const acceptedBeforeCancellation = await readAcceptedConnectionIds();
    const cancellationReconnect = waitForNewAcceptedConnection(
      acceptedBeforeCancellation,
    );
    await page.reload();
    const cancelled = await waitForFile<ProviderEvidence>(PROVIDER_CANCELLED!);
    expect(cancelled).toEqual(blocked);
    await cancellationReconnect;
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

    finishLifecycle = async () => {
      const continuationSnapshot = await fetchSnapshot();
      await driveHumanTurn(continuationSnapshot);

      await expect
        .poll(
          async () => {
            await fetchSnapshot();
            return publicEvents.some((raw) => {
              const event = JSON.parse(raw) as {
                type?: string;
                payload?: {
                  previous_status?: string;
                  status?: string;
                  trigger?: string;
                };
              };
              return (
                event.type === "session.state_changed" &&
                event.payload?.previous_status === "FINAL_SUMMARY" &&
                event.payload.status === "COMPLETED" &&
                event.payload.trigger === "PHASE_DEADLINE"
              );
            });
          },
          { timeout: test.info().timeout },
        )
        .toBe(true);

      const finalSnapshot = await fetchSnapshot();
      const finalTranscript = await fetchTranscript();
      const providerCalls = await readProviderCalls();
      expect(finalSnapshot.id).toBe(sessionId);
      expect(finalSnapshot.status).toBe("COMPLETED");
      expect(finalSnapshot.floor.current_grant).toBeNull();
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
      expect(
        new Set(finalTranscript.map((item) => item.floor_grant_id)).size,
      ).toBe(finalTranscript.length);
      expect(
        ais.every((participant) =>
          finalTranscript.some(
            (item) =>
              item.actor_kind === "AI" &&
              item.participant_id === participant.participant_id,
          ),
        ),
      ).toBe(true);
      const publicEvidence = JSON.stringify({ publicEvents, finalTranscript });
      const browserText = await page.locator("body").innerText();
      const cancellationEvidence = JSON.stringify(cancelled);
      for (const sentinel of PRIVATE_SENTINELS) {
        expect(publicEvidence).not.toContain(sentinel);
        expect(browserText).not.toContain(sentinel);
        expect(cancellationEvidence).not.toContain(sentinel);
      }
      await expect(
        page.getByText("已完成", { exact: true }).first(),
      ).toBeVisible();

      if (!P17E_FINAL_COMPOSITION) return;

      const fetchReport = () =>
        page.evaluate(
          async ({ apiBaseUrl, session }) => {
            const response = await fetch(
              `${apiBaseUrl}/sessions/${session}/report`,
              { credentials: "include" },
            );
            return {
              status: response.status,
              body: (await response.json()) as ReportView,
            };
          },
          { apiBaseUrl: API_BASE_URL, session: sessionId },
        );
      const beforeGeneration = await fetchReport();
      expect(beforeGeneration.status).toBe(404);

      const generateResponsePromise = page.waitForResponse(
        (response) =>
          response.url() === `${API_BASE_URL}/sessions/${sessionId}/report` &&
          response.request().method() === "POST",
      );
      await page
        .getByRole("button", {
          name: "训练报告 · 生成 / 查看本次训练报告",
        })
        .first()
        .click();
      const generateResponse = await generateResponsePromise;
      expect(generateResponse.status()).toBe(200);
      const generatedReport =
        (await generateResponse.json()) as ReportView["report"];
      expect(generatedReport).toMatchObject({
        session_id: sessionId,
        status: "COMPLETED",
        report_schema_version: 1,
        derivation_version: "basic-report/v1",
        source_through_sequence: finalSnapshot.last_sequence,
      });
      await expect(page).toHaveURL(`/sessions/${sessionId}/report`);
      await expect(page.getByTestId("report-bento")).toBeVisible();
      await expect(page.getByTestId("studio-shell")).toBeVisible();

      const firstRead = await fetchReport();
      expect(firstRead.status).toBe(200);
      expect(firstRead.body.report).toEqual(generatedReport);
      expect(firstRead.body.content).not.toBeNull();
      const reportContent = firstRead.body.content!;
      const humanTranscript = finalTranscript.filter(
        (item) => item.actor_kind === "HUMAN",
      );
      const aiTranscript = finalTranscript.filter(
        (item) => item.actor_kind === "AI",
      );
      expect(reportContent.overview).toMatchObject({
        session_status: "COMPLETED",
        question: { id: targetQuestion!.id },
        participant_count: 4,
        human_utterance_count: humanTranscript.length,
        ai_utterance_count: aiTranscript.length,
        total_utterance_count: finalTranscript.length,
      });
      expect(reportContent.overview.summary).toBe(
        "The report is derived from authoritative public discussion history.",
      );
      const evidence = [
        ...reportContent.strengths,
        ...reportContent.improvements,
      ];
      expect(evidence.length).toBeGreaterThan(0);
      for (const item of evidence) {
        const source = finalTranscript.find(
          (utterance) =>
            utterance.sequence === item.source_event_sequence &&
            utterance.utterance_id === item.source_utterance_id,
        );
        expect(source).toBeDefined();
        expect(item.source_event_sequence).toBeLessThanOrEqual(
          generatedReport.source_through_sequence,
        );
        expect(source).toMatchObject({
          actor_kind: "HUMAN",
          participant_id: item.source_participant_id,
          phase: item.phase,
          content: item.quote,
        });
      }

      const idempotentGeneration = await page.evaluate(
        async ({ apiBaseUrl, session }) => {
          const response = await fetch(
            `${apiBaseUrl}/sessions/${session}/report`,
            {
              method: "POST",
              credentials: "include",
              headers: { "X-GIA-CSRF": "1" },
            },
          );
          return { status: response.status, body: await response.json() };
        },
        { apiBaseUrl: API_BASE_URL, session: sessionId },
      );
      expect(idempotentGeneration.status).toBe(200);
      expect(idempotentGeneration.body).toEqual(generatedReport);

      await page.reload();
      await expect(page.getByTestId("report-bento")).toBeVisible();
      const afterBrowserReload = await fetchReport();
      expect(afterBrowserReload).toEqual(firstRead);

      await writeFile(REPORT_API_RESTART_REQUEST!, "restart", "utf8");
      await expect
        .poll(() => fileExists(REPORT_API_RESTART_READY!), {
          timeout: 15_000,
        })
        .toBe(true);
      await page.reload();
      await expect(page.getByTestId("report-bento")).toBeVisible();
      const afterApiRestart = await fetchReport();
      expect(afterApiRestart).toEqual(firstRead);

      const otherContext = await browser.newContext();
      try {
        const otherPage = await otherContext.newPage();
        await otherPage.goto("/");
        await otherPage.getByRole("button", { name: "注册" }).click();
        await otherPage
          .getByLabel("用户名")
          .fill(`P17E_OTHER_${Date.now().toString(36)}`);
        await otherPage
          .getByLabel("密码")
          .fill(`P1-7E Other ${crypto.randomUUID()}!`);
        expect(OTHER_INVITE_CODE).toBeTruthy();
        await otherPage.getByLabel("邀请码").fill(OTHER_INVITE_CODE ?? "");
        await otherPage.getByRole("button", { name: "创建账户" }).click();
        await expect(
          otherPage.getByRole("heading", { name: "下一场完整模拟" }),
        ).toBeVisible();
        const isolation = await otherPage.evaluate(
          async ({ apiBaseUrl, session }) => {
            const sessionRead = await fetch(
              `${apiBaseUrl}/sessions/${session}`,
              { credentials: "include" },
            );
            const read = await fetch(
              `${apiBaseUrl}/sessions/${session}/report`,
              { credentials: "include" },
            );
            const generate = await fetch(
              `${apiBaseUrl}/sessions/${session}/report`,
              {
                method: "POST",
                credentials: "include",
                headers: { "X-GIA-CSRF": "1" },
              },
            );
            return {
              sessionRead: {
                status: sessionRead.status,
                body: await sessionRead.text(),
              },
              read: { status: read.status, body: await read.text() },
              generate: {
                status: generate.status,
                body: await generate.text(),
              },
            };
          },
          { apiBaseUrl: API_BASE_URL, session: sessionId },
        );
        expect(isolation.sessionRead.status).toBe(404);
        expect(isolation.read.status).toBe(404);
        expect(isolation.generate.status).toBe(404);
        expect(JSON.stringify(isolation)).not.toContain(sessionId);
        expect(JSON.stringify(isolation)).not.toContain(
          generatedReport.report_id,
        );
      } finally {
        await otherContext.close();
      }

      const reportEvidence = JSON.stringify(firstRead.body);
      const reportPageText = await page.locator("body").innerText();
      for (const sentinel of PRIVATE_SENTINELS) {
        expect(reportEvidence).not.toContain(sentinel);
        expect(reportPageText).not.toContain(sentinel);
      }
    };
  });

  test("continues the same durable session to COMPLETED", async () => {
    if (P17E_FINAL_COMPOSITION) test.setTimeout(90_000);
    expect(finishLifecycle).toBeDefined();
    await finishLifecycle!();
  });
});
