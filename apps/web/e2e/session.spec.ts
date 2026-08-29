import { expect, test } from "@playwright/test";
import { access, readFile, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE";
const HUMAN_CONTRIBUTION = [
  "  Human evidence: preserve this exact contribution.",
  ...Array.from(
    { length: 24 },
    (_, index) =>
      `Public evidence line ${String(index + 1).padStart(2, "0")}: resource allocation trade-offs stay concrete, attributable, and reviewable.`,
  ),
  "Second line stays exact.  ",
].join("\n");
const AI_CONTRIBUTION =
  process.env.GIA_E2E_AI_CONTENT ??
  "F4 Browser deterministic fake AI contribution.";
const R3_PROMPT_SENTINEL = "R3_PROMPT_CONTEXT_VERIFIED";
const PRIVATE_NOTES = "仅在当前页面内存中保留的私人思路";
const API_RESTART_REQUEST = process.env.GIA_E2E_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_E2E_API_RESTART_READY;
const PROVIDER_BLOCKED = process.env.GIA_E2E_PROVIDER_BLOCKED;
const PROVIDER_CANCELLED = process.env.GIA_E2E_PROVIDER_CANCELLED;

test.setTimeout(150_000);

test("browser session recovers durable phases across API restart and reload", async ({
  page,
}, testInfo) => {
  const username = `P11D_${Date.now().toString(36)}`;
  const password = `P1-1D browser ${crypto.randomUUID()} phrase`;
  expect(process.env.GIA_E2E_FLOOR_REQUEST).toBeUndefined();
  expect(process.env.GIA_E2E_FLOOR_READY).toBeUndefined();
  expect(PROVIDER_BLOCKED).toBeTruthy();
  expect(PROVIDER_CANCELLED).toBeTruthy();
  let startCommand: string | undefined;
  let floorEvent: string | undefined;
  const lifecycleEvents: string[] = [];
  const floorReleaseEvents: string[] = [];
  let humanSubmitCommand: string | undefined;
  let humanSubmitActionId: string | undefined;
  let humanCreatedEvent: string | undefined;
  let humanReleaseEvent: string | undefined;
  let laterUnrelatedReleaseEvent: string | undefined;
  let aiCreatedEvent: string | undefined;
  const aiCreatedEvents: string[] = [];
  let releaseHumanConfirmation: (() => void) | undefined;
  let humanConfirmationReleased = false;
  let releaseHistoryTail: (() => void) | undefined;
  let releaseBufferedHistoryRemainder: (() => void) | undefined;
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
    const bufferedHistoryFrames: Array<Parameters<typeof socket.send>[0]> = [];
    let bufferingHistoryTail = false;
    let releasedHistoryTailCount = 0;
    const isAiConfirmationFrame = (
      frame: Parameters<typeof socket.send>[0],
    ) => {
      const payload = frame.toString();
      return (
        payload.includes("participant.utterance.created") &&
        payload.includes('\"actor_kind\":\"AI\"')
      );
    };
    const armHistoryTailRelease = () => {
      if (
        releaseHistoryTail ||
        releaseBufferedHistoryRemainder ||
        !bufferingHistoryTail
      )
        return;
      const nextAiIndex = bufferedHistoryFrames.findIndex(
        isAiConfirmationFrame,
      );
      if (nextAiIndex < 0) return;
      releaseHistoryTail = () => {
        const releaseThroughIndex = bufferedHistoryFrames.findIndex(
          isAiConfirmationFrame,
        );
        if (releaseThroughIndex < 0) return;
        const frames = bufferedHistoryFrames.splice(0, releaseThroughIndex + 1);
        for (const bufferedFrame of frames) socket.send(bufferedFrame);
        releasedHistoryTailCount += 1;
        releaseHistoryTail = undefined;
        if (releasedHistoryTailCount >= 2) {
          releaseBufferedHistoryRemainder = () => {
            bufferingHistoryTail = false;
            for (const bufferedFrame of bufferedHistoryFrames.splice(0)) {
              socket.send(bufferedFrame);
            }
            releaseBufferedHistoryRemainder = undefined;
          };
        } else {
          armHistoryTailRelease();
        }
      };
    };

    socket.onMessage((message) => {
      const payload = message.toString();
      const command = JSON.parse(payload) as {
        type?: string;
        action_id?: string;
      };
      if (command.type === "session.start") {
        startCommand = payload;
      }
      if (command.type === "participant.utterance.submit") {
        humanSubmitCommand = payload;
        humanSubmitActionId = command.action_id;
      }
      server.send(message);
    });

    server.onMessage((message) => {
      const payload = message.toString();
      const event = JSON.parse(payload) as {
        schema_version?: number;
        type?: string;
        action_id?: string | null;
        payload?: { reason_code?: string };
      };
      if (payload.includes("floor.granted")) {
        floorEvent ??= payload;
        lifecycleEvents.push(payload);
      }
      if (payload.includes("session.state_changed")) {
        lifecycleEvents.push(payload);
      }
      const isHumanConfirmation =
        payload.includes("participant.utterance.created") &&
        payload.includes('\"actor_kind\":\"HUMAN\"');
      if (isHumanConfirmation) {
        humanCreatedEvent = payload;
      }
      if (
        payload.includes("participant.utterance.created") &&
        payload.includes('\"actor_kind\":\"AI\"')
      ) {
        aiCreatedEvent ??= payload;
        aiCreatedEvents.push(payload);
      }
      if (event.schema_version === 2 && event.type === "floor.released") {
        floorReleaseEvents.push(payload);
        if (event.payload?.reason_code === "SPEAKER_FINISHED") {
          if (event.action_id === humanSubmitActionId) {
            humanReleaseEvent = payload;
          } else if (humanReleaseEvent !== undefined) {
            laterUnrelatedReleaseEvent = payload;
          }
        }
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
          bufferingHistoryTail = true;
          const [humanFrame, ...tailFrames] = bufferedServerFrames.splice(0);
          if (humanFrame !== undefined) socket.send(humanFrame);
          bufferedHistoryFrames.push(...tailFrames);
          armHistoryTailRelease();
          releaseHumanConfirmation = undefined;
        };
        return;
      }
      if (bufferingHistoryTail) {
        bufferedHistoryFrames.push(message);
        armHistoryTailRelease();
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

  const exactConfirmedAiContributionCount = () =>
    page
      .locator('[data-testid^="utterance-content-"]')
      .evaluateAll(
        (items, exactContent) =>
          items.filter((item) => item.textContent === exactContent).length,
        AI_CONTRIBUTION,
      );

  const captureResponsiveEvidence = async (name: string) => {
    const path = testInfo.outputPath(name + ".png");
    await page.screenshot({ fullPage: true, path });
    await testInfo.attach(name, { contentType: "image/png", path });
  };
  const readLoadedLayout = () =>
    page.evaluate(() => {
      const transcript = document.querySelector<HTMLElement>(
        '[data-testid="confirmed-transcript-list"]',
      );
      const discussion = document.querySelector<HTMLElement>(
        "#discussion-surface",
      );
      const task = document.querySelector<HTMLElement>("#task-surface");
      const progress = document.querySelector<HTMLElement>("#progress-surface");
      const composer = document.querySelector<HTMLElement>(
        '[data-testid="human-composer"]',
      );
      const root = discussion?.closest<HTMLElement>('[class~="h-dvh"]');
      if (
        !transcript ||
        !discussion ||
        !task ||
        !progress ||
        !composer ||
        !root
      ) {
        throw new Error(
          "Loaded workspace layout probe could not resolve required nodes.",
        );
      }
      const rootBox = root.getBoundingClientRect();
      const composerBox = composer.getBoundingClientRect();
      const progressBox = progress.getBoundingClientRect();
      const centerLongScrollOwners = Array.from(
        discussion.querySelectorAll<HTMLElement>("*"),
      )
        .filter((element) => {
          const overflowY = getComputedStyle(element).overflowY;
          return (
            (overflowY === "auto" || overflowY === "scroll") &&
            element.scrollHeight > element.clientHeight
          );
        })
        .map((element) => element.dataset.testid ?? element.id);
      return {
        viewportHeight: window.innerHeight,
        documentHeight: Math.max(
          document.documentElement.scrollHeight,
          document.body.scrollHeight,
        ),
        root: { top: rootBox.top, bottom: rootBox.bottom },
        transcript: {
          scrollHeight: transcript.scrollHeight,
          clientHeight: transcript.clientHeight,
          scrollTop: transcript.scrollTop,
        },
        discussion: {
          overflowY: getComputedStyle(discussion).overflowY,
          scrollHeight: discussion.scrollHeight,
          clientHeight: discussion.clientHeight,
        },
        task: {
          overflowY: getComputedStyle(task).overflowY,
          scrollHeight: task.scrollHeight,
          clientHeight: task.clientHeight,
        },
        composer: { top: composerBox.top, bottom: composerBox.bottom },
        progress: { top: progressBox.top, bottom: progressBox.bottom },
        centerLongScrollOwners,
      };
    });

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
  await expect(
    page.locator('[data-product-surface="interview-simulation-studio"]'),
  ).toHaveCount(1);
  await expect(page.getByTestId("studio-identity")).toContainText(
    "Interview Simulation Studio",
  );
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
  expect(taskBox!.x + taskBox!.width).toBeLessThanOrEqual(discussionBox!.x);
  expect(discussionBox!.x + discussionBox!.width).toBeLessThanOrEqual(
    progressBox!.x,
  );
  expect(progressBox!.x + progressBox!.width).toBeLessThanOrEqual(1440);
  expect(discussionBox!.width).toBeGreaterThan(progressBox!.width);
  await page.getByLabel("发言草稿").scrollIntoViewIfNeeded();
  await expect(page.getByLabel("发言草稿")).toBeVisible();
  const boundedDocumentHeightAtWideBaseline = await page.evaluate(() =>
    Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
  );
  await captureResponsiveEvidence("f3b-wide-1440x900");

  const authorityReadsBeforeSwitching = authoritativeReadCount;
  const webSocketsBeforeSwitching = workspaceWebSocketCount;
  await page.setViewportSize({ height: 900, width: 900 });
  const boundedDocumentHeightAtTabletBaseline = await page.evaluate(() =>
    Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
  );
  await expect(discussionSurface).toBeVisible();
  await expect(taskSurface).toBeHidden();
  await expect(progressSurface).toBeHidden();
  await page.getByRole("button", { name: "打开题目与思考" }).click();
  await expect(taskSurface).toBeVisible();
  const [tabletTaskBox, tabletDiscussionBox] = await Promise.all([
    taskSurface.boundingBox(),
    discussionSurface.boundingBox(),
  ]);
  expect(tabletTaskBox).not.toBeNull();
  expect(tabletDiscussionBox).not.toBeNull();
  expect(tabletDiscussionBox!.width).toBeGreaterThan(tabletTaskBox!.width);
  expect(tabletTaskBox!.x + tabletTaskBox!.width).toBeLessThanOrEqual(900);
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
  const boundedDocumentHeightAtMobileBaseline = await page.evaluate(() =>
    Math.max(document.documentElement.scrollHeight, document.body.scrollHeight),
  );
  expect(
    await page.evaluate(() =>
      Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
    ),
  ).toBeLessThanOrEqual(390);
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
  await expect(page.getByText("当前发言：你", { exact: true })).toBeVisible();
  await expect(page.getByText("发言权已授予", { exact: true })).toBeVisible();
  await expect(
    page.locator('[data-current-speaker="true"]').filter({
      hasText: "你",
    }),
  ).toHaveAttribute("aria-current", "true");
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
  const transcriptList = page.getByTestId("confirmed-transcript-list");
  const initialReturnToLatest = page.getByRole("button", {
    name: "回到最新发言",
  });
  await expect(initialReturnToLatest).toBeVisible();
  await initialReturnToLatest.click();
  await expect
    .poll(() =>
      transcriptList.evaluate(
        (element) =>
          element.scrollHeight - element.scrollTop - element.clientHeight,
      ),
    )
    .toBeLessThanOrEqual(48);
  await page.getByTestId("human-composer").scrollIntoViewIfNeeded();
  await page
    .locator('[class~="h-dvh"]')
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  const desktopLayout = await readLoadedLayout();
  expect(desktopLayout.documentHeight).toBe(
    boundedDocumentHeightAtWideBaseline,
  );
  expect(desktopLayout.root.bottom - desktopLayout.root.top).toBe(
    desktopLayout.viewportHeight,
  );
  expect(desktopLayout.transcript.scrollHeight).toBeGreaterThan(
    desktopLayout.transcript.clientHeight,
  );
  expect(desktopLayout.discussion.overflowY).toBe("hidden");
  expect(desktopLayout.centerLongScrollOwners).toEqual([
    "confirmed-transcript-list",
  ]);
  expect(desktopLayout.task.overflowY).toBe("auto");
  expect(desktopLayout.composer.top).toBeGreaterThanOrEqual(0);
  expect(desktopLayout.composer.bottom).toBeLessThanOrEqual(
    desktopLayout.viewportHeight,
  );
  expect(desktopLayout.progress.top).toBeGreaterThanOrEqual(0);
  expect(desktopLayout.progress.bottom).toBeLessThanOrEqual(
    desktopLayout.viewportHeight,
  );
  expect(
    desktopLayout.transcript.scrollHeight -
      desktopLayout.transcript.scrollTop -
      desktopLayout.transcript.clientHeight,
  ).toBeLessThanOrEqual(48);
  await expect(page.getByRole("button", { name: "回到最新发言" })).toHaveCount(
    0,
  );
  if (desktopLayout.task.scrollHeight > desktopLayout.task.clientHeight) {
    const independentTaskScroll = await page.evaluate(() => {
      const task = document.querySelector<HTMLElement>("#task-surface")!;
      const transcript = document.querySelector<HTMLElement>(
        '[data-testid="confirmed-transcript-list"]',
      )!;
      const transcriptBefore = transcript.scrollTop;
      task.scrollTop = task.scrollHeight;
      return {
        taskMoved: task.scrollTop > 0,
        transcriptUnchanged: transcript.scrollTop === transcriptBefore,
      };
    });
    expect(independentTaskScroll).toEqual({
      taskMoved: true,
      transcriptUnchanged: true,
    });
  }
  await captureResponsiveEvidence("r2a-long-wide-1440x900");
  const historyScrollTop = await transcriptList.evaluate((element) => {
    element.scrollTop = 0;
    return element.scrollTop;
  });
  expect(historyScrollTop).toBe(0);
  await expect.poll(() => releaseHistoryTail).toBeTruthy();
  releaseHistoryTail?.();

  await expect.poll(() => humanReleaseEvent).toBeTruthy();
  await test.step("a later unrelated release cannot replace the Human release", async () => {
    await expect.poll(() => laterUnrelatedReleaseEvent).toBeTruthy();
    const parsedUnrelatedRelease = JSON.parse(
      laterUnrelatedReleaseEvent ?? "{}",
    );
    expect(parsedUnrelatedRelease).toMatchObject({
      schema_version: 2,
      type: "floor.released",
      session_id: sessionId,
      action_id: null,
      payload: { reason_code: "SPEAKER_FINISHED" },
    });
  });

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

  await expect.poll(() => aiCreatedEvent, { timeout: 10_000 }).toBeTruthy();
  const parsedAiEvent = JSON.parse(aiCreatedEvent ?? "{}");
  expect(parsedAiEvent).toMatchObject({
    schema_version: 1,
    type: "participant.utterance.created",
    session_id: sessionId,
    action_id: null,
    payload: {
      utterance_id: expect.stringMatching(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      ),
      participant_id: expect.stringMatching(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      ),
      actor_kind: "AI",
      floor_grant_id: expect.stringMatching(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
      ),
      phase: "OPENING_STATEMENTS",
      content: AI_CONTRIBUTION,
    },
  });
  expect(aiCreatedEvent).not.toContain(PRIVATE_SENTINEL);
  expect(parsedAiEvent.payload.content).toContain(R3_PROMPT_SENTINEL);
  expect(parsedAiEvent.sequence).toBeGreaterThan(parsedHumanRelease.sequence);
  await expect
    .poll(exactConfirmedAiContributionCount)
    .toBeGreaterThanOrEqual(1);
  const confirmedAiUtterance = page
    .getByTestId("confirmed-transcript")
    .getByTestId(
      `utterance-content-${parsedAiEvent.payload.utterance_id as string}`,
    );
  await expect(confirmedAiUtterance).toHaveText(AI_CONTRIBUTION, {
    useInnerText: false,
  });
  expect(await transcriptList.evaluate((element) => element.scrollTop)).toBe(
    historyScrollTop,
  );
  const returnToLatest = page.getByRole("button", { name: "回到最新发言" });
  await expect(returnToLatest).toBeVisible();
  await returnToLatest.click();
  await expect
    .poll(() =>
      transcriptList.evaluate(
        (element) =>
          element.scrollHeight - element.scrollTop - element.clientHeight,
      ),
    )
    .toBeLessThanOrEqual(48);
  await expect(returnToLatest).toHaveCount(0);
  await expect.poll(() => releaseHistoryTail).toBeTruthy();
  releaseHistoryTail?.();
  await expect.poll(exactConfirmedAiContributionCount).toBe(2);
  await expect
    .poll(() =>
      transcriptList.evaluate(
        (element) =>
          element.scrollHeight - element.scrollTop - element.clientHeight,
      ),
    )
    .toBeLessThanOrEqual(48);
  await expect(returnToLatest).toHaveCount(0);
  const parsedAiRelease = floorReleaseEvents
    .map((event) => JSON.parse(event))
    .find(
      (event) =>
        event.payload?.grant_id === parsedAiEvent.payload.floor_grant_id,
    );
  expect(parsedAiRelease).toMatchObject({
    schema_version: 2,
    type: "floor.released",
    session_id: sessionId,
    sequence: parsedAiEvent.sequence + 1,
    action_id: null,
    payload: {
      grant_id: parsedAiEvent.payload.floor_grant_id,
      participant_id: parsedAiEvent.payload.participant_id,
      phase: "OPENING_STATEMENTS",
      reason_code: "SPEAKER_FINISHED",
    },
  });
  expect(releaseBufferedHistoryRemainder).toBeDefined();
  releaseBufferedHistoryRemainder?.();

  await expect
    .poll(
      async () => {
        try {
          await access(PROVIDER_BLOCKED!);
          return true;
        } catch {
          return false;
        }
      },
      { timeout: 10_000 },
    )
    .toBe(true);
  const runningProviderState = JSON.parse(
    await readFile(PROVIDER_BLOCKED!, "utf8"),
  ) as { floor_grant_id: string; request_status: string };
  expect(runningProviderState).toMatchObject({ request_status: "RUNNING" });
  const socketsBeforeCancellationReload = workspaceWebSocketCount;

  await page.reload();

  await expect
    .poll(
      async () => {
        try {
          await access(PROVIDER_CANCELLED!);
          return true;
        } catch {
          return false;
        }
      },
      { timeout: 10_000 },
    )
    .toBe(true);
  const cancelledProviderState = JSON.parse(
    await readFile(PROVIDER_CANCELLED!, "utf8"),
  ) as { floor_grant_id: string };
  expect(cancelledProviderState.floor_grant_id).toBe(
    runningProviderState.floor_grant_id,
  );
  await expect(page.getByText("连接正常").first()).toBeVisible();
  expect(workspaceWebSocketCount).toBeGreaterThan(
    socketsBeforeCancellationReload,
  );
  await expect
    .poll(
      () =>
        floorReleaseEvents.filter((rawEvent) => {
          const event = JSON.parse(rawEvent);
          return (
            event.payload?.grant_id === runningProviderState.floor_grant_id &&
            event.payload?.reason_code === "INTERRUPTED"
          );
        }).length,
      { timeout: 10_000 },
    )
    .toBe(1);
  const interruptedRelease = floorReleaseEvents
    .map((rawEvent) => JSON.parse(rawEvent))
    .find(
      (event) =>
        event.payload?.grant_id === runningProviderState.floor_grant_id &&
        event.payload?.reason_code === "INTERRUPTED",
    );
  expect(interruptedRelease).toMatchObject({
    schema_version: 2,
    type: "floor.released",
    session_id: sessionId,
    action_id: null,
    payload: {
      grant_id: runningProviderState.floor_grant_id,
      reason_code: "INTERRUPTED",
    },
  });
  expect(
    aiCreatedEvents.filter(
      (rawEvent) =>
        JSON.parse(rawEvent).payload?.floor_grant_id ===
        runningProviderState.floor_grant_id,
    ),
  ).toHaveLength(0);
  await expect
    .poll(
      () =>
        lifecycleEvents.some((rawEvent) => {
          const event = JSON.parse(rawEvent);
          return (
            event.type === "floor.granted" &&
            event.sequence > interruptedRelease.sequence
          );
        }),
      { timeout: 10_000 },
    )
    .toBe(true);

  const readsBeforeLongResponsiveSwitching = authoritativeReadCount;
  const socketsBeforeLongResponsiveSwitching = workspaceWebSocketCount;
  await page.setViewportSize({ height: 900, width: 900 });
  await page
    .locator('[class~="h-dvh"]')
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  let responsiveLayout = await readLoadedLayout();
  expect(responsiveLayout.documentHeight).toBe(
    boundedDocumentHeightAtTabletBaseline,
  );
  expect(responsiveLayout.root.bottom - responsiveLayout.root.top).toBe(900);
  expect(responsiveLayout.transcript.scrollHeight).toBeGreaterThan(
    responsiveLayout.transcript.clientHeight,
  );
  expect(responsiveLayout.discussion.overflowY).toBe("hidden");
  expect(responsiveLayout.centerLongScrollOwners).toEqual([
    "confirmed-transcript-list",
  ]);
  expect(responsiveLayout.composer.bottom).toBeLessThanOrEqual(900);
  await page.getByRole("button", { name: "打开题目与思考" }).click();
  await expect(taskSurface).toBeVisible();
  await expect(progressSurface).toBeHidden();
  await page.getByRole("button", { name: "打开训练进程" }).click();
  await expect(taskSurface).toBeHidden();
  await expect(progressSurface).toBeVisible();
  await page.getByRole("button", { name: "关闭训练进程" }).click();
  await expect(discussionSurface).toBeVisible();
  await captureResponsiveEvidence("r2a-long-tablet-900x900");

  await page.setViewportSize({ height: 844, width: 390 });
  const longTabs = page.getByRole("tab");
  await expect(longTabs).toHaveText(["讨论", "题目", "进程"]);
  await expect(page.getByRole("tab", { name: "讨论" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page
    .locator('[class~="h-dvh"]')
    .evaluate((element) => element.scrollIntoView({ block: "start" }));
  responsiveLayout = await readLoadedLayout();
  expect(responsiveLayout.documentHeight).toBe(
    boundedDocumentHeightAtMobileBaseline,
  );
  expect(responsiveLayout.root.bottom - responsiveLayout.root.top).toBe(844);
  expect(responsiveLayout.transcript.scrollHeight).toBeGreaterThan(
    responsiveLayout.transcript.clientHeight,
  );
  expect(responsiveLayout.discussion.overflowY).toBe("hidden");
  expect(responsiveLayout.centerLongScrollOwners).toEqual([
    "confirmed-transcript-list",
  ]);
  expect(responsiveLayout.composer.bottom).toBeLessThanOrEqual(844);
  await page.getByRole("tab", { name: "题目" }).click();
  await page
    .getByRole("textbox", { name: "我的思路 / 私人笔记" })
    .fill(PRIVATE_NOTES);
  await page.getByRole("tab", { name: "进程" }).click();
  await page.getByRole("tab", { name: "讨论" }).click();
  await expect(discussionSurface).toBeVisible();
  expect(authoritativeReadCount).toBe(readsBeforeLongResponsiveSwitching);
  expect(workspaceWebSocketCount).toBe(socketsBeforeLongResponsiveSwitching);
  await captureResponsiveEvidence("r2a-long-mobile-390x844");
  await page.setViewportSize({ height: 900, width: 1440 });

  await page.reload();
  await expect.poll(exactConfirmedContributionCount).toBe(1);
  await expect(confirmedAiUtterance).toHaveText(AI_CONTRIBUTION, {
    useInnerText: false,
  });
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
  await expect(confirmedAiUtterance).toHaveText(AI_CONTRIBUTION, {
    useInnerText: false,
  });

  await expect
    .poll(
      () =>
        lifecycleEvents.some((event) => {
          const parsed = JSON.parse(event);
          return (
            parsed.type === "session.state_changed" &&
            parsed.payload?.status === "EXPLORATION"
          );
        }),
      { timeout: 25_000 },
    )
    .toBe(true);
  await expect
    .poll(
      () =>
        lifecycleEvents.some((event) => {
          const parsed = JSON.parse(event);
          return (
            parsed.type === "floor.granted" &&
            parsed.payload?.phase === "EXPLORATION"
          );
        }),
      { timeout: 10_000 },
    )
    .toBe(true);
  const parsedLifecycleEvents = lifecycleEvents.map((event) =>
    JSON.parse(event),
  );
  const explorationTransitionIndex = parsedLifecycleEvents.findIndex(
    (event) =>
      event.type === "session.state_changed" &&
      event.payload?.status === "EXPLORATION",
  );
  const explorationGrantIndex = parsedLifecycleEvents.findIndex(
    (event) =>
      event.type === "floor.granted" && event.payload?.phase === "EXPLORATION",
  );
  expect(explorationTransitionIndex).toBeGreaterThanOrEqual(0);
  expect(explorationGrantIndex).toBeGreaterThan(explorationTransitionIndex);
  expect(parsedLifecycleEvents[explorationGrantIndex].sequence).toBeGreaterThan(
    parsedLifecycleEvents[explorationTransitionIndex].sequence,
  );

  await expect(page.getByText("已完成", { exact: true }).first()).toBeVisible({
    timeout: 100_000,
  });
  await expect(
    page.getByText("讨论已完成", { exact: true }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("正在安排下一位发言者", { exact: true }),
  ).toHaveCount(0);
  await expect.poll(exactConfirmedContributionCount).toBe(1);
  const completedLifecycle = lifecycleEvents
    .map((event) => JSON.parse(event))
    .filter((event) => event.type === "session.state_changed")
    .map((event) => event.payload?.status as string)
    .filter((status, index, statuses) => statuses.indexOf(status) === index);
  expect(completedLifecycle).toEqual([
    "PREPARATION",
    "OPENING_STATEMENTS",
    "EXPLORATION",
    "CONFLICT_AND_EVALUATION",
    "CONVERGENCE",
    "FINAL_SUMMARY",
    "COMPLETED",
  ]);
  expect(
    floorReleaseEvents.filter((rawEvent) => {
      const event = JSON.parse(rawEvent);
      return (
        event.payload?.grant_id === runningProviderState.floor_grant_id &&
        event.payload?.reason_code === "INTERRUPTED"
      );
    }),
  ).toHaveLength(1);
  expect(
    aiCreatedEvents.filter(
      (rawEvent) =>
        JSON.parse(rawEvent).payload?.floor_grant_id ===
        runningProviderState.floor_grant_id,
    ),
  ).toHaveLength(0);

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
  expect(finalSequence).toBeGreaterThan(parsedAiEvent.sequence);
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
  await expect(confirmedAiUtterance).toHaveText(AI_CONTRIBUTION, {
    useInnerText: false,
  });
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
