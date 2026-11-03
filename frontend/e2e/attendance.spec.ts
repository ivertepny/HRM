import { readFile } from "node:fs/promises";

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

  // Той самий звіт файлом для Excel
  const downloading = page.waitForEvent("download");
  await page.getByRole("link", { name: "Завантажити CSV" }).click();
  const download = await downloading;
  expect(download.suggestedFilename()).toMatch(/^tabel-\d{4}-\d{2}\.csv$/);
  const csv = await readFile((await download.path())!, "utf8");
  expect(csv.startsWith("\ufeffПрацівник;Email;Підрозділ;")).toBe(true);
  expect(csv).toContain("Коваль Олена;olena@example.com;");
});

test("HR додає і прибирає святковий день", async ({ page }) => {
  // Далекий рік і випадковий день — повторні прогони не зіткнуться датою
  const day = String(1 + Math.floor(Math.random() * 28)).padStart(2, "0");
  const name = `e2e-свято-${Date.now()}`;
  await login(page, USERS.hr, "/attendance/holidays");

  for (let i = 0; i < 5; i++) {
    await page.getByRole("button", { name: /→$/ }).click();
  }
  const year = new Date().getFullYear() + 5;
  await expect(page.getByRole("heading", { name: `${year} рік` })).toBeVisible();

  await page.getByLabel("Дата").fill(`${year}-03-${day}`);
  await page.getByLabel("Назва").fill(name);
  await page.getByRole("button", { name: "Додати свято" }).click();
  await expect(page.getByText(name)).toBeVisible();

  await page.getByRole("button", { name: `Видалити «${name}»` }).click();
  await expect(page.getByText(name)).toHaveCount(0);
});
