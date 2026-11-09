import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: 'browser.spec.mjs',
  timeout: 45000,
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  outputDir: '../../data/processed/airwindow-browser-tests',
  use: { baseURL: process.env.AIRWINDOW_BASE_URL || 'http://127.0.0.1:5173', channel: 'chrome', headless: true, viewport: { width: 1440, height: 1000 }, locale: 'en-IN', timezoneId: 'Asia/Kolkata' },
});
