import { expect, test } from "@playwright/test";
import { access, writeFile } from "node:fs/promises";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const PRIVATE_SENTINEL = "P1_2C_PRIVATE_SENTINEL_DO_NOT_DISCLOSE";
const API_RESTART_REQUEST = process.env.GIA_E2E_API_RESTART_REQUEST;
const API_RESTART_READY = process.env.GIA_E2E_API_RESTART_READY;
const FLOOR_REQUEST = process.env.GIA_E2E_FLOOR_REQUEST;
const FLOOR_READY = process.env.GIA_E2E_FLOOR_READY;

test("browser session recovers durable phases across API restart and reload", async ({
  page,
}) => {
  const username = `P11D_${Date.now().toString(36)}`;
  const password = `P1-1D browser ${crypto.randomUUID()} phrase`;
  let startCommand: string | undefined;
  let floorEvent: string | undefined;

  page.on("websocket", (socket) => {
    socket.on("framesent", ({ payload }) => {
      if (typeof payload === "string" && payload.includes("session.start")) {
        startCommand = payload;
      }
    });
    socket.on("framereceived", ({ payload }) => {
      if (typeof payload === "string" && payload.includes("floor.granted")) {
        floorEvent = payload;
      }
    });
  });

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

  await expect(page.getByText("实时连接已建立")).toBeVisible();
  await expect(page.getByText("已创建")).toBeVisible();
  await expect(page.getByTestId("session-sequence")).toHaveText("1");
  await expect(page.getByTestId("question-version-id")).toContainText(
    questionVersionId,
  );
  await expect(
    page.getByText("内部工程验证题：团队需要在有限资源下安排三类社区活动。"),
  ).toBeVisible();
  await expect(
    page.getByText("形成满足硬约束、说明取舍且可执行的资源安排。"),
  ).toBeVisible();
  const sessionId = (
    (await page.getByTestId("session-id").textContent()) ?? ""
  ).replace("会话 ID：", "");
  expect(sessionId).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  expect(new URL(page.url()).searchParams.get("session_id")).toBe(sessionId);

  await page.getByRole("button", { name: "开始讨论" }).click();
  await expect(page.getByText("进行中")).toBeVisible();
  await expect(page.getByTestId("phase-label")).toContainText("准备");
  await expect(page.getByTestId("session-sequence")).toHaveText("2");
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

  await expect(page.getByTestId("phase-label")).toContainText("个人陈述", {
    timeout: 10_000,
  });
  await expect(page.getByTestId("session-sequence")).toHaveText("3");
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
  await expect(page.getByTestId("session-sequence")).toHaveText("4");
  await expect(page.getByTestId("floor-owner")).toContainText(
    "你（真人参与者）",
  );
  await expect(page.getByTestId("floor-lifecycle")).toHaveText("发言权已授予");
  await expect(page.getByTestId("floor-reason")).toContainText(
    "优先安排尚未发言的参与者",
  );
  await expect.poll(() => floorEvent).toBeTruthy();
  const parsedFloorEvent = JSON.parse(floorEvent ?? "{}");
  expect(parsedFloorEvent).toMatchObject({
    schema_version: 1,
    type: "floor.granted",
    session_id: sessionId,
    sequence: 4,
    payload: {
      phase: "OPENING_STATEMENTS",
      reason_code: "FIRST_OPPORTUNITY",
    },
  });
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

  await page.reload();
  await expect(page.getByTestId("session-sequence")).toHaveText("4");
  await expect(page.getByTestId("floor-owner")).toContainText(
    "你（真人参与者）",
  );
  await expect(page.getByTestId("floor-lifecycle")).toHaveText("发言权已授予");
  await expect(page.getByText("实时连接已建立")).toBeVisible();

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
  await expect(page.getByText("实时连接已建立")).toBeVisible({
    timeout: 10_000,
  });
  await expect(page.getByTestId("session-sequence")).toHaveText("4");
  await expect(page.getByTestId("floor-owner")).toContainText(
    "你（真人参与者）",
  );

  await expect(
    page.locator("p").filter({ hasText: "会话状态：" }),
  ).toContainText("已完成", { timeout: 25_000 });
  await expect(page.getByTestId("phase-label")).toContainText("已完成");
  await expect(page.getByTestId("session-sequence")).toHaveText("10");
  await expect(page.getByTestId("floor-owner")).toContainText("暂无");
  await expect(page.getByTestId("floor-lifecycle")).toHaveText("发言权已释放");

  const duplicate = await page.evaluate(
    ({ apiBaseUrl, command, session }) =>
      new Promise<Record<string, unknown>>((resolve, reject) => {
        const socketUrl = new URL(apiBaseUrl);
        socketUrl.protocol = socketUrl.protocol === "https:" ? "wss:" : "ws:";
        socketUrl.pathname = `/ws/sessions/${session}`;
        socketUrl.search = "after_sequence=10";
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
    { apiBaseUrl: API_BASE_URL, command: startCommand!, session: sessionId },
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
      last_sequence: 10,
      floor: {
        current_grant: null,
        latest_event: {
          type: "floor.released",
          sequence: 5,
          phase: "OPENING_STATEMENTS",
          reason_code: "PHASE_CHANGED",
        },
      },
    },
  });
  expect(JSON.stringify(authoritative)).not.toContain(PRIVATE_SENTINEL);
  expect(await page.locator("body").textContent()).not.toContain(
    PRIVATE_SENTINEL,
  );

  const browserStorage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
  }));
  expect(browserStorage).toEqual({ local: [], session: [] });
  expect(JSON.stringify(browserStorage)).not.toContain(parsedCommand.action_id);
  expect(JSON.stringify(browserStorage)).not.toContain(sessionId);

  await page.reload();
  await expect(page.getByTestId("current-username")).toHaveText(
    username.toLowerCase(),
  );
  await expect(
    page.locator("p").filter({ hasText: "会话状态：" }),
  ).toContainText("已完成");
  await expect(page.getByTestId("session-sequence")).toHaveText("10");
  await expect(page.getByTestId("floor-owner")).toContainText("暂无");
  await expect(page.getByTestId("floor-lifecycle")).toHaveText("发言权已释放");
  await expect(page.getByTestId("question-version-id")).toContainText(
    questionVersionId,
  );
  await expect(
    page.getByText("内部工程验证题：团队需要在有限资源下安排三类社区活动。"),
  ).toBeVisible();
  await expect(page.getByText("实时连接已建立")).toBeVisible();
});
