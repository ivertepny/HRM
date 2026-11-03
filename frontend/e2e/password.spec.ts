import { expect, test } from "@playwright/test";

import { login, logout, USERS } from "./helpers";
import { lastLink } from "./mail";

const FIRST_PASSWORD = "Invite-accepted-2026";
const SECOND_PASSWORD = "Reset-worked-2026";

async function signIn(page: import("@playwright/test").Page, email: string, password: string) {
  await page.goto("/login");
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(email);
  await page.locator("input[type=password]:visible").fill(password);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

async function setPassword(page: import("@playwright/test").Page, password: string) {
  await page.getByLabel("Новий пароль").fill(password);
  await page.getByLabel("Повторіть пароль").fill(password);
  await page.getByRole("button", { name: "Зберегти пароль" }).click();
  await expect(page.getByText("Пароль збережено")).toBeVisible();
}

test("запрошення → свій пароль → забутий пароль → новий пароль", async ({ page }) => {
  const email = `invite-${Date.now()}@example.com`;

  // Адміністратор створює запис — людина отримує лист із запрошенням
  await login(page, USERS.admin, "/admin/users");
  await page.getByRole("button", { name: "Створити обліковий запис" }).click();
  await page.getByRole("textbox", { name: "Ім'я" }).fill("Нова");
  await page.getByRole("textbox", { name: "Прізвище" }).fill("Колега");
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(email);
  await page.getByRole("button", { name: "Створити і надіслати запрошення" }).click();
  await expect(page.getByText(`Запрошення надіслано на ${email}`)).toBeVisible();
  await logout(page);

  // Людина відкриває посилання і задає пароль; вдруге воно не діє
  const invite = lastLink(email, "/invite");
  await page.goto(invite);
  await expect(page.getByRole("heading", { name: "Ласкаво просимо" })).toBeVisible();
  await setPassword(page, FIRST_PASSWORD);
  await signIn(page, email, FIRST_PASSWORD);
  await logout(page);

  await page.goto(invite);
  await page.getByLabel("Новий пароль").fill("Another-try-2026");
  await page.getByLabel("Повторіть пароль").fill("Another-try-2026");
  await page.getByRole("button", { name: "Зберегти пароль" }).click();
  await expect(page.getByText("Посилання не діє")).toBeVisible();

  // Забула пароль: лист зі скиданням → новий пароль → вхід
  await page.goto("/login");
  await page.getByRole("link", { name: "Забули пароль?" }).click();
  // Поле з тією ж назвою є і на сторінці входу — чекаємо, поки перехід завершиться
  await expect(page.getByRole("heading", { name: "Забули пароль?" })).toBeVisible();
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(email);
  await page.getByRole("button", { name: "Надіслати посилання" }).click();
  await expect(page.getByText("Перевірте пошту")).toBeVisible();

  await page.goto(lastLink(email, "/reset-password"));
  await setPassword(page, SECOND_PASSWORD);
  await page.getByRole("link", { name: "Увійти" }).click();
  await signIn(page, email, SECOND_PASSWORD);
});
