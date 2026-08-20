import { defineConfig } from "cypress";

export default defineConfig({
  allowCypressEnv: false,
  trashAssetsBeforeRuns: false,
  video: false,
  screenshotOnRunFailure: true,
  viewportWidth: 1280,
  viewportHeight: 800,
  e2e: {
    baseUrl: "http://localhost:5173",
    specPattern: "cypress/e2e/**/*.cy.{js,ts}",
    supportFile: "cypress/support/e2e.ts",
    defaultCommandTimeout: 10000,
  },
});
