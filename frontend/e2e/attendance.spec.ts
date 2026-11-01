import { expect, test } from "@playwright/test";

import { login, logout, USERS } from "./helpers";

test("працівниця відмічається, HR бачить її в місячному звіті", async ({ page }) => {
  await login(page, USERS.olena, "/attendance");
  const nav = page.getByRole("navigation", { name: "Розділи" });
  await expect(nav.getByRole("link", { name: "Табель команди" })).toHaveCount(0);

  // Перший прогін — нова відмітка, повторний — виправлення сьогоднішньої
  await page.getByRole("radio", { name: "Віддалено" }).check();
  await page.getByRole("textbox", { name: "Коментар" }).fill("e2e");
  await page.getByRole("button", { name: /^(Відмітитись|Зберегти зміни)$/ }).click();
  await expect(page.getByText("Збережено")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Сьогодні — відмічено" })).toBeVisible();
  await logout(page);

  await login(page, USERS.hr, "/attendance/report");
  const row = page.getByRole("row").filter({ hasText: "Коваль Олена" });
  await expect(row).toBeVisible();
  await expect(page.getByText(/Робочих днів у місяці: \d+/)).toBeVisible();
});
