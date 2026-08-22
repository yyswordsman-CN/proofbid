import { expect, test } from "@playwright/test";

test("home has two public-safe synthetic cases without horizontal overflow", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /From tender event/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Run green case/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Run blocked case/ })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test("green event reaches a reviewable downloadable terminal package", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Run green case/ }).click();
  await expect(page.getByText("Preparation package ready for controlled submission")).toBeVisible({
    timeout: 20_000
  });
  await expect(page.getByRole("link", { name: /Download validated ZIP/ })).toBeVisible();
  await expect(page.getByText("finalize complete")).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflow).toBe(false);
});

test("blocked event isolates one project authorization gap", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /Run blocked case/ }).click();
  await expect(page.getByText("Package blocked with evidence gaps")).toBeVisible({
    timeout: 20_000
  });
  await expect(page.getByText("PROJECT_AUTHORIZATION_MISSING")).toBeVisible();
  await expect(page.getByText("Missing items").locator("..").getByText("1", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /Download validated ZIP/ })).toBeVisible();
});
