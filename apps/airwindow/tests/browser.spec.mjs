import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { readFileSync } from 'node:fs';

const screenshots = path.resolve(process.env.AIRWINDOW_SCREENSHOT_DIR || '../../reports/creative_submission/screenshots');

test('real planner, abstention, evidence, replay, mobile and printable brief work', async ({ page }) => {
  const errors = [];
  const replayRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => { if (request.url().endsWith('/data/replay.json')) replayRequests.push(request.url()); });
  await mkdir(screenshots, { recursive: true });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Should you move/ })).toBeVisible();
  await expect(page.getByLabel('Monitoring station')).toHaveValue('11606');
  expect(replayRequests).toHaveLength(0);
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_plan.png') });
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByText('INSUFFICIENT EVIDENCE', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('heading', { name: /Your original/ })).toBeVisible();
  await expect(page.getByText('Original schedule', { exact: true }).first()).toBeVisible();
  await expect(page.getByText(/current issue\/PM clocks outside comparable evidence/)).toBeVisible();
  await page.waitForTimeout(450); // Let the user-facing smooth scroll settle before the documentary capture.
  await page.locator('.comparison-area').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_comparison.png') });
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_decision.png') });
  await page.getByRole('button', { name: 'Create event brief' }).click();
  await expect(page.getByRole('heading', { name: 'A plan, with its evidence attached.' })).toBeVisible();
  await expect(page.locator('#event-brief')).toContainText('Matched station validation unavailable');
  await page.emulateMedia({ media: 'print' });
  await page.pdf({ path: path.join(screenshots, 'airwindow_event_brief.pdf'), format: 'A4', printBackground: true });
  await page.screenshot({ path: path.join(screenshots, 'airwindow_event_brief.png'), fullPage: true });
  await page.emulateMedia({ media: 'screen' });
  await page.getByRole('button', { name: 'Close brief' }).click();
  await page.getByLabel('Activity duration').selectOption('3');
  await expect(page.getByRole('heading', { name: /Your original/ })).toHaveCount(0);
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('heading', { name: /Your original/ })).toBeVisible();
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Would the move/ })).toBeVisible();
  await expect(page.getByText('1,848', { exact: true })).toBeVisible();
  await expect(page.getByText(/No schedule changes were endorsed/)).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_replay.png') });
  await page.locator('.replay-case').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_replay_detail.png') });
  await page.getByLabel('Station', { exact: true }).selectOption('11611');
  await expect(page.getByRole('heading', { name: /Malad West/ })).toBeVisible();
  await page.getByRole('button', { name: 'Evidence & sources' }).click();
  await expect(page.getByRole('heading', { name: /Know what/ })).toBeVisible();
  await page.getByRole('button', { name: 'Plan an activity', exact: true }).click();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.evaluate(() => window.scrollTo(0, 0));
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: path.join(screenshots, 'airwindow_mobile_plan.png'), fullPage: true });
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByText('INSUFFICIENT EVIDENCE', { exact: true }).first()).toBeVisible();
  expect(errors).toEqual([]);
});

test('impossible duration and missing/invalid forecast artifact fail explicitly', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByLabel('Activity duration')).toBeVisible();
  await page.getByLabel('Activity duration').selectOption('3');
  await page.getByLabel('Latest feasible end').selectOption({ label: '9:00 am' });
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('alert')).toContainText('does not fit');
  await page.route('**/data/forecast.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: '{"schema_version":"broken"}' }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'A plan needs real data.' })).toBeVisible();
  await expect(page.getByText(/No substitute forecast/)).toBeVisible();
});

test('best original abstains and expired frozen snapshot cannot produce a new plan', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Original start').selectOption({ label: '3:00 pm' });
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByText('NO CLEAR WINNER', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Your current slot is already as well ranked.' })).toBeVisible();
  await page.clock.install({ time: new Date('2026-11-22T12:00:00+05:30') });
  await page.reload();
  await expect(page.getByText(/New planning is disabled/)).toBeVisible();
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('alert')).toContainText('forecast period has ended');
  await expect(page.getByRole('heading', { name: /Your original/ })).toHaveCount(0);
});

test('a partly elapsed horizon defaults to future activity dates and hours', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-19T12:00:00+05:30') });
  await page.goto('/');
  await expect(page.getByLabel('Planning date')).toHaveValue('2026-11-20');
  await expect(page.getByLabel('Planning date').locator('option[value="2026-11-09"]')).toHaveCount(0);
  await page.getByLabel('Planning date').selectOption('2026-11-19');
  await expect(page.getByLabel('Original start').locator('option')).toHaveCount(11);
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('heading', { name: /Your original/ })).toBeVisible();
  const starts = await page.locator('.comparison-grid .window-date').allTextContents();
  expect(starts.every(value => value.includes('19 Nov 2026'))).toBe(true);
});

test('missing station forecasts and missing replay observations remain missing', async ({ page }) => {
  const forecast = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
  const station = forecast.stations[0];
  for (const row of station.forecasts) { row.pm25_prediction = null; row.status = 'missing'; }
  station.data_status.status = 'unavailable';
  station.data_status.available_forecast_hours = 0;
  station.data_status.missing_target_starts_ist = station.forecasts.map(h => h.target_start_ist);
  await page.route('**/data/forecast.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(forecast) }));
  await page.goto('/');
  await page.getByLabel('Planning date').selectOption('2026-11-09');
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('alert')).toContainText('original activity needs complete forecast hours');
  const replay = JSON.parse(readFileSync(new URL('../public/data/replay.json', import.meta.url), 'utf8'));
  const missing = replay.cases.find(c => c.station_id === '11606' && c.duration_hours === 2 && c.observed_difference === null);
  expect(missing).toBeTruthy();
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  await page.getByLabel('Historical forecast case').selectOption(missing.case_id);
  await expect(page.getByText('OBSERVED COMPARISON UNAVAILABLE', { exact: true })).toBeVisible();
  await expect(page.getByText(/missing values are never zero-filled/)).toBeVisible();
  expect(await page.locator('.paired-bars i:nth-child(2)').count()).toBeLessThan(10);
});
