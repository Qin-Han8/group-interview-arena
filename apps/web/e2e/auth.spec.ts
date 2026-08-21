import { expect, test } from "@playwright/test";

const API_BASE_URL = process.env.GIA_E2E_API_ORIGIN ?? "http://localhost:8000";
const SESSION_COOKIE_NAME = "gia_session";

test("browser auth round trip preserves and clears the opaque session", async ({
  context,
  page,
}) => {
  const rawUsername = `E2E_${Date.now().toString(36)}`;
  const canonicalUsername = rawUsername.toLowerCase();
  const password = `P0-5D browser ${crypto.randomUUID()} phrase`;

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "登录或注册" })).toBeVisible();

  await page.getByRole("button", { name: "注册" }).click();
  await page.getByLabel("用户名").fill(rawUsername);
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
});
