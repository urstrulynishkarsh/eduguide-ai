import { defineConfig, devices } from "@playwright/test";

/**
 * End-to-end journeys against the real backend. Start the database and the API first
 * (see the README); Playwright builds and starts the frontend itself.
 */
export default defineConfig({
  testDir: "tests/e2e",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: devices["Desktop Chrome"] },
    { name: "phone", use: devices["Pixel 7"] },
  ],
  webServer: {
    command: "npm run build && npm run start",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
});
