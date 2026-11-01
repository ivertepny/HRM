import { defineConfig, devices } from "@playwright/test";

/**
 * e2e проти стенда з docker-compose.e2e.yml (засіяного seed_demo).
 * Тести змінюють спільні дані, тому виконуються послідовно.
 */
export default defineConfig({
  testDir: "e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:13000",
    locale: "uk-UA",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chrome",
      // Локально — встановлений Chrome; у CI — завантажений chromium
      use: process.env.CI
        ? { ...devices["Desktop Chrome"] }
        : { ...devices["Desktop Chrome"], channel: "chrome" },
    },
  ],
});
