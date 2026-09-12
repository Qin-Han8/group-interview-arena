import { expect, test, type Page } from "@playwright/test";

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

test("owner generates from completed session, reloads report, and another user receives nondisclosing not-found", async ({
  browser,
  page,
}) => {
  expect(sessionId).toBeTruthy();
  expect(ownerUsername).toBeTruthy();
  expect(otherUsername).toBeTruthy();
  expect(password).toBeTruthy();
  await login(page, ownerUsername!);

  await page.goto("/?session_id=" + sessionId);
  await page.getByRole("button", { name: "生成 / 查看训练报告" }).click();
  await expect(page).toHaveURL("/sessions/" + sessionId + "/report");
  await expect(page.getByRole("heading", { name: "训练报告" })).toBeVisible();
  await expect(
    page.getByText(
      "The report is derived from authoritative public discussion history.",
    ),
  ).toBeVisible();
  await expect(page.getByText(/发言事件 #2/)).toBeVisible();
  const quote = page.locator("blockquote").first();
  await expect(quote).toBeVisible();
  expect(await quote.textContent()).toBe("  exact opening source\n");

  await page.reload();
  await expect(page.getByRole("heading", { name: "训练报告" })).toBeVisible();
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
});
