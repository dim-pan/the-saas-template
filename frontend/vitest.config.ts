import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // Only run unit tests from the unit tests directory
    include: ['tests/unit/**/*.test.{js,ts,tsx}'],
    // Make sure we never try to run Playwright tests with Vitest
    exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**'],
    environment: 'node',
  },
});
