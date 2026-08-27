import { expect, test } from "@playwright/test";
import { access, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE";
const HUMAN_CONTRIBUTION =
  "  Human evidence: preserve this exact contribution.\nSecond line stays exact.  ";
const PRIVATE_NOTES = "仅在当前页面内存中保留的私人思路";
const API_RESTART_REQUEST = process.env.GIA_E2E_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_E2E_API_RESTART_READY;
const FLOOR_REQUEST = process.env.GIA_E2E_FLOOR_REQUEST;
const FLOOR_READY = process.env.GIA_E2E_FLOOR_READY;

test("browser session recovers durable phases across API restart and reload", async ({
  page,
}, testInfo) => {
  const username = `P11D_${Date.now().toString(36)}`;
  const password = `P1-1D browser ${crypto.randomUUID()} phrase`;
  let startCommand: string | undefined;
  let floorEvent: string | undefined;
  let humanSubmitCommand: string | undefined;
  let humanCreatedEvent: string | undefined;
  let humanReleaseEvent: string | undefined;
  let releaseHumanConfirmation: (() => void) | undefined;
  let humanConfirmationReleased = false;
  let authoritativeReadCount = 0;
  let workspaceWebSocketCount = 0;

  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (
      request.method() === "GET" &&
      (/\/questions\/[^/]+$/.test(pathname) ||
        /\/sessions\/[^/]+$/.test(pathname) ||
        /\/sessions\/[^/]+\/utterances$/.test(pathname))
    ) {
      authoritativeReadCount += 1;
    }
  });

  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    workspaceWebSocketCount += 1;
    const server = socket.connectToServer();
    const bufferedServerFrames: Array<Parameters<typeof socket.send>[0]> = [];
    let bufferingHumanConfirmation = false;

    socket.onMessage((message) => {
      const payload = message.toString();
      if (payload.includes("session.start")) {
        startCommand = payload;
      }
      if (payload.includes("participant.utterance.submit")) {
        humanSubmitCommand = payload;
      }
      server.send(message);
    });

    server.onMessage((message) => {
      const payload = message.toString();
      if (payload.includes("floor.granted")) {
        floorEvent = payload;
      }
      const isHumanConfirmation =
        payload.includes("participant.utterance.created") &&
        payload.includes('\"actor_kind\":\"HUMAN\"');
      if (isHumanConfirmation) {
        humanCreatedEvent = payload;
      }
      if (
        payload.includes("floor.released") &&
        payload.includes('\"reason_code\":\"SPEAKER_FINISHED\"')
      ) {
        humanReleaseEvent = payload;
      }

      if (
        !humanConfirmationReleased &&
        (bufferingHumanConfirmation || isHumanConfirmation)
      ) {
        bufferingHumanConfirmation = true;
        bufferedServerFrames.push(message);
        releaseHumanConfirmation ??= () => {
          humanConfirmationReleased = true;
          bufferingHumanConfirmation = false;
          for (const bufferedFrame of bufferedServerFrames.splice(0)) {
            socket.send(bufferedFrame);
          }
          releaseHumanConfirmation = undefined;
        };
        return;
      }

      socket.send(message);
    });
  });

  const exactConfirmedContributionCount = () =>
    page
      .locator('[data-testid^="utterance-content-"]')
      .evaluateAll(
        (items, exactContent) =>
          items.filter((item) => item.textContent === exactContent).length,
        HUMAN_CONTRIBUTION,
      );

  const captureResponsiveEvidence = async (name: string) => {
    const path = testInfo.outputPath(name + ".png");
    await page.screenshot({ fullPage: true, path });
    await testInfo.attach(name, { contentType: "image/png", path });
  };

  await page.setViewportSize({ height: 900, width: 1440 });
  await page.goto("/");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill(username);
  await page.getByLabel("密码").fill(password);
  await page.getByRole("button", { name: "创建账户" }).click();
  await expect(page.getByRole("heading", { name: "讨论会话" })).toBeVisible();
  await expect(page.getByLabel("选择训练题目")).toContainText(
    "内部验证：社区活动资源安排",
  );

  const discovery = await page.evaluate(async (apiBaseUrl) => {
    const response = await fetch(`${apiBaseUrl}/questions`, {
      credentials: "include",
    });
    return { status: response.status, body: await response.json() };
  }, API_BASE_URL);
  expect(discovery.status).toBe(200);
  expect(discovery.body).toHaveLength(1);
  const questionVersionId = discovery.body[0].id as string;
  expect(JSON.stringify(discovery)).not.toContain(PRIVATE_SENTINEL);

  const createResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === `${API_BASE_URL}/sessions` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "创建文字会话" }).click();
  const createResponse = await createResponsePromise;
  expect(createResponse.status()).toBe(201);
  expect((await createResponse.request().allHeaders())["x-gia-csrf"]).toBe("1");
  expect(createResponse.request().postDataJSON()).toEqual({
    question_version_id: questionVersionId,
  });
  const createdSession = (await createResponse.json()) as {
    id: string;
    question_version_id: string | null;
    status: string;
    last_sequence: number;
  };
  expect(createdSession).toMatchObject({
    id: expect.stringMatching(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    ),
    question_version_id: questionVersionId,
    status: "CREATED",
    last_sequence: 1,
  });
  const sessionId = createdSession.id;
  expect(new URL(page.url()).searchParams.get("session_id")).toBe(sessionId);

  await expect(page.getByText("连接正常").first()).toBeVisible();
  await expect(page.getByText("未开始", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByText("内部工程验证题：团队需要在有限资源下安排三类社区活动。"),
  ).toBeVisible();
  await expect(
    page.getByText("形成满足硬约束、说明取舍且可执行的资源安排。"),
  ).toBeVisible();
  for (const diagnosticTestId of [
    "session-id",
    "session-sequence",
    "question-version-id",
    "phase-deadline",
  ]) {
    await expect(page.getByTestId(diagnosticTestId)).toHaveCount(0);
  }
  expect(await page.locator("body").textContent()).not.toContain(sessionId);
  expect(await page.locator("body").textContent()).not.toContain(
    questionVersionId,
  );

  const taskSurface = page.locator("#task-surface");
  const discussionSurface = page.locator("#discussion-surface");
  const progressSurface = page.locator("#progress-surface");
  await expect(taskSurface).toBeVisible();
  await expect(discussionSurface).toBeVisible();
  await expect(progressSurface).toBeVisible();
  const [taskBox, discussionBox, progressBox] = await Promise.all([
    taskSurface.boundingBox(),
    discussionSurface.boundingBox(),
    progressSurface.boundingBox(),
  ]);
  expect(taskBox).not.toBeNull();
  expect(discussionBox).not.toBeNull();
  expect(progressBox).not.toBeNull();
  expect(discussionBox!.width).toBeGreaterThan(taskBox!.width);
  expect(discussionBox!.width).toBeGreaterThan(progressBox!.width);
  await page.getByLabel("发言草稿").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("发言草稿")).toBeVisible();
  await captureResponsiveEvidence("f3b-wide-1440x900");

  const authorityReadsBeforeSwitching = authoritativeReadCount;
  const webSocketsBeforeSwitching = workspaceWebSocketCount;
  await page.setViewportSize({ height: 900, width: 900 });
  await expect(discussionSurface).toBeVisible();
  await expect(taskSurface).toBeHidden();
  await expect(progressSurface).toBeHidden();
  await page.getByRole("button", { name: "打开题目与思考" }).click();
  await expect(taskSurface).toBeVisible();
  await expect(progressSurface).toBeHidden();
  await page
    .getByRole("textbox", { name: "我的思路 / 私人笔记" })
    .fill(PRIVATE_NOTES);
  await page.getByRole("button", { name: "打开训练进程" }).click();
  await expect(taskSurface).toBeHidden();
  await expect(progressSurface).toBeVisible();
  await page.getByRole("button", { name: "关闭训练进程" }).click();
  await expect(taskSurface).toBeHidden();
  await expect(progressSurface).toBeHidden();
  await expect(discussionSurface).toBeVisible();
  await page.getByLabel("发言草稿").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("发言草稿")).toBeVisible();
  await captureResponsiveEvidence("f3b-tablet-900x900");

  await page.setViewportSize({ height: 844, width: 390 });
  const tabs = page.getByRole("tab");
  await expect(tabs).toHaveText(["讨论", "题目", "进程"]);
  const discussionTab = page.getByRole("tab", { name: "讨论" });
  const taskTab = page.getByRole("tab", { name: "题目" });
  const progressTab = page.getByRole("tab", { name: "进程" });
  await expect(discussionTab).toHaveAttribute(
    "aria-controls",
    "discussion-surface",
  );
  await expect(taskTab).toHaveAttribute("aria-controls", "task-surface");
  await expect(progressTab).toHaveAttribute(
    "aria-controls",
    "progress-surface",
  );
  await expect(discussionSurface).toHaveAttribute(
    "aria-labelledby",
    "discussion-tab",
  );
  await expect(taskSurface).toHaveAttribute("aria-labelledby", "task-tab");
  await expect(progressSurface).toHaveAttribute(
    "aria-labelledby",
    "progress-tab",
  );
  await discussionTab.focus();
  await discussionTab.press("ArrowRight");
  await expect(taskTab).toBeFocused();
  await expect(taskTab).toHaveAttribute("aria-selected", "true");
  await expect(taskSurface).toBeVisible();
  await expect(discussionSurface).toBeHidden();
  await expect(
    page.getByRole("textbox", { name: "我的思路 / 私人笔记" }),
  ).toHaveValue(PRIVATE_NOTES);
  await taskTab.press("End");
  await expect(progressTab).toBeFocused();
  await expect(progressSurface).toBeVisible();
  await progressTab.press("Home");
  await expect(discussionTab).toBeFocused();
  await expect(discussionSurface).toBeVisible();
  await discussionTab.press("ArrowLeft");
  await expect(progressTab).toBeFocused();
  await progressTab.press("ArrowRight");
  await expect(discussionTab).toBeFocused();
  await expect(discussionSurface).toBeVisible();
  await page.getByLabel("发言草稿").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("发言草稿")).toBeVisible();
  expect(authoritativeReadCount).toBe(authorityReadsBeforeSwitching);
  expect(workspaceWebSocketCount).toBe(webSocketsBeforeSwitching);
  await captureResponsiveEvidence("f3b-mobile-390x844");

  const transientStorage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
  }));
  expect(transientStorage).toEqual({ local: [], session: [] });
  expect(JSON.stringify(transientStorage)).not.toContain(PRIVATE_NOTES);
  expect(JSON.stringify(transientStorage)).not.toContain(sessionId);

  await page.setViewportSize({ height: 900, width: 1440 });
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "我的思路 / 私人笔记" }),
  ).toHaveValue("");
  await expect(page.getByText("连接正常").first()).toBeVisible();

  await page.getByRole("button", { name: "开始讨论" }).click();
  await expect(page.getByText("准备", { exact: true }).first()).toBeVisible();
  await expect.poll(() => startCommand).toBeTruthy();
  const parsedCommand = JSON.parse(startCommand ?? "{}");
  expect(parsedCommand).toEqual({
    schema_version: 1,
    type: "session.start",
    session_id: sessionId,
    action_id: expect.stringMatching(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    ),
    payload: {},
  });
  expect(startCommand).not.toContain("next_status");
  expect(startCommand).not.toContain("phase_deadline_at");

  await expect(
    page.locator('[aria-current="step"]').getByText("个人陈述", {
      exact: true,
    }),
  ).toBeVisible({ timeout: 10_000 });
  expect(FLOOR_REQUEST).toBeTruthy();
  expect(FLOOR_READY).toBeTruthy();
  await writeFile(FLOOR_REQUEST!, sessionId, "utf8");
  await expect
    .poll(
      async () => {
        try {
          await access(FLOOR_READY!);
          return true;
        } catch {
          return false;
        }
      },
      { timeout: 10_000 },
    )
    .toBe(true);
  await expect.poll(() => floorEvent).toBeTruthy();
  const parsedFloorEvent = JSON.parse(floorEvent ?? "{}");
  expect(parsedFloorEvent).toMatchObject({
    schema_version: 2,
    type: "floor.granted",
    session_id: sessionId,
    sequence: 4,
    action_id: null,
    payload: {
      phase: "OPENING_STATEMENTS",
      reason_code: "FIRST_OPPORTUNITY",
    },
  });
  expect(parsedFloorEvent.sequence).toBeGreaterThan(
    createdSession.last_sequence,
  );
  await expect(
    page.getByText("当前发言：你（真人参与者）", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("发言权已授予", { exact: true })).toBeVisible();
  await expect(
    page.getByText("优先安排尚未发言的参与者", { exact: true }),
  ).toBeVisible();
  for (const forbidden of [
    "private_stance",
    "persona_calibration",
    "policy_weights",
    "hidden_ranking",
    "decision_metadata",
    "score",
    "prompt",
    "provider",
  ]) {
    expect(floorEvent!.toLowerCase()).not.toContain(forbidden);
  }

  const humanFloorGrantId = parsedFloorEvent.payload.grant_id as string;
  const humanParticipantId = parsedFloorEvent.payload.participant_id as string;
  const draft = page.getByLabel("发言草稿");
  await draft.fill(HUMAN_CONTRIBUTION);
  await page.getByRole("button", { name: "发送发言" }).click();
  await expect.poll(() => humanSubmitCommand).toBeTruthy();
  await expect.poll(() => humanCreatedEvent).toBeTruthy();
  await expect(page.getByTestId("human-pending")).toBeVisible();
  await expect(page.getByTestId("human-pending-content")).toHaveText(
    HUMAN_CONTRIBUTION,
    { useInnerText: false },
  );
  expect(await exactConfirmedContributionCount()).toBe(0);

  const parsedHumanCommand = JSON.parse(humanSubmitCommand ?? "{}");
  expect(parsedHumanCommand).toEqual({
    schema_version: 1,
    type: "participant.utterance.submit",
    session_id: sessionId,
    action_id: expect.stringMatching(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    ),
    payload: {
      floor_grant_id: humanFloorGrantId,
      content: HUMAN_CONTRIBUTION,
    },
  });

  const parsedHumanEvent = JSON.parse(humanCreatedEvent ?? "{}");
  expect(parsedHumanEvent).toMatchObject({
    schema_version: 1,
    type: "participant.utterance.created",
    session_id: sessionId,
    action_id: parsedHumanCommand.action_id,
    payload: {
      participant_id: humanParticipantId,
      actor_kind: "HUMAN",
      floor_grant_id: humanFloorGrantId,
      phase: "OPENING_STATEMENTS",
      content: HUMAN_CONTRIBUTION,
    },
  });
  expect(releaseHumanConfirmation).toBeDefined();
  releaseHumanConfirmation?.();
  await expect.poll(exactConfirmedContributionCount).toBe(1);
  await expect(page.getByTestId("human-pending")).toHaveCount(0);

  await expect.poll(() => humanReleaseEvent).toBeTruthy();
  const parsedHumanRelease = JSON.parse(humanReleaseEvent ?? "{}");
  expect(parsedHumanRelease).toMatchObject({
    schema_version: 2,
    type: "floor.released",
    session_id: sessionId,
    sequence: parsedHumanEvent.sequence + 1,
    action_id: parsedHumanCommand.action_id,
    payload: {
      grant_id: humanFloorGrantId,
      participant_id: humanParticipantId,
      phase: "OPENING_STATEMENTS",
      reason_code: "SPEAKER_FINISHED",
    },
  });

  await page.reload();
  await expect.poll(exactConfirmedContributionCount).toBe(1);
  expect(
    await page
      .locator('[data-testid^="utterance-content-"]')
      .filter({ hasText: "Human evidence" })
      .first()
      .textContent(),
  ).toBe(HUMAN_CONTRIBUTION);
  await expect(page.getByText("连接正常").first()).toBeVisible();

  expect(API_RESTART_REQUEST).toBeTruthy();
  expect(API_RESTART_READY).toBeTruthy();
  await writeFile(API_RESTART_REQUEST!, "restart", "utf8");
  await expect
    .poll(
      async () => {
        try {
          await access(API_RESTART_READY!);
          return true;
        } catch {
          return false;
        }
      },
      { timeout: 10_000 },
    )
    .toBe(true);
  await expect(page.getByText("连接正常").first()).toBeVisible({
    timeout: 10_000,
  });
  await expect.poll(exactConfirmedContributionCount).toBe(1);

  await expect(page.getByText("已完成", { exact: true }).first()).toBeVisible({
    timeout: 25_000,
  });
  await expect(
    page.getByText("讨论已完成", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("正在安排下一位发言者", { exact: true }),
  ).toHaveCount(0);
  await expect.poll(exactConfirmedContributionCount).toBe(1);

  const authoritative = await page.evaluate(
    async ({ apiBaseUrl, session }) => {
      const response = await fetch(`${apiBaseUrl}/sessions/${session}`, {
        credentials: "include",
      });
      return { status: response.status, body: await response.json() };
    },
    { apiBaseUrl: API_BASE_URL, session: sessionId },
  );
  expect(authoritative).toMatchObject({
    status: 200,
    body: {
      id: sessionId,
      question_version_id: questionVersionId,
      status: "COMPLETED",
      phase_started_at: null,
      phase_deadline_at: null,
      last_sequence: expect.any(Number),
      floor: {
        current_grant: null,
      },
    },
  });
  const finalSequence = Number(authoritative.body.last_sequence);
  expect(finalSequence).toBeGreaterThan(parsedHumanRelease.sequence);
  expect(JSON.stringify(authoritative)).not.toContain(PRIVATE_SENTINEL);

  const duplicate = await page.evaluate(
    ({ apiBaseUrl, command, session, afterSequence }) =>
      new Promise<Record<string, unknown>>((resolve, reject) => {
        const socketUrl = new URL(apiBaseUrl);
        socketUrl.protocol = socketUrl.protocol === "https:" ? "wss:" : "ws:";
        socketUrl.pathname = `/ws/sessions/${session}`;
        socketUrl.search = `after_sequence=${afterSequence.toString()}`;
        const socket = new WebSocket(socketUrl);
        const timeout = window.setTimeout(() => {
          socket.close();
          reject(new Error("Timed out waiting for duplicate replay"));
        }, 5_000);
        socket.addEventListener("open", () => socket.send(command));
        socket.addEventListener("message", (event) => {
          window.clearTimeout(timeout);
          socket.close();
          resolve(JSON.parse(String(event.data)) as Record<string, unknown>);
        });
        socket.addEventListener("error", () => {
          window.clearTimeout(timeout);
          reject(new Error("Duplicate replay WebSocket failed"));
        });
      }),
    {
      apiBaseUrl: API_BASE_URL,
      command: startCommand!,
      session: sessionId,
      afterSequence: finalSequence,
    },
  );
  expect(duplicate).toMatchObject({
    type: "session.state_changed",
    session_id: sessionId,
    sequence: 2,
    action_id: parsedCommand.action_id,
    payload: {
      previous_status: "CREATED",
      status: "PREPARATION",
      trigger: "USER_START",
    },
  });
  expect(JSON.stringify(duplicate)).not.toContain(PRIVATE_SENTINEL);

  expect(await page.locator("body").textContent()).not.toContain(
    PRIVATE_SENTINEL,
  );

  const browserStorage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
  }));
  expect(browserStorage).toEqual({ local: [], session: [] });
  expect(JSON.stringify(browserStorage)).not.toContain(parsedCommand.action_id);
  expect(JSON.stringify(browserStorage)).not.toContain(
    parsedHumanCommand.action_id,
  );
  expect(JSON.stringify(browserStorage)).not.toContain(humanFloorGrantId);
  expect(JSON.stringify(browserStorage)).not.toContain(HUMAN_CONTRIBUTION);
  expect(JSON.stringify(browserStorage)).not.toContain("human-pending");
  expect(JSON.stringify(browserStorage)).not.toContain("confirmed-transcript");
  expect(JSON.stringify(browserStorage)).not.toContain(sessionId);
  expect(JSON.stringify(browserStorage)).not.toContain(PRIVATE_NOTES);

  await page.reload();
  await expect(page.getByTestId("current-username")).toHaveText(
    username.toLowerCase(),
  );
  await expect(page.getByText("已完成", { exact: true }).first()).toBeVisible();
  await expect(
    page.getByText("讨论已完成", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("正在安排下一位发言者", { exact: true }),
  ).toHaveCount(0);
  await expect.poll(exactConfirmedContributionCount).toBe(1);
  await expect(
    page.getByText("内部工程验证题：团队需要在有限资源下安排三类社区活动。"),
  ).toBeVisible();
  await expect(page.getByText("连接正常").first()).toBeVisible();
  for (const diagnosticTestId of [
    "session-id",
    "session-sequence",
    "question-version-id",
    "phase-deadline",
  ]) {
    await expect(page.getByTestId(diagnosticTestId)).toHaveCount(0);
  }
});
