import { expect, type Page } from "@playwright/test";

/** Пароль демо-користувачів (docker-compose.e2e.yml → seed_demo --password). */
export const PASSWORD = process.env.E2E_PASSWORD ?? "Demo-pass-2026";

export const USERS = {
  admin: "admin@example.com",
  hr: "hr@example.com",
  olena: "olena@example.com",
  petro: "petro@example.com",
} as const;

export async function login(page: Page, email: string, next = "/") {
  await page.goto(`/login?next=${encodeURIComponent(next)}`);
  await page.getByRole("textbox", { name: "Робоча пошта" }).fill(email);
  await page.locator("input[type=password]:visible").fill(PASSWORD);
  await page.getByRole("button", { name: "Увійти" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

export async function logout(page: Page) {
  await page.getByRole("button", { name: "Меню користувача" }).click();
  await page.getByRole("menuitem", { name: "Вийти" }).click();
  await expect(page).toHaveURL(/\/login/);
}

/** Дата через `days` днів у форматі YYYY-MM-DD (як у полях type=date). */
export function inDays(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

/** Випадковий зсув — повторні прогони на тому ж стенді не перетинаються датами. */
export function randomOffset() {
  return 100 + Math.floor(Math.random() * 600);
}
