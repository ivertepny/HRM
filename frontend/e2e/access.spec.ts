import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test("працівник не бачить адміністрування і чужих зарплат", async ({ page }) => {
  await login(page, USERS.olena, "/profile");

  const nav = page.getByRole("navigation", { name: "Розділи" });
  await expect(nav.getByRole("link", { name: "Працівники" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Облікові записи" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Відпустки команди" })).toHaveCount(0);

  // Своя зарплата видна
  await expect(page.getByRole("heading", { name: "Зарплата" })).toBeVisible();

  // Чужа — ні
  await page.goto("/employees");
  await page.getByRole("link", { name: /Петро Шевчук/ }).click();
  await expect(page.getByRole("heading", { name: "Петро Шевчук" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Зарплата" })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Кадрова зміна" })).toHaveCount(0);
});

test("пряме посилання на адмін-розділ не відкриває чужих даних", async ({ page }) => {
  await login(page, USERS.olena, "/admin/roles");

  await expect(page.getByText("Розділ для адміністраторів доступу.")).toBeVisible();
});

test("HR бачить зарплату і форму кадрової зміни", async ({ page }) => {
  await login(page, USERS.hr, "/employees");

  await page.getByRole("link", { name: /Петро Шевчук/ }).click();

  await expect(page.getByRole("heading", { name: "Зарплата" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Кадрова зміна" })).toBeVisible();
});
