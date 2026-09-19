import {
  expect,
  test,
  type Page,
  type Request,
  type TestInfo,
} from "@playwright/test";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const SESSION_COOKIE_NAME = "gia_session";
const VISUAL_VIEWPORTS = [
  { height: 900, label: "1440x900", width: 1440 },
  { height: 1024, label: "768x1024", width: 768 },
  { height: 844, label: "390x844", width: 390 },
] as const;

async function captureEvidence(page: Page, testInfo: TestInfo, name: string) {
  const screenshotPath = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path: screenshotPath });
  await testInfo.attach(name, {
    contentType: "image/png",
    path: screenshotPath,
  });
}

async function captureTask2Surface(
  page: Page,
  testInfo: TestInfo,
  surface: "entry" | "shell",
) {
  for (const viewport of VISUAL_VIEWPORTS) {
    await page.setViewportSize({
      height: viewport.height,
      width: viewport.width,
    });
    await page.evaluate(() => document.fonts.ready.then(() => true));
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const name = `f010-task2-${surface}-${viewport.label}`;
    await captureEvidence(page, testInfo, name);
    if (surface === "entry") {
      await captureEvidence(
        page,
        testInfo,
        `f010-final-entry-${viewport.label}`,
      );
    }
  }
}

async function captureTask3Surface(
  page: Page,
  testInfo: TestInfo,
  surface: "lobby" | "setup",
) {
  for (const viewport of VISUAL_VIEWPORTS) {
    await page.setViewportSize({
      height: viewport.height,
      width: viewport.width,
    });
    await page.evaluate(() => document.fonts.ready.then(() => true));
    await page.evaluate(() => {
      window.scrollTo(0, 0);
      document
        .querySelector<HTMLElement>('[data-testid="training-entry"]')
        ?.scrollTo(0, 0);
    });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const name = `f010-task3-${surface}-${viewport.label}`;
    await captureEvidence(page, testInfo, name);
    await captureEvidence(
      page,
      testInfo,
      `f010-final-${surface}-${viewport.label}`,
    );
  }
}

async function captureTask8Settings(page: Page, testInfo: TestInfo) {
  for (const viewport of VISUAL_VIEWPORTS) {
    await page.setViewportSize({
      height: viewport.height,
      width: viewport.width,
    });
    await page.evaluate(() => document.fonts.ready.then(() => true));
    await page.evaluate(() => window.scrollTo(0, 0));
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const name = `f010-task8-settings-${viewport.label}`;
    await captureEvidence(page, testInfo, name);
    await captureEvidence(
      page,
      testInfo,
      `f010-final-settings-${viewport.label}`,
    );
  }
}

async function captureTask8State(
  page: Page,
  testInfo: TestInfo,
  state: "custom-layout-state" | "default-after-reset",
) {
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.evaluate(() => document.fonts.ready.then(() => true));
  const name = `f010-task8-settings-${state}-1440x900`;
  await captureEvidence(page, testInfo, name);
  await captureEvidence(
    page,
    testInfo,
    `f010-final-settings-${state}-1440x900`,
  );
}

test("browser auth round trip preserves and clears the opaque session", async ({
  context,
  page,
}, testInfo) => {
  const rawUsername = `E2E_${Date.now().toString(36)}`;
  const canonicalUsername = rawUsername.toLowerCase();
  const password = "Abcd123!";

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();
  await expect(page.getByText("API 状态：已连接")).toBeVisible();
  await captureTask2Surface(page, testInfo, "entry");

  await page.setViewportSize({ height: 900, width: 1440 });
  await page.getByRole("button", { name: "注册" }).click();
  await expect(
    page.getByText(
      "密码需为 8–128 位，并同时包含大写英文字母、小写英文字母、数字和符号。",
    ),
  ).toBeVisible();
  await page.getByLabel("用户名").fill(rawUsername);
  let invalidRegistrationRequests = 0;
  const countInvalidRegistrationRequest = (request: Request) => {
    if (request.url() === `${API_BASE_URL}/auth/register`) {
      invalidRegistrationRequests += 1;
    }
  };
  page.on("request", countInvalidRegistrationRequest);
  for (const invalidPassword of [
    "Ab1!xyz",
    "abcdef1!",
    "ABCDEF1!",
    "Abcdefg!",
    "Abcdefg1",
    "Abcd123 ",
    "Abcd123。",
  ]) {
    await page.getByLabel("密码").fill(invalidPassword);
    await page.getByRole("button", { name: "创建账户" }).click();
    await expect(page.getByLabel("密码")).toHaveAttribute(
      "aria-invalid",
      "true",
    );
    expect(invalidRegistrationRequests).toBe(0);
  }
  page.off("request", countInvalidRegistrationRequest);
  await page.getByLabel("密码").fill(password);

  const registerResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === `${API_BASE_URL}/auth/register` &&
      response.request().method() === "POST",
  );
  await page.getByRole("button", { name: "创建账户" }).click();
  const registerResponse = await registerResponsePromise;

  expect(registerResponse.status()).toBe(201);
  expect(registerResponse.headers()["access-control-allow-origin"]).toBe(
    "http://localhost:3000",
  );
  expect(registerResponse.headers()["access-control-allow-credentials"]).toBe(
    "true",
  );
  expect((await registerResponse.request().allHeaders())["x-gia-csrf"]).toBe(
    "1",
  );
  await expect(page.getByTestId("current-username")).toHaveText(
    canonicalUsername,
  );
  await expect(
    page.getByRole("heading", { level: 1, name: "训练大厅" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "一次完整的群面练习" }),
  ).toBeVisible();
  await captureTask2Surface(page, testInfo, "shell");
  await captureTask3Surface(page, testInfo, "lobby");
  await page.setViewportSize({ height: 360, width: 1100 });
  await captureEvidence(page, testInfo, "f010-final-lobby-1100x360");
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.evaluate(() => {
    document.body.style.zoom = "1.25";
  });
  await expect(page.getByRole("button", { name: "开始选题" })).toBeVisible();
  await captureEvidence(
    page,
    testInfo,
    "f010-final-productshell-125-percent-1440x900",
  );
  await page.evaluate(() => {
    document.body.style.zoom = "";
  });

  await page.evaluate(() => {
    localStorage.setItem("unrelated.preference", "keep-me");
    localStorage.setItem(
      "gia.training.workspace.layout",
      JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
    );
  });
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.getByRole("button", { name: "设置" }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "设置" }),
  ).toBeVisible();
  await expect(page.getByTestId("current-username")).toHaveText(
    canonicalUsername,
  );
  await expect(page.getByText("已保存自定义布局")).toBeVisible();
  await expect(
    page.getByText("题目与思考：356px · 训练进程：336px", { exact: true }),
  ).toBeVisible();
  await captureTask8State(page, testInfo, "custom-layout-state");

  await page.getByRole("tab", { name: "账户与会话" }).click();
  await expect(
    page.getByRole("tabpanel").getByText(canonicalUsername),
  ).toBeVisible();
  await page.getByRole("tab", { name: "隐私与数据" }).click();
  await expect(page.getByText(/只保留在当前页面内存/)).toBeVisible();
  await page.getByRole("tab", { name: "更多设置" }).click();
  await expect(page.getByText("声音与设备")).toBeVisible();
  await expect(page.getByRole("switch")).toHaveCount(0);
  await page.getByRole("tab", { name: "训练界面" }).click();

  await page.getByRole("button", { name: "恢复默认布局" }).click();
  await expect(page.getByText("默认布局", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "恢复默认布局" }),
  ).toBeDisabled();
  expect(
    await page.evaluate(() => ({
      layout: localStorage.getItem("gia.training.workspace.layout"),
      unrelated: localStorage.getItem("unrelated.preference"),
    })),
  ).toEqual({ layout: null, unrelated: "keep-me" });
  await captureTask8State(page, testInfo, "default-after-reset");
  await captureTask8Settings(page, testInfo);

  await page.getByRole("button", { name: "完整模拟" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.getByRole("button", { name: "开始选题" }).click();
  await expect(
    page.getByRole("heading", { name: "选择本次训练题目" }),
  ).toBeVisible();
  for (const category of ["排序选择型", "资源分配型", "方案策划型"]) {
    await page.getByRole("tab", { name: `${category} 4 道` }).click();
    await expect(page.getByRole("radio")).toHaveCount(4);
  }
  await page.getByRole("tab", { name: "排序选择型 4 道" }).click();
  await page.getByRole("radio").first().focus();
  await page.getByRole("radio").first().press("Space");
  await expect(page.getByRole("heading", { name: "讨论目标" })).toBeVisible();
  await page.getByRole("heading", { name: "已选题目" }).click();
  await captureTask3Surface(page, testInfo, "setup");
  await page.setViewportSize({ height: 900, width: 1440 });
  await page.getByRole("button", { name: "创建文字会话" }).click();
  await expect(
    page.locator('[data-presentation-mode="focused-training"]'),
  ).toBeVisible();
  const leftSeparator = page.getByRole("separator", {
    name: "调整题目与思考面板宽度",
  });
  const rightSeparator = page.getByRole("separator", {
    name: "调整训练进程面板宽度",
  });
  await expect(leftSeparator).toHaveAttribute("aria-valuenow", "280");
  await expect(rightSeparator).toHaveAttribute("aria-valuenow", "280");
  await captureEvidence(
    page,
    testInfo,
    "f010-final-layout-next-session-default-after-settings-reset",
  );
  await page.getByRole("button", { name: "结束会话" }).click();
  await expect(
    page.getByRole("navigation", { name: "桌面主导航" }),
  ).toBeVisible();

  const sessionCookie = (await context.cookies()).find(
    (cookie) => cookie.name === SESSION_COOKIE_NAME,
  );
  expect(sessionCookie).toBeDefined();
  if (!sessionCookie) {
    throw new Error("Expected the opaque session Cookie to exist.");
  }
  expect(sessionCookie?.httpOnly).toBe(true);
  expect(sessionCookie?.secure).toBe(false);
  expect(sessionCookie?.sameSite).toBe("Lax");
  expect(sessionCookie?.path).toBe("/");
  expect(sessionCookie?.domain).toBe("localhost");
  expect(await page.evaluate(() => document.cookie)).not.toContain(
    SESSION_COOKIE_NAME,
  );

  await page.reload();
  await expect(page.getByTestId("current-username")).toHaveText(
    canonicalUsername,
  );

  const rejected = await page.evaluate(async (apiBaseUrl) => {
    const response = await fetch(`${apiBaseUrl}/auth/logout`, {
      method: "POST",
      credentials: "include",
    });
    return { status: response.status, body: await response.json() };
  }, API_BASE_URL);
  expect(rejected.status).toBe(403);
  expect(rejected.body.error.code).toBe("CSRF_REJECTED");
  await expect(page.getByTestId("current-username")).toHaveText(
    canonicalUsername,
  );

  const browserStorage = await page.evaluate(() => ({
    local: Object.entries(localStorage),
    session: Object.entries(sessionStorage),
  }));
  const serializedBrowserStorage = JSON.stringify(browserStorage);
  expect({
    passwordPersisted: serializedBrowserStorage.includes(password),
    sessionTokenPersisted: serializedBrowserStorage.includes(
      sessionCookie.value,
    ),
  }).toEqual({
    passwordPersisted: false,
    sessionTokenPersisted: false,
  });

  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();

  const meStatus = await page.evaluate(async (apiBaseUrl) => {
    const response = await fetch(`${apiBaseUrl}/auth/me`, {
      credentials: "include",
    });
    return response.status;
  }, API_BASE_URL);
  expect(meStatus).toBe(401);
  expect(
    (await context.cookies()).some(
      (cookie) => cookie.name === SESSION_COOKIE_NAME,
    ),
  ).toBe(false);

  await page
    .getByLabel("认证方式")
    .getByRole("button", { name: "登录" })
    .click();
  await page.getByLabel("用户名").fill(canonicalUsername);
  await page.getByLabel("密码").fill(password);
  const loginResponsePromise = page.waitForResponse(
    (response) =>
      response.url() === `${API_BASE_URL}/auth/login` &&
      response.request().method() === "POST",
  );
  await page
    .getByRole("form", { name: "登录账户" })
    .getByRole("button", { name: "登录" })
    .click();
  expect((await loginResponsePromise).status()).toBe(200);
  await expect(page.getByTestId("current-username")).toHaveText(
    canonicalUsername,
  );
  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();
});

test("settings center remains usable across desktop, tablet, and mobile", async ({
  page,
}, testInfo) => {
  const settingsUser = {
    id: "00000000-0000-4000-8000-000000000081",
    username: "settings_visual_user",
  };
  await page.route(`${API_BASE_URL}/auth/me`, async (route) => {
    await route.fulfill({
      body: JSON.stringify(settingsUser),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.addInitScript(() => {
    try {
      localStorage.setItem("unrelated.preference", "keep-me");
      localStorage.setItem(
        "gia.training.workspace.layout",
        JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
      );
    } catch {
      // Non-HTTP documents do not expose localStorage; the app document does.
    }
  });

  await page.setViewportSize({ height: 900, width: 1440 });
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { level: 1, name: "设置" }),
  ).toBeVisible();
  await expect(page.getByTestId("current-username")).toHaveText(
    settingsUser.username,
  );
  await expect(page.getByText("已保存自定义布局")).toBeVisible();
  await expect(
    page.getByText("题目与思考：356px · 训练进程：336px", { exact: true }),
  ).toBeVisible();
  await captureTask8State(page, testInfo, "custom-layout-state");

  for (const section of ["账户与会话", "隐私与数据", "更多设置"]) {
    await page.getByRole("tab", { name: section }).click();
    await expect(page.getByRole("tabpanel")).toBeVisible();
  }
  await expect(page.getByText("声音与设备")).toBeVisible();
  await expect(page.getByRole("switch")).toHaveCount(0);
  await expect(page.getByRole("checkbox")).toHaveCount(0);
  await page.getByRole("tab", { name: "隐私与数据" }).click();
  await expect(page.getByText(/只保留在当前页面内存/)).toBeVisible();
  await page.getByRole("tab", { name: "训练界面" }).click();

  await page.getByRole("button", { name: "恢复默认布局" }).click();
  await expect(page.getByText("默认布局", { exact: true })).toBeVisible();
  await expect(
    page.getByRole("button", { name: "恢复默认布局" }),
  ).toBeDisabled();
  expect(
    await page.evaluate(() => ({
      layout: localStorage.getItem("gia.training.workspace.layout"),
      unrelated: localStorage.getItem("unrelated.preference"),
    })),
  ).toEqual({ layout: null, unrelated: "keep-me" });
  await captureTask8State(page, testInfo, "default-after-reset");
  await captureTask8Settings(page, testInfo);
});

test("short and constrained lobby viewports keep all training controls reachable", async ({
  page,
}) => {
  const user = {
    id: "00000000-0000-4000-8000-000000000061",
    username: "short_viewport_user",
  };
  const question = {
    id: "21000000-0000-4000-8000-000000000001",
    question_template_id: "20000000-0000-4000-8000-000000000001",
    version_number: 1,
    title: "短视口可达性验证题",
    question_type: "RESOURCE_ALLOCATION",
    background_domain: "GENERAL",
    difficulty: "STANDARD",
    estimated_minutes: 25,
  };
  await page.route(`${API_BASE_URL}/auth/me`, async (route) => {
    await route.fulfill({
      body: JSON.stringify({
        error: {
          code: "AUTHENTICATION_REQUIRED",
          message: "Authentication is required.",
          request_id: "00000000-0000-4000-8000-000000000062",
        },
      }),
      contentType: "application/json",
      status: 401,
    });
  });
  await page.route(`${API_BASE_URL}/auth/register`, async (route) => {
    await route.fulfill({
      body: JSON.stringify(user),
      contentType: "application/json",
      status: 201,
    });
  });
  await page.route(`${API_BASE_URL}/questions`, async (route) => {
    await route.fulfill({
      body: JSON.stringify([question]),
      contentType: "application/json",
      status: 200,
    });
  });

  await page.setViewportSize({ height: 360, width: 1100 });
  await page.goto("/");
  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill("short_viewport_user");
  await page.getByLabel("密码").fill("Short viewport browser 1!");
  await page.getByRole("button", { name: "创建账户" }).click();

  const lobby = page.getByTestId("training-entry");
  const beginSelection = page.getByRole("button", { name: "开始选题" });
  const trainingMethod = page.getByRole("heading", {
    name: "一次完整的群面练习",
  });
  await expect(beginSelection).toBeVisible();
  await expect(lobby).toBeVisible();
  expect(
    await lobby.evaluate((element) => ({
      clientHeight: element.clientHeight,
      overflowY: getComputedStyle(element).overflowY,
      scrollHeight: element.scrollHeight,
    })),
  ).toMatchObject({ overflowY: "auto" });
  expect(
    await lobby.evaluate((element) => element.scrollHeight),
  ).toBeGreaterThan(await lobby.evaluate((element) => element.clientHeight));

  for (const target of [beginSelection, trainingMethod]) {
    await target.scrollIntoViewIfNeeded();
    await expect(target).toBeInViewport();
  }

  await beginSelection.click();
  const selector = page.getByRole("radio", { name: question.title });
  await selector.focus();
  await selector.press("Space");
  const selectorCard = selector.locator("xpath=..");
  const creation = page.getByRole("button", { name: "创建文字会话" });

  for (const target of [selectorCard, creation]) {
    await target.scrollIntoViewIfNeeded();
    await expect(target).toBeInViewport();
  }

  await page.evaluate(() => {
    document.body.style.zoom = "1.25";
  });
  for (const target of [selectorCard, creation]) {
    await target.scrollIntoViewIfNeeded();
    await expect(target).toBeInViewport();
  }
});
