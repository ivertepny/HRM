import { expect, type Page, test } from "@playwright/test";

import { inDays, login, logout, randomOffset, USERS } from "./helpers";

async function submitVacation(page: Page, start: string, end: string) {
  await page.goto("/vacations");
  await page.getByLabel("Перший день", { exact: true }).filter({ visible: true }).fill(start);
  await page.getByLabel("Останній день", { exact: true }).filter({ visible: true }).fill(end);
  await page.getByRole("button", { name: "Подати заявку" }).click();
  await expect(page.getByText("Заявку подано")).toBeVisible();
}

test("працівник подає і скасовує заявку", async ({ page }) => {
  const offset = randomOffset();
  await login(page, USERS.olena, "/vacations");

  await submitVacation(page, inDays(offset), inDays(offset + 2));

  const row = page.getByRole("row").filter({ hasText: "На розгляді" }).first();
  await expect(row).toContainText("3 дні");
  await row.getByRole("button", { name: "Скасувати заявку" }).click();
  await expect(page.getByText("Заявку скасовано")).toBeVisible();
});

test("перетин дат показує помилку біля форми", async ({ page }) => {
  const offset = randomOffset();
  await login(page, USERS.olena, "/vacations");
  await submitVacation(page, inDays(offset), inDays(offset + 4));

  await page.getByLabel("Перший день", { exact: true }).filter({ visible: true }).fill(inDays(offset + 2));
  await page.getByLabel("Останній день", { exact: true }).filter({ visible: true }).fill(inDays(offset + 6));
  await page.getByRole("button", { name: "Подати заявку" }).click();

  await expect(page.getByRole("alert").filter({ hasText: /\S/ })).toContainText("Перетин");
});

test("HR схвалює заявку працівника", async ({ page }) => {
  const offset = randomOffset();
  await login(page, USERS.petro, "/vacations");
  await submitVacation(page, inDays(offset), inDays(offset + 1));
  await logout(page);

  await login(page, USERS.hr, "/vacations/review");
  const row = page
    .getByRole("row")
    .filter({ hasText: "Шевчук Петро" })
    .filter({ hasText: "2 календарні дні" })
    .first();
  await row.getByRole("button", { name: "Схвалити" }).click();

  await expect(page.getByText("Заявку схвалено")).toBeVisible();
});
