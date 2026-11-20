import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  retries: 0,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:5175',
    acceptDownloads: true,
    permissions: ['camera'],
    launchOptions: {
      ...(process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE } : {}),
      args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream'],
    },
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'exec python3 ../../scripts/run_local_demo.py --web-port 5175 --api-port 8010 --worker-port 8011',
    url: 'http://127.0.0.1:5175',
    reuseExistingServer: false,
    timeout: 45_000,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 15_000 },
  },
});
