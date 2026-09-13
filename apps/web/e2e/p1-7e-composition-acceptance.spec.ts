import { expect, test } from "@playwright/test";
import { access, readFile, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_P17E_API_ORIGIN ?? "http://localhost:8000";
const API_RESTART_REQUEST = process.env.GIA_P17E_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_P17E_API_RESTART_READY;
const PRE_REPORT_PROBE_REQUEST = process.env.GIA_P17E_PRE_REPORT_PROBE_REQUEST;
const PRE_REPORT_PROBE_RESULT = process.env.GIA_P17E_PRE_REPORT_PROBE_RESULT;
const BROWSER_EVIDENCE = process.env.GIA_P17E_BROWSER_EVIDENCE;
const PROVIDER_CALLS = process.env.GIA_P17E_PROVIDER_CALLS;
const INTERNAL_VALIDATION_QUESTION_VERSION_ID =
  "21000000-0000-4000-8000-000000000001";
const PRIVATE_SENTINELS = [
  "P16D_PRIVATE_ALPHA_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_BRAVO_DO_NOT_DISCLOSE",
  "P16D_PRIVATE_CHARLIE_DO_NOT_DISCLOSE",
];
const LIFECYCLE = [
  "PREPARATION",
  "OPENING_STATEMENTS",
  "EXPLORATION",
  "CONFLICT_AND_EVALUATION",
  "CONVERGENCE",
  "FINAL_SUMMARY",
  "COMPLETED",
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
  phase_started_at: string | null;
  phase_deadline_at: string | null;
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
  content: string;
};
type EvidenceCard = {
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
  content: null | {
    overview: {
      session_status: string;
      question: Record<string, unknown>;
      participant_count: number;
      human_utterance_count: number;
      ai_utterance_count: number;
      total_utterance_count: number;
      covered_phases: string[];
      summary: string;
    };
    strengths: EvidenceCard[];
    improvements: EvidenceCard[];
    priority_improvement: string;
  };
};
type PreReportProbe = { report_count: number; evidence_count: number };

test.skip(
  !API_RESTART_REQUEST ||
    !API_RESTART_READY ||
    !PRE_REPORT_PROBE_REQUEST ||
    !PRE_REPORT_PROBE_RESULT ||
    !BROWSER_EVIDENCE ||
    !PROVIDER_CALLS,
  "P1-7E requires its dedicated network-free API/PostgreSQL harness.",
);

test("composes discussion, report, reload, restart, and owner isolation", async ({
  browser,
}) => {
  test.setTimeout(180_000);
  const ownerContext = await browser.newContext();
  const otherContext = await browser.newContext();
  const page = await ownerContext.newPage();
  const publicWebSocketEvents: string[] = [];
  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    const server = socket.connectToServer();
    socket.onMessage((message) => server.send(message));
    server.onMessage((message) => {
      publicWebSocketEvents.push(message.toString());
      socket.send(message);
    });
  });

  const fileExists = async (path: string): Promise<boolean> => {
    try {
      await access(path);
      return true;
    } catch {
      return false;
    }
  };
  const readJson = async <T>(path: string): Promise<T> =>
    JSON.parse(await readFile(path, "utf8")) as T;

  try {
    await page.goto("/");
    await page.getByRole("button", { name: "注册" }).click();
    await page
      .getByLabel("用户名")
      .fill(`P17E_OWNER_${Date.now().toString(36)}`);
    await page
      .getByLabel("密码")
      .fill(`P1-7E owner ${crypto.randomUUID()} phrase`);
    await page.getByRole("button", { name: "创建账户" }).click();
    await expect(page.getByRole("heading", { name: "讨论会话" })).toBeVisible();

    await page
      .getByRole("combobox")
      .selectOption(INTERNAL_VALIDATION_QUESTION_VERSION_ID);
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
        async ({ apiBaseUrl, id }) => {
          const response = await fetch(`${apiBaseUrl}/sessions/${id}`, {
            credentials: "include",
          });
          if (!response.ok)
            throw new Error(`snapshot failed: ${response.status}`);
          return (await response.json()) as SessionSnapshot;
        },
        { apiBaseUrl: API_BASE_URL, id: sessionId },
      );
    const fetchTranscript = () =>
      page.evaluate(
        async ({ apiBaseUrl, id }) => {
          const response = await fetch(
            `${apiBaseUrl}/sessions/${id}/utterances?after_sequence=0&limit=200`,
            { credentials: "include" },
          );
          if (!response.ok)
            throw new Error(`transcript failed: ${response.status}`);
          return ((await response.json()) as { items: TranscriptItem[] }).items;
        },
        { apiBaseUrl: API_BASE_URL, id: sessionId },
      );
    const getReport = () =>
      page.evaluate(
        async ({ apiBaseUrl, id }) => {
          const response = await fetch(`${apiBaseUrl}/sessions/${id}/report`, {
            credentials: "include",
          });
          return {
            status: response.status,
            body: response.ok ? ((await response.json()) as ReportView) : null,
          };
        },
        { apiBaseUrl: API_BASE_URL, id: sessionId },
      );
    const postReport = () =>
      page.evaluate(
        async ({ apiBaseUrl, id }) => {
          const response = await fetch(`${apiBaseUrl}/sessions/${id}/report`, {
            method: "POST",
            credentials: "include",
            headers: { "X-GIA-CSRF": "1" },
          });
          return {
            status: response.status,
            body: response.ok
              ? ((await response.json()) as ReportView["report"])
              : null,
          };
        },
        { apiBaseUrl: API_BASE_URL, id: sessionId },
      );

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

    const submittedHumanGrants = new Set<string>();
    const humanUtterances: string[] = [];
    const driveHumanTurn = async (snapshot: SessionSnapshot): Promise<void> => {
      const grant = snapshot.floor.current_grant;
      if (
        !grant ||
        grant.participant_id !== humans[0].participant_id ||
        submittedHumanGrants.has(grant.grant_id)
      ) {
        return;
      }
      const content =
        `  P17E_HUMAN_PUBLIC:${grant.phase}:${grant.grant_id}: ` +
        "明确比较执行风险、公众承诺与并行处理窗口，并给出可复核的取舍。\n";
      submittedHumanGrants.add(grant.grant_id);
      humanUtterances.push(content);
      await page.getByLabel("发言草稿").fill(content);
      await page.getByRole("button", { name: "发送发言" }).click();
    };

    await expect(page.getByText("连接正常").first()).toBeVisible();
    await page.getByRole("button", { name: "开始讨论" }).click();
    await expect
      .poll(
        async () => {
          const snapshot = await fetchSnapshot();
          await driveHumanTurn(snapshot);
          return snapshot.status;
        },
        { timeout: 120_000, intervals: [100, 250, 500] },
      )
      .toBe("COMPLETED");

    const completedSnapshot = await fetchSnapshot();
    const transcript = await fetchTranscript();
    const spokenAiIds = new Set(
      transcript
        .filter((item) => item.actor_kind === "AI")
        .map((item) => item.participant_id),
    );
    expect(completedSnapshot.floor.current_grant).toBeNull();
    expect(completedSnapshot.phase_started_at).toBeNull();
    expect(completedSnapshot.phase_deadline_at).toBeNull();
    expect(transcript.some((item) => item.actor_kind === "HUMAN")).toBe(true);
    expect(
      ais.every((participant) => spokenAiIds.has(participant.participant_id)),
    ).toBe(true);
    const completionLastSequence = completedSnapshot.last_sequence;

    const beforeGeneration = await getReport();
    expect(beforeGeneration.status).toBe(404);
    await writeFile(
      PRE_REPORT_PROBE_REQUEST!,
      JSON.stringify({ session_id: sessionId }),
      "utf8",
    );
    await expect
      .poll(() => fileExists(PRE_REPORT_PROBE_RESULT!), { timeout: 15_000 })
      .toBe(true);
    const preReportProbe = await readJson<PreReportProbe>(
      PRE_REPORT_PROBE_RESULT!,
    );
    expect(preReportProbe).toEqual({ report_count: 0, evidence_count: 0 });

    const generationResponsePromise = page.waitForResponse(
      (response) =>
        response.url() === `${API_BASE_URL}/sessions/${sessionId}/report` &&
        response.request().method() === "POST",
    );
    await page.getByRole("button", { name: "生成 / 查看训练报告" }).click();
    const generationResponse = await generationResponsePromise;
    expect(generationResponse.status()).toBe(200);
    await expect(page).toHaveURL(
      new RegExp(`/sessions/${sessionId}/report$`, "u"),
    );
    await expect(page.getByRole("heading", { name: "训练报告" })).toBeVisible();

    const firstGet = await getReport();
    expect(firstGet.status).toBe(200);
    const report = firstGet.body!;
    expect(report.report.status).toBe("COMPLETED");
    expect(report.report.session_id).toBe(sessionId);
    expect(report.report.report_schema_version).toBe(1);
    expect(report.report.derivation_version).toBe("basic-report/v1");
    expect(report.report.source_through_sequence).toBe(completionLastSequence);
    expect(report.content).not.toBeNull();
    expect(report.content!.overview.session_status).toBe("COMPLETED");
    expect(report.content!.overview.participant_count).toBe(4);
    expect(
      report.content!.overview.human_utterance_count,
    ).toBeGreaterThanOrEqual(1);
    expect(report.content!.overview.ai_utterance_count).toBeGreaterThanOrEqual(
      3,
    );
    expect(report.content!.overview.total_utterance_count).toBe(
      report.content!.overview.human_utterance_count +
        report.content!.overview.ai_utterance_count,
    );
    expect(report.content!.overview.covered_phases.length).toBeGreaterThan(0);
    expect(report.content!.overview.summary).toBeTruthy();
    expect(report.content!.priority_improvement).toBeTruthy();
    expect(report.content!.strengths).toHaveLength(1);
    expect(report.content!.strengths.length).toBeLessThanOrEqual(3);
    expect(report.content!.improvements.length).toBeLessThanOrEqual(3);
    const evidence = [
      ...report.content!.strengths,
      ...report.content!.improvements,
    ];
    expect(evidence.length).toBeGreaterThan(0);
    expect(evidence[0].quote).toBe(
      transcript.find((item) => item.actor_kind === "HUMAN")!.content,
    );

    const repeatedGet = await getReport();
    expect(repeatedGet).toEqual(firstGet);
    await page.reload();
    await expect(page.getByRole("heading", { name: "训练报告" })).toBeVisible();
    expect(await getReport()).toEqual(firstGet);

    const repeatedPost = await postReport();
    expect(repeatedPost.status).toBe(200);
    expect(repeatedPost.body).toEqual(report.report);

    await writeFile(API_RESTART_REQUEST!, "restart", "utf8");
    await expect
      .poll(() => fileExists(API_RESTART_READY!), { timeout: 20_000 })
      .toBe(true);
    await page.reload();
    await expect(page.getByRole("heading", { name: "训练报告" })).toBeVisible();
    const afterRestart = await getReport();
    expect(afterRestart).toEqual(firstGet);

    const otherPage = await otherContext.newPage();
    await otherPage.goto("/");
    await otherPage.getByRole("button", { name: "注册" }).click();
    await otherPage
      .getByLabel("用户名")
      .fill(`P17E_OTHER_${Date.now().toString(36)}`);
    await otherPage
      .getByLabel("密码")
      .fill(`P1-7E other ${crypto.randomUUID()} phrase`);
    await otherPage.getByRole("button", { name: "创建账户" }).click();
    await expect(
      otherPage.getByRole("heading", { name: "讨论会话" }),
    ).toBeVisible();
    const otherGet = await otherPage.evaluate(
      async ({ apiBaseUrl, id }) => {
        const response = await fetch(`${apiBaseUrl}/sessions/${id}/report`, {
          credentials: "include",
        });
        return { status: response.status, text: await response.text() };
      },
      { apiBaseUrl: API_BASE_URL, id: sessionId },
    );
    expect(otherGet.status).toBe(404);
    await otherPage.goto(`/sessions/${sessionId}/report`);
    await expect(otherPage.getByText("未找到可查看的训练报告")).toBeVisible();
    const otherBody = await otherPage.locator("body").innerText();
    expect(otherBody).not.toContain(report.content!.overview.summary);
    expect(otherBody).not.toContain(evidence[0].quote);

    const ownerBody = await page.locator("body").innerText();
    const publicSurface = JSON.stringify({
      report,
      transcript,
      publicWebSocketEvents,
      ownerBody,
      otherBody,
      otherGet,
    });
    for (const forbidden of [
      ...PRIVATE_SENTINELS,
      "private_information",
      "red_lines",
      "concession_conditions",
      "behavior_parameters",
      "hidden_conflicts",
      "acceptable_outcome_patterns",
      "reference_dimensions",
      "Authorization",
      "Cookie",
      "chain-of-thought",
      "user_private_notes",
    ]) {
      expect(publicSurface).not.toContain(forbidden);
    }
    for (const forbidden of [
      "overall_score",
      "six_dimension",
      "percentile",
      "ranking",
      "outperformed",
      "hiring_probability",
      "job_fit",
      "personality_type",
      "雷达图",
      "录取概率",
    ]) {
      expect(publicSurface.toLowerCase()).not.toContain(
        forbidden.toLowerCase(),
      );
    }

    const providerLines = (await readFile(PROVIDER_CALLS!, "utf8"))
      .split(/\r?\n/u)
      .filter(Boolean);
    expect(providerLines.length).toBeGreaterThan(0);
    await writeFile(
      BROWSER_EVIDENCE!,
      JSON.stringify(
        {
          session_id: sessionId,
          candidate_participant_ids: candidates.map(
            (participant) => participant.participant_id,
          ),
          human_participant_id: humans[0].participant_id,
          ai_participant_ids: ais.map(
            (participant) => participant.participant_id,
          ),
          lifecycle: LIFECYCLE,
          completion_last_sequence: completionLastSequence,
          transcript,
          report,
          repeated_get: repeatedGet,
          repeated_post: repeatedPost,
          after_restart: afterRestart,
          pre_report_probe: preReportProbe,
          public_websocket_events: publicWebSocketEvents,
          owner_isolation_status: otherGet.status,
        },
        null,
        2,
      ),
      "utf8",
    );
  } finally {
    await otherContext.close();
    await ownerContext.close();
  }
});
