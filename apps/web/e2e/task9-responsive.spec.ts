import { expect, test, type Page, type TestInfo } from "@playwright/test";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const SESSION_ID = "00000000-0000-4000-8000-000000000091";
const QUESTION_ID = "21000000-0000-4000-8000-000000000091";
const USER = {
  id: "00000000-0000-4000-8000-000000000090",
  username: "task9_responsive_user",
};

const browserDiagnostics = new WeakMap<Page, string[]>();

test.beforeEach(async ({ page }) => {
  const diagnostics: string[] = [];
  browserDiagnostics.set(page, diagnostics);
  page.on("console", (message) => {
    if (message.type() === "error" || message.type() === "warning") {
      diagnostics.push(`console.${message.type()}: ${message.text()}`);
    }
  });
  page.on("pageerror", (error) =>
    diagnostics.push(`pageerror: ${error.message}`),
  );
});

test.afterEach(async ({ page }) => {
  expect(browserDiagnostics.get(page)).toEqual([]);
  await expect(page.locator("nextjs-portal")).toHaveCount(0);
});

const QUESTION_TYPES = [
  "ORDERING_SELECTION",
  "RESOURCE_ALLOCATION",
  "PLAN_DESIGN",
] as const;

const QUESTIONS = QUESTION_TYPES.flatMap((questionType, typeIndex) =>
  Array.from({ length: 4 }, (_, index) => ({
    id: `21000000-0000-4000-8${typeIndex}00-0000000000${index + 1}`,
    question_template_id: `20000000-0000-4000-8${typeIndex}00-0000000000${index + 1}`,
    version_number: 1,
    title: `${["公共事务优先级", "社区资源安排", "校园活动方案"][typeIndex]} ${index + 1}`,
    question_type: questionType,
    background_domain: "GENERAL",
    difficulty: index % 2 === 0 ? "STANDARD" : "ADVANCED",
    estimated_minutes: 25,
  })),
);

const QUESTION_DETAIL = {
  id: QUESTION_ID,
  question_template_id: "20000000-0000-4000-8000-000000000091",
  version_number: 1,
  title: "在非常有限的公共资源下协调多方诉求并形成可执行方案的长标题训练题",
  question_type: "RESOURCE_ALLOCATION",
  background_domain: "GENERAL",
  difficulty: "STANDARD",
  estimated_minutes: 25,
  scenario:
    "社区需要在有限预算与志愿者资源下，同时安排儿童服务、长者支持和公共文化活动。",
  objective: "形成满足硬约束、解释关键取舍且可以立即执行的资源安排。",
  hard_constraints: [
    { key: "BUDGET", text: "总预算不得超过 100 个单位。" },
    { key: "COVERAGE", text: "三类服务都必须获得基础覆盖。" },
  ],
  soft_constraints: [],
  stakeholders: [],
  options: [
    { key: "A", label: "儿童服务", description: "覆盖课后活动与安全看护。" },
    { key: "B", label: "长者支持", description: "覆盖陪诊与日常协助。" },
    { key: "C", label: "公共文化", description: "覆盖社区共创活动。" },
  ],
};

async function capture(page: Page, testInfo: TestInfo, name: string) {
  await expect(page).toHaveTitle("AI 群面训练场");
  await page.evaluate(() => document.fonts.ready.then(() => true));
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
  const path = testInfo.outputPath(`${name}.png`);
  await page.screenshot({ path });
  await testInfo.attach(name, { contentType: "image/png", path });
}

async function mockAuthenticatedUser(page: Page) {
  await page.route(`${API_BASE_URL}/auth/me`, async (route) => {
    await route.fulfill({
      body: JSON.stringify(USER),
      contentType: "application/json",
      status: 200,
    });
  });
}

async function expectProductNavigationMode(
  page: Page,
  mode: "full" | "rail" | "top",
) {
  const navigations = {
    full: page.getByRole("navigation", { name: "桌面主导航" }),
    rail: page.getByRole("navigation", { name: "精简侧边栏导航" }),
    top: page.getByRole("navigation", { name: "移动主导航" }),
  };

  await expect(navigations[mode]).toBeVisible();
  for (const [candidate, navigation] of Object.entries(navigations)) {
    if (candidate !== mode) {
      await expect(navigation).toBeHidden();
    }
  }
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);

  if (mode === "top") {
    const compactNavigation = await page
      .locator(".product-mobile-navigation")
      .boundingBox();
    expect(compactNavigation).not.toBeNull();
    expect(compactNavigation!.height).toBeLessThanOrEqual(72);
  }
}

test("Task 9 entry, lobby, setup, Settings, and ProductShell responsive matrix", async ({
  page,
}, testInfo) => {
  await page.route(`${API_BASE_URL}/auth/me`, async (route) => {
    await route.fulfill({
      body: JSON.stringify({
        error: {
          code: "AUTHENTICATION_REQUIRED",
          message: "Authentication is required.",
          request_id: "00000000-0000-4000-8000-000000000099",
        },
      }),
      contentType: "application/json",
      status: 401,
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();
  await capture(page, testInfo, "f010-task9-login-390x844");
  expect(browserDiagnostics.get(page)).toEqual([
    "console.error: Failed to load resource: the server responded with a status of 401 (Unauthorized)",
  ]);
  browserDiagnostics.set(page, []);
  await page.setViewportSize({ width: 1100, height: 360 });
  for (const control of [
    page.getByRole("button", { name: "注册" }),
    page.getByLabel("用户名"),
    page.getByLabel("密码"),
    page.getByLabel("登录账户").getByRole("button", { name: "登录" }),
  ]) {
    await control.scrollIntoViewIfNeeded();
    await expect(control).toBeInViewport();
  }
  await capture(page, testInfo, "f010-task9-login-1100x360");

  await page.unroute(`${API_BASE_URL}/auth/me`);
  await mockAuthenticatedUser(page);
  await page.route(`${API_BASE_URL}/questions`, async (route) => {
    await route.fulfill({
      body: JSON.stringify(QUESTIONS),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "下一场完整模拟" }),
  ).toBeVisible();
  await expectProductNavigationMode(page, "top");
  await capture(page, testInfo, "f010-task9-lobby-390x844");

  await page.setViewportSize({ width: 768, height: 1024 });
  await expectProductNavigationMode(page, "top");
  await capture(page, testInfo, "f010-task9-product-shell-768x1024");

  await page.setViewportSize({ width: 1440, height: 900 });
  await expectProductNavigationMode(page, "full");
  await capture(page, testInfo, "f010-navigation-full-1440x900");

  await page.setViewportSize({ width: 1280, height: 900 });
  await expectProductNavigationMode(page, "full");

  await page.setViewportSize({ width: 1200, height: 900 });
  await expectProductNavigationMode(page, "rail");
  await capture(page, testInfo, "f010-navigation-rail-1200x900");
  const lobbyRail = page.getByRole("navigation", {
    name: "精简侧边栏导航",
  });
  await expect(
    lobbyRail.getByRole("button", { name: "完整模拟" }),
  ).toHaveAttribute("aria-current", "page");
  const lobbyRailSettings = lobbyRail.getByRole("button", { name: "设置" });
  await lobbyRailSettings.focus();
  await expect(lobbyRailSettings).toBeFocused();
  await lobbyRailSettings.hover();
  await capture(
    page,
    testInfo,
    "f010-navigation-rail-hover-focus-active-1200x900",
  );

  await page.setViewportSize({ width: 1100, height: 360 });
  await expectProductNavigationMode(page, "rail");
  await capture(page, testInfo, "f010-task9-lobby-1100x360");
  const beginSelection = page.getByRole("button", { name: "开始选题" });
  await beginSelection.scrollIntoViewIfNeeded();
  await expect(beginSelection).toBeInViewport();

  await page.setViewportSize({ width: 1152, height: 720 });
  await expectProductNavigationMode(page, "rail");
  await capture(
    page,
    testInfo,
    "f010-task9-product-shell-125-percent-effective-1152x720",
  );

  await page.setViewportSize({ width: 1024, height: 768 });
  await expectProductNavigationMode(page, "rail");

  await page.setViewportSize({ width: 900, height: 768 });
  await expectProductNavigationMode(page, "top");
  await capture(page, testInfo, "f010-navigation-top-900x768");

  await beginSelection.click();
  await expect(
    page.getByRole("heading", { name: "选择本次训练题目" }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await capture(page, testInfo, "f010-task9-setup-390x844");
  await page.setViewportSize({ width: 1100, height: 360 });
  const firstQuestion = page.getByRole("radio").first();
  await firstQuestion.scrollIntoViewIfNeeded();
  await firstQuestion.focus();
  await firstQuestion.press("Space");
  await page
    .getByRole("button", { name: "创建文字会话" })
    .scrollIntoViewIfNeeded();
  await capture(page, testInfo, "f010-task9-setup-1100x360");

  await page.setViewportSize({ width: 1200, height: 900 });
  await page.goto("/settings");
  await expect(
    page.getByRole("heading", { level: 1, name: "设置" }),
  ).toBeVisible();
  await expectProductNavigationMode(page, "rail");
  await capture(page, testInfo, "f010-navigation-rail-settings-1200x900");
  const railSettings = page
    .getByRole("navigation", { name: "精简侧边栏导航" })
    .getByRole("button", { name: "设置" });
  await expect(railSettings).toHaveAttribute("aria-current", "page");

  await page.setViewportSize({ width: 390, height: 844 });
  await expectProductNavigationMode(page, "top");
  const trainingTab = page.getByRole("tab", { name: "训练界面" });
  const accountTab = page.getByRole("tab", { name: "账户与会话" });
  await trainingTab.focus();
  await trainingTab.press("ArrowRight");
  await expect(accountTab).toBeFocused();
  await expect(accountTab).toHaveAttribute("aria-selected", "true");
  await accountTab.press("Home");
  await expect(trainingTab).toBeFocused();
  await capture(page, testInfo, "f010-task9-settings-390x844");
});

test("Task 9 completed report wraps long truthful content on mobile", async ({
  page,
}, testInfo) => {
  await mockAuthenticatedUser(page);
  await page.route(
    `${API_BASE_URL}/sessions/${SESSION_ID}/report`,
    async (route) => {
      await route.fulfill({
        body: JSON.stringify({
          report: {
            report_id: "00000000-0000-4000-8000-000000000092",
            session_id: SESSION_ID,
            status: "COMPLETED",
            report_schema_version: 1,
            derivation_version: "p1-7-v1",
            source_through_sequence: 18,
            created_at: "2026-09-17T10:00:00Z",
            completed_at: "2026-09-17T10:00:02Z",
          },
          content: {
            overview: {
              session_status: "COMPLETED",
              question: QUESTION_DETAIL,
              participant_count: 4,
              human_utterance_count: 4,
              ai_utterance_count: 12,
              total_utterance_count: 16,
              covered_phases: [
                "OPENING_STATEMENTS",
                "EXPLORATION",
                "CONVERGENCE",
              ],
              summary:
                "讨论从约束澄清推进到资源取舍，并形成了能够解释优先级的共同方案。",
            },
            strengths: [
              {
                kind: "STRENGTH",
                source_participant_id: "00000000-0000-4000-8000-000000000093",
                source_utterance_id: "00000000-0000-4000-8000-000000000094",
                source_event_sequence: 8,
                phase: "EXPLORATION",
                quote:
                  "我建议先统一预算、覆盖范围与最低服务线，再比较每种安排对三类居民的实际影响。",
                interpretation: "先建立共同标准，帮助团队减少无效争论。",
                confidence: "0.930",
              },
            ],
            improvements: [
              {
                kind: "IMPROVEMENT",
                source_participant_id: "00000000-0000-4000-8000-000000000093",
                source_utterance_id: "00000000-0000-4000-8000-000000000095",
                source_event_sequence: 15,
                phase: "CONVERGENCE",
                quote:
                  "方案已经接近一致，但还可以更明确地把负责人、时间点和验收条件写入结论。",
                interpretation: "收敛阶段需要把原则性共识转化为可执行动作。",
                confidence: "0.880",
              },
            ],
            priority_improvement:
              "下一次在收敛阶段更早提出包含负责人、完成时间、资源上限和验收标准的完整行动方案，并邀请其他成员逐项确认。",
          },
        }),
        contentType: "application/json",
        status: 200,
      });
    },
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/sessions/${SESSION_ID}/report`);
  await expect(
    page.getByRole("heading", { name: "训练报告", exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("report-priority-copy")).toHaveCSS(
    "overflow-wrap",
    "anywhere",
  );
  await capture(page, testInfo, "f010-task9-report-390x844");
});

test("Task 9 focused workspace preserves controls, fallback, and scroll ownership", async ({
  page,
}, testInfo) => {
  await mockAuthenticatedUser(page);
  const now = Date.now();
  const participants = [
    ["00000000-0000-4000-8000-000000000093", "HUMAN"],
    ["00000000-0000-4000-8000-000000000094", "AI"],
    ["00000000-0000-4000-8000-000000000095", "AI"],
    ["00000000-0000-4000-8000-000000000096", "AI"],
  ].map(([participant_id, actor_kind], index) => ({
    participant_id,
    actor_kind,
    seat_order: index + 1,
  }));
  const snapshot = {
    id: SESSION_ID,
    question_version_id: QUESTION_ID,
    status: "EXPLORATION",
    phase_started_at: new Date(now - 60_000).toISOString(),
    phase_deadline_at: new Date(now + 240_000).toISOString(),
    server_now: new Date(now).toISOString(),
    created_at: new Date(now - 300_000).toISOString(),
    updated_at: new Date(now).toISOString(),
    last_sequence: 3,
    floor: {
      participants,
      current_grant: {
        grant_id: "00000000-0000-4000-8000-000000000097",
        participant_id: participants[0].participant_id,
        phase: "EXPLORATION",
        reason_code: "EXPLICIT_OPPORTUNITY",
        granted_at: new Date(now - 15_000).toISOString(),
      },
      latest_event: null,
    },
  };
  const transcript = {
    items: [
      {
        utterance_id: "00000000-0000-4000-8000-000000000098",
        sequence: 2,
        occurred_at: new Date(now - 45_000).toISOString(),
        action_id: null,
        participant_id: participants[1].participant_id,
        actor_kind: "AI",
        floor_grant_id: "00000000-0000-4000-8000-000000000089",
        phase: "EXPLORATION",
        content:
          "我们可以先确认三类服务的最低覆盖线，再比较剩余资源的边际收益。",
      },
      {
        utterance_id: "00000000-0000-4000-8000-000000000088",
        sequence: 3,
        occurred_at: new Date(now - 25_000).toISOString(),
        action_id: null,
        participant_id: participants[2].participant_id,
        actor_kind: "AI",
        floor_grant_id: "00000000-0000-4000-8000-000000000087",
        phase: "EXPLORATION",
        content: "同意，并建议把预算约束和执行负责人放进同一张方案清单。",
      },
    ],
    next_after_sequence: null,
  };

  await page.route(`${API_BASE_URL}/sessions/${SESSION_ID}`, async (route) => {
    await route.fulfill({
      body: JSON.stringify(snapshot),
      contentType: "application/json",
      status: 200,
    });
  });
  await page.route(
    `${API_BASE_URL}/sessions/${SESSION_ID}/utterances?**`,
    async (route) => {
      await route.fulfill({
        body: JSON.stringify(transcript),
        contentType: "application/json",
        status: 200,
      });
    },
  );
  await page.route(
    `${API_BASE_URL}/questions/${QUESTION_ID}`,
    async (route) => {
      await route.fulfill({
        body: JSON.stringify(QUESTION_DETAIL),
        contentType: "application/json",
        status: 200,
      });
    },
  );
  await page.routeWebSocket(/\/ws\/sessions\//, (socket) => {
    socket.onMessage(() => undefined);
  });

  await page.addInitScript(() => {
    localStorage.setItem(
      "gia.training.workspace.layout",
      JSON.stringify({ version: 1, leftWidth: 356, rightWidth: 336 }),
    );
  });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/?session_id=${SESSION_ID}`);
  await expect(
    page.locator('[data-presentation-mode="focused-training"]'),
  ).toBeVisible();
  await expect(page.getByText("连接正常").first()).toBeVisible();
  const leftSeparator = page.getByRole("separator", {
    name: "调整题目与思考面板宽度",
  });
  const rightSeparator = page.getByRole("separator", {
    name: "调整训练进程面板宽度",
  });
  await expect(leftSeparator).toHaveAttribute("aria-valuenow", "356");
  await expect(rightSeparator).toHaveAttribute("aria-valuenow", "336");
  await capture(page, testInfo, "f010-task9-focused-custom-1440x900");

  await page.setViewportSize({ width: 768, height: 1024 });
  await expect(page.getByRole("separator")).toHaveCount(0);
  await capture(page, testInfo, "f010-task9-focused-768x1024");

  await page.setViewportSize({ width: 1440, height: 900 });
  await expect(leftSeparator).toHaveAttribute("aria-valuenow", "356");
  await expect(rightSeparator).toHaveAttribute("aria-valuenow", "336");

  await page.setViewportSize({ width: 390, height: 844 });
  const discussionTab = page.getByRole("tab", { name: "讨论" });
  const taskTab = page.getByRole("tab", { name: "题目" });
  const progressTab = page.getByRole("tab", { name: "进程" });
  await expect(discussionTab).toHaveAttribute("aria-selected", "true");
  await capture(page, testInfo, "f010-task9-focused-390x844-discussion");
  await taskTab.click();
  await capture(page, testInfo, "f010-task9-focused-390x844-task");
  await progressTab.click();
  await capture(page, testInfo, "f010-task9-focused-390x844-progress");
  await discussionTab.click();

  await page.setViewportSize({ width: 1100, height: 360 });
  await expect(page.getByRole("separator")).toHaveCount(0);
  await expect(page.locator("#discussion-surface")).toBeVisible();
  const shortViewportComposer = await page
    .getByTestId("human-composer")
    .boundingBox();
  expect(shortViewportComposer).not.toBeNull();
  expect(shortViewportComposer!.y).toBeGreaterThanOrEqual(0);
  expect(
    shortViewportComposer!.y + shortViewportComposer!.height,
  ).toBeLessThanOrEqual(360);
  expect(
    await page.evaluate(() =>
      Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
      ),
    ),
  ).toBeLessThanOrEqual(361);
  await capture(page, testInfo, "f010-task9-focused-1100x360");

  await page.setViewportSize({ width: 1152, height: 720 });
  await expect(page.getByRole("separator")).toHaveCount(0);
  await capture(
    page,
    testInfo,
    "f010-task9-focused-125-percent-effective-1152x720",
  );

  expect(
    await page
      .getByTestId("studio-shell")
      .getByRole("main")
      .getAttribute("data-scroll-owner"),
  ).toBe("none");
  await expect(
    page.locator('[data-product-surface="interview-simulation-studio"]'),
  ).toHaveAttribute("data-scroll-owner", "viewport-constrained");
  await expect(page.getByTestId("confirmed-transcript-list")).toBeVisible();
  expect(
    await page.evaluate(() =>
      Math.max(
        document.body.scrollHeight,
        document.documentElement.scrollHeight,
      ),
    ),
  ).toBeLessThanOrEqual(721);
});
