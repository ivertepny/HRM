import { expect, test } from "@playwright/test";

import { login, USERS } from "./helpers";

test("адміністратор створює обліковий запис і оформлює прийом", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;
  await login(page, USERS.admin, "/admin/users");

  await page.getByRole("button", { name: "Створити обліковий запис" }).click();
  await page.getByRole("textbox", { name: "Ім'я" }).fill("Тест");
  await page.getByRole("textbox", { name: "Прізвище" }).fill("Плейрайт");
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(email);
  await page.getByRole("button", { name: "Згенерувати" }).click();
  await page.getByRole("button", { name: "Створити обліковий запис" }).click();

  await expect(page.getByRole("heading", { name: "Тест Плейрайт" })).toBeVisible();
  await expect(page.getByText("Employee — уся компанія")).toBeVisible();

  await page.getByRole("combobox", { name: "Посада" }).selectOption({ label: "Розробник" });
  await page.getByRole("combobox", { name: "Підрозділ" }).selectOption({ label: "Головний офіс > IT > Backend" });
  await page.getByRole("button", { name: "Оформити прийом" }).click();

  await expect(page.getByRole("link", { name: "Відкрити профіль працівника" })).toBeVisible();
});

test("матриця дозволів показує права ролі", async ({ page }) => {
  await login(page, USERS.admin, "/admin/roles");

  await page.getByRole("button", { name: /HR Manager/ }).click();

  await expect(page.getByRole("checkbox", { name: "Зарплати: усі дії" })).toBeChecked();
  await expect(page.getByRole("checkbox", { name: "Ролі та доступ: Керування" })).not.toBeChecked();
});
