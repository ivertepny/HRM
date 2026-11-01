import { expect, test } from "@playwright/test";

import { login, logout, PASSWORD, USERS } from "./helpers";

test("закрита сторінка веде на вхід і повертає назад після логіну", async ({ page }) => {
  await page.goto("/vacations");
  await expect(page).toHaveURL(/\/login\?next=%2Fvacations/);

  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(USERS.olena);
  await page.locator("input[type=password]:visible").fill(PASSWORD);
  await page.getByRole("button", { name: "Увійти" }).click();

  await expect(page).toHaveURL(/\/vacations$/);
  await expect(page.getByRole("heading", { name: "Мої відпустки" })).toBeVisible();
});

test("неправильний пароль дає зрозуміле повідомлення", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(USERS.olena);
  await page.locator("input[type=password]:visible").fill("wrong-password");
  await page.getByRole("button", { name: "Увійти" }).click();

  // Next.js має власний порожній role="alert" (оголошувач навігації) — беремо непорожній
  await expect(page.getByRole("alert").filter({ hasText: /\S/ })).toHaveText(
    "Невірна пошта або пароль.",
  );
});

test("вихід завершує сесію", async ({ page }) => {
  await login(page, USERS.olena, "/profile");
  await expect(page.getByRole("heading", { name: "Олена Коваль" })).toBeVisible();

  await logout(page);
  await page.goto("/profile");

  await expect(page).toHaveURL(/\/login/);
});
