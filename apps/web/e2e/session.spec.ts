import { expect, test } from "@playwright/test";

const API_BASE_URL = "http://localhost:8000";

test("browser session uses durable ordered WebSocket events and REST reload", async ({
  page,
}) => {
  const username = `P11D_${Date.now().toString(36)}`;
  const password = `P1-1D browser ${crypto.randomUUID()} phrase`;
  let abortCommand: string | undefined;

  page.on("websocket", (socket) => {
    socket.on("framesent", ({ payload }) => {
      if (typeof payload === "string" && payload.includes("session.abort")) {
        abortCommand = payload;
      }
    });
  });

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
  expect((await createResponse.request().allHeaders())["x-gia-csrf"]).toBe("1");

  await expect(page.getByText("实时连接已建立")).toBeVisible();
  await expect(page.getByText("已创建")).toBeVisible();
  await expect(page.getByTestId("session-sequence")).toHaveText("1");
  const sessionId = (
    (await page.getByTestId("session-id").textContent()) ?? ""
  ).replace("会话 ID：", "");
  expect(sessionId).toMatch(
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
  );
  expect(new URL(page.url()).searchParams.get("session_id")).toBe(sessionId);

  await page.getByRole("button", { name: "结束会话" }).click();
  await expect(page.getByText("已由用户结束")).toBeVisible();
  await expect(page.getByTestId("session-sequence")).toHaveText("2");
  await expect.poll(() => abortCommand).toBeTruthy();
  const parsedCommand = JSON.parse(abortCommand ?? "{}");
  expect(parsedCommand).toEqual({
    schema_version: 1,
    type: "session.abort",
    session_id: sessionId,
    action_id: expect.stringMatching(
      /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/,
    ),
    payload: {},
  });

  const duplicate = await page.evaluate(
    ({ command, session }) =>
      new Promise<Record<string, unknown>>((resolve, reject) => {
        const socket = new WebSocket(
          `ws://localhost:8000/ws/sessions/${session}?after_sequence=2`,
        );
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
    { command: abortCommand!, session: sessionId },
  );
  expect(duplicate).toMatchObject({
    type: "session.state_changed",
    session_id: sessionId,
    sequence: 2,
    action_id: parsedCommand.action_id,
    payload: { previous_status: "CREATED", status: "ABORTED_USER" },
  });

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
    body: { id: sessionId, status: "ABORTED_USER", last_sequence: 2 },
  });

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
  await expect(page.getByText("已由用户结束")).toBeVisible();
  await expect(page.getByTestId("session-sequence")).toHaveText("2");
  await expect(page.getByText("实时连接已建立")).toBeVisible();
});
