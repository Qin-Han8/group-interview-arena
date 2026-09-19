import { expect, test, type Page, type TestInfo } from "@playwright/test";

const API_ORIGIN = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const sessionId = process.env.GIA_P17D_SESSION_ID;
const ownerUsername = process.env.GIA_P17D_OWNER_USERNAME;
const otherUsername = process.env.GIA_P17D_OTHER_USERNAME;
const password = process.env.GIA_P17D_PASSWORD;

async function login(page: Page, username: string) {
  const response = await page.request.post(`${API_ORIGIN}/auth/login`, {
    headers: { Origin: "http://localhost:3000", "X-GIA-CSRF": "1" },
    data: { username, password },
  });
  expect(response.status()).toBe(200);
}

async function captureReport(
  page: Page,
  testInfo: TestInfo,
  width: number,
  height: number,
) {
  await page.setViewportSize({ width, height });
  await expect(page.getByTestId("report-bento")).toBeVisible();
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth),
  ).toBeLessThanOrEqual(width);
  const name = `f010-task5-report-${width}x${height}.png`;
  const path = testInfo.outputPath(name);
  await page.screenshot({ path });
  await testInfo.attach(name, { path, contentType: "image/png" });
  const finalName = `f010-final-report-${width}x${height}.png`;
  const finalPath = testInfo.outputPath(finalName);
  await page.screenshot({ path: finalPath });
  await testInfo.attach(finalName, {
    path: finalPath,
    contentType: "image/png",
  });
}

test("owner generates from completed session, reloads report, and another user receives nondisclosing not-found", async ({
  browser,
  page,
}, testInfo) => {
  expect(sessionId).toBeTruthy();
  expect(ownerUsername).toBeTruthy();
  expect(otherUsername).toBeTruthy();
  expect(password).toBeTruthy();
  await login(page, ownerUsername!);

  await page.goto("/?session_id=" + sessionId);
  await page
    .getByRole("button", {
      name: "训练报告 · 生成 / 查看本次训练报告",
    })
    .first()
    .click();
  await expect(page).toHaveURL("/sessions/" + sessionId + "/report");
  await expect(
    page.getByRole("heading", { name: "训练报告", exact: true }),
  ).toBeVisible();
  await expect(page.getByTestId("studio-shell")).toBeVisible();
  await expect(
    page
      .getByRole("navigation", { name: "桌面主导航" })
      .getByRole("button", { name: /训练报告/ }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    page.getByText(
      "The report is derived from authoritative public discussion history.",
    ),
  ).toBeVisible();
  await expect(page.getByText(/发言事件 #2/)).toBeVisible();
  const quote = page.locator("blockquote").first();
  await expect(quote).toBeVisible();
  expect(await quote.textContent()).toBe("  exact opening source\n");
  await expect(page.getByTestId("report-overview")).toHaveAttribute(
    "data-report-span",
    "8",
  );
  await expect(page.getByTestId("report-priority")).toHaveAttribute(
    "data-report-span",
    "4",
  );
  await expect(page.getByTestId("report-strengths")).toHaveAttribute(
    "data-report-span",
    "6",
  );
  await expect(page.getByTestId("report-improvements")).toHaveAttribute(
    "data-report-span",
    "6",
  );
  await expect(page.locator("body")).not.toContainText(
    /总分|六维|雷达|排名|录用概率|岗位匹配|成长趋势|推荐专项训练/,
  );

  for (const [width, height] of [
    [1440, 900],
    [768, 1024],
    [390, 844],
  ] as const) {
    await captureReport(page, testInfo, width, height);
  }

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "训练报告", exact: true }),
  ).toBeVisible();
  expect(await page.locator("blockquote").first().textContent()).toBe(
    "  exact opening source\n",
  );

  const otherContext = await browser.newContext();
  try {
    const otherPage = await otherContext.newPage();
    await login(otherPage, otherUsername!);
    await otherPage.goto(`/sessions/${sessionId}/report`);
    await expect(otherPage.getByText("未找到可查看的训练报告")).toBeVisible();
    await expect(
      otherPage.getByText(
        "The report is derived from authoritative public discussion history.",
      ),
    ).toHaveCount(0);
  } finally {
    await otherContext.close();
  }

  await page.getByRole("button", { name: "退出登录" }).click();
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();
});
