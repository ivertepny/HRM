import { expect, test } from "@playwright/test";

import { login, logout, USERS } from "./helpers";

const MONITOR = 'Dell P2723DE 27"';

test("HR видає монітор зі складу, працівниця бачить його в профілі, HR приймає назад", async ({
  page,
}) => {
  // Склад: знаходимо монітор за серійним номером
  await login(page, USERS.hr, "/equipment");
  await page.getByRole("searchbox", { name: "Пошук" }).fill("DEMO-MN-001");
  await page.getByRole("link", { name: MONITOR }).click();
  await expect(page.getByRole("heading", { name: MONITOR })).toBeVisible();

  // Видача
  await page.getByRole("button", { name: "Видати працівнику" }).click();
  await page.getByRole("searchbox", { name: "Знайти працівника" }).fill("olena");
  const employee = page.getByRole("combobox", { name: "Працівник" });
  await expect(employee.locator("option")).toHaveCount(2); // підказка + Олена
  await employee.selectOption({ index: 1 });
  await page.getByRole("textbox", { name: "Примітка" }).fill("З кабелем USB-C");
  await page.getByRole("button", { name: "Видати", exact: true }).click();
  await expect(page.getByText("Видано: Коваль Олена")).toBeVisible();
  await expect(page.getByText("зараз у працівника")).toBeVisible();
  await logout(page);

  // Працівниця бачить монітор у профілі, але не склад
  await login(page, USERS.olena, "/profile");
  await expect(page.getByText(MONITOR)).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Розділи" });
  await expect(nav.getByRole("link", { name: "Обладнання" })).toHaveCount(0);
  await logout(page);

  // Повернення — стенд лишається в початковому стані для наступного прогону
  await login(page, USERS.hr, "/equipment");
  await page.getByRole("searchbox", { name: "Пошук" }).fill("DEMO-MN-001");
  await page.getByRole("link", { name: MONITOR }).click();
  await page.getByRole("button", { name: "Повернути на склад" }).click();
  await page.getByRole("button", { name: "Підтвердити повернення" }).click();
  await expect(page.getByText("Повернено на склад")).toBeVisible();
  await expect(page.getByRole("button", { name: "Видати працівнику" })).toBeVisible();
});
