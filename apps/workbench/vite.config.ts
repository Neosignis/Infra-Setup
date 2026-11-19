import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

const apiPort = Number(process.env.NEOSIGNIS_API_PORT || 8000);
const experimentPort = Number(process.env.NEOSIGNIS_EXPERIMENT_PORT || 8002);
if (!Number.isInteger(experimentPort) || experimentPort < 1024 || experimentPort > 65535) throw new Error('Invalid local interpreter port');
if (!Number.isInteger(apiPort) || apiPort < 1024 || apiPort > 65535) {
  throw new Error('NEOSIGNIS_API_PORT must be an unprivileged local port');
}

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: Number(process.env.NEOSIGNIS_WEB_PORT || 5173),
    strictPort: true,
    proxy: {
      '/research': {
        target: `http://127.0.0.1:${experimentPort}`,
        rewrite: path => path.replace(/^\/research/, ''),
        timeout: 30000,
        proxyTimeout: 30000,
      },
      // Development-only loopback proxy. The bearer secret never enters the bundle.
      '/engine': {
        target: `http://127.0.0.1:${apiPort}`,
        rewrite: path => path.replace(/^\/engine/, ''),
        headers: process.env.DEV_API_TOKEN
          ? { Authorization: `Bearer ${process.env.DEV_API_TOKEN}` }
          : {},
        timeout: 5000,
        proxyTimeout: 5000,
      },
    },
  },
  test: {
    // Keep test processes within the memory available on the development Mac.
    pool: 'threads',
    maxWorkers: 1,
    disableConsoleIntercept: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    restoreMocks: true,
  },
});
