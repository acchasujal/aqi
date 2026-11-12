import { test, expect } from '@playwright/test';
import { mkdir } from 'node:fs/promises';
import path from 'node:path';
import { readFileSync } from 'node:fs';

const screenshots = path.resolve(process.env.AIRWINDOW_SCREENSHOT_DIR || '../../reports/creative_submission/screenshots');

test('real planner, abstention, evidence, replay, mobile and printable brief work', async ({ page }) => {
  const errors = [];
  const replayRequests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => { if (!request.failure()?.errorText.includes('ERR_ABORTED')) errors.push(`Network: ${request.url()}`); });
  page.on('response', response => { if (response.status() >= 400) errors.push(`HTTP ${response.status()}: ${response.url()}`); });
  page.on('request', request => { if (request.url().endsWith('/data/replay.json')) replayRequests.push(request.url()); });
  await mkdir(screenshots, { recursive: true });
  await page.clock.install({ time: new Date('2026-11-11T09:00:00+05:30') });
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
  await expect(page.getByText(/Forecast-ranked schedules are not calibrated recommendations/)).toBeVisible();
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_replay.png') });
  await page.locator('.replay-case').evaluate(el => el.scrollIntoView({ block: 'start', behavior: 'instant' }));
  await expect(page.getByText('HIGHER AFTERWARDS', { exact: true })).toHaveCount(0);
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await expect(page.getByText('HIGHER AFTERWARDS', { exact: true })).toBeVisible();
  await expect(page.getByText(/No schedule changes were endorsed/)).toBeVisible();
  await expect(page.getByText('1,848', { exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: /How did the forecast-ranked choice compare/ })).toBeVisible();
  await expect(page.locator('.baseline-panel')).toContainText('Usual cleanest window');
  await expect(page.locator('.baseline-panel')).toContainText('Latest feasible window');
  await expect(page.locator('.baseline-panel')).toContainText('−0.73');
  await expect(page.locator('.baseline-panel')).toContainText('-2.64 to 0.54');
  await expect(page.locator('.baseline-panel')).toContainText('Interval spans zero');
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_replay_detail.png') });
  await page.getByLabel('Station', { exact: true }).selectOption('11611');
  await expect(page.getByRole('heading', { name: /Malad West/ })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Reveal subsequent observations' })).toBeVisible();
  await page.getByRole('button', { name: 'Evidence & sources' }).click();
  await expect(page.getByRole('heading', { name: /Know what/ })).toBeVisible();
  await page.screenshot({ path: path.join(screenshots, 'airwindow_desktop_evidence.png'), fullPage: true });
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

test('one-click school sports day uses genuine future forecasts and keeps manual planning editable', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-11T09:00:00+05:30') });
  await page.goto('/');
  await page.getByRole('button', { name: 'Try a school sports day' }).click();
  await expect(page.getByText('Example event · School sports day')).toBeVisible();
  await expect(page.getByLabel('Activity duration')).toHaveValue('2');
  const originalStart = await page.getByLabel('Original start').inputValue();
  expect(originalStart.slice(11, 16)).toBe('10:00');
  const forecast = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
  const stationId = await page.getByLabel('Monitoring station').inputValue();
  const hours = forecast.stations.find(s => s.station_id === stationId).forecasts;
  const first = hours.find(h => h.target_start_ist === originalStart);
  const second = hours.find(h => Date.parse(h.target_start_ist) === Date.parse(originalStart) + 3_600_000);
  const expectedMean = ((first.pm25_prediction + second.pm25_prediction) / 2).toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  await expect(page.locator('.window-original .window-value strong')).toHaveText(expectedMean);
  await expect.poll(() => page.evaluate(() => document.activeElement?.classList.contains('comparison-area'))).toBe(true);
  await mkdir(screenshots, { recursive: true });
  await page.screenshot({ path: path.join(screenshots, 'airwindow_guided_live_demo.png') });
  await page.getByLabel('Original start').selectOption({ index: 3 });
  await expect(page.getByText('Example event · School sports day')).toHaveCount(0);
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.locator('.comparison-area')).toBeVisible();
});

test('expired or unusable forecast opens authentic hidden-outcome sports day replay by keyboard', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-22T12:00:00+05:30') });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  const demo = page.getByRole('button', { name: 'Explore a historical school sports day' });
  await expect(demo).toBeVisible();
  await demo.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Example event · School sports day')).toBeVisible();
  await expect(page.getByLabel('Duration')).toHaveValue('2');
  await expect(page.getByRole('button', { name: 'Reveal subsequent observations' })).toHaveAttribute('aria-expanded', 'false');
  await expect(page.locator('.replay-case .observed-color, .outcome-verdict')).toHaveCount(0);
  await expect.poll(() => page.evaluate(() => document.activeElement?.classList.contains('replay-case'))).toBe(true);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await mkdir(screenshots, { recursive: true });
  await page.screenshot({ path: path.join(screenshots, 'airwindow_guided_historical_demo.png') });
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await expect(page.locator('.replay-case .observed-color')).not.toHaveCount(0);
  await page.getByRole('button', { name: 'Plan an activity', exact: true }).click();
  await expect(page.getByRole('heading', { name: /Should you move/ })).toBeVisible();
  await expect(page.getByLabel('Monitoring station')).toBeVisible();
});

test('no complete future two-hour windows offers historical demo without inventing a forecast', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-11T09:00:00+05:30') });
  const forecast = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
  for (const station of forecast.stations) {
    station.forecasts.forEach((h, i) => { if (i % 2) { h.pm25_prediction = null; h.status = 'missing'; } });
    station.data_status.available_forecast_hours = station.forecasts.filter(h => h.status === 'available').length;
    station.data_status.missing_target_starts_ist = station.forecasts.filter(h => h.status === 'missing').map(h => h.target_start_ist);
  }
  await page.route('**/data/forecast.json', route => route.fulfill({ json: forecast }));
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Explore a historical school sports day' })).toBeVisible();
  await page.getByRole('button', { name: 'Explore a historical school sports day' }).click();
  await expect(page.getByRole('button', { name: 'Reveal subsequent observations' })).toHaveAttribute('aria-expanded', 'false');
});

test('historical replay keeps every outcome behind reveal and resets on selection changes', async ({ page }) => {
  const replay = JSON.parse(readFileSync(new URL('../public/data/replay.json', import.meta.url), 'utf8'));
  const initial = replay.cases.filter(c => c.station_id === '11606' && c.duration_hours === 2).at(-1);
  const observed = initial.original.mean_observed.toLocaleString('en-IN', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  const hidden = async () => {
    await expect(page.getByRole('button', { name: 'Reveal subsequent observations' })).toHaveAttribute('aria-expanded', 'false');
    await expect(page.locator('.replay-summary, .baseline-panel, .outcome-verdict, .replay-case .observed-color')).toHaveCount(0);
    await expect(page.locator('.replay-case [title^="Observed"]')).toHaveCount(0);
    await expect(page.locator('.replay-case')).not.toContainText('Later observed mean');
    await expect(page.locator('.replay-case')).not.toContainText('Retrospective decision classification');
    await expect(page.locator('.replay-case')).not.toContainText('Hindsight gap');
    await expect(page.locator('.replay-case')).not.toContainText('OBSERVED COMPARISON');
    await expect(page.locator('.replay-page')).not.toContainText('Median realised difference');
    await expect(page.locator('.replay-page')).not.toContainText('No schedule changes were endorsed');
    const html = await page.locator('.replay-page').evaluate(el => el.outerHTML);
    expect(html).not.toMatch(/(?:title|aria-label)="[^"]*(?:Observed |Hindsight gap|Later observed mean)/i);
    const accessibility = await page.locator('.replay-page').ariaSnapshot();
    expect(accessibility).not.toMatch(/Later observed mean|Hindsight gap|Median realised difference|Retrospective decision classification/);
  };
  await hidden();
  await expect(page.locator('.replay-outcome')).not.toContainText(observed);
  await page.locator('.replay-case summary').click();
  await expect(page.locator('.replay-case table')).not.toContainText('Later observed mean');
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await expect(page.locator('.replay-outcome')).toContainText(observed);
  await expect(page.locator('.replay-case .observed-color')).toHaveCount(12);
  await expect(page.locator('.replay-case [title^="Observed"]')).toHaveCount(10);
  await expect(page.locator('.replay-case table')).toContainText('Later observed mean');
  await expect(page.locator('.outcome-verdict')).toContainText('HIGHER AFTERWARDS');
  await expect(page.locator('.replay-summary')).toBeVisible();
  await expect(page.locator('.baseline-panel')).toBeVisible();
  await page.getByRole('button', { name: 'Hide subsequent observations' }).click();
  await hidden();
  await expect(page.locator('.replay-outcome')).not.toContainText(observed);
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  const otherCase = replay.cases.find(c => c.station_id === '11606' && c.duration_hours === 2 && c.case_id !== initial.case_id);
  await page.getByLabel('Historical forecast case').selectOption(otherCase.case_id);
  await hidden();
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await page.getByLabel('Station', { exact: true }).selectOption('11611');
  await hidden();
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await page.getByLabel('Duration').selectOption('3');
  await hidden();
});

test('missing station forecasts and missing replay observations remain missing', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-11T09:00:00+05:30') });
  const forecast = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
  const station = forecast.stations[0];
  for (const row of station.forecasts) { row.pm25_prediction = null; row.status = 'missing'; }
  station.data_status.status = 'unavailable';
  station.data_status.available_forecast_hours = 0;
  station.data_status.missing_target_starts_ist = station.forecasts.map(h => h.target_start_ist);
  await page.route('**/data/forecast.json', route => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(forecast) }));
  await page.goto('/');
  await page.getByLabel('Planning date').selectOption('2026-11-11');
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.getByRole('alert')).toContainText('original activity needs complete forecast hours');
  const replay = JSON.parse(readFileSync(new URL('../public/data/replay.json', import.meta.url), 'utf8'));
  const missing = replay.cases.find(c => c.station_id === '11606' && c.duration_hours === 2 && c.observed_difference === null);
  expect(missing).toBeTruthy();
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  await page.getByLabel('Historical forecast case').selectOption(missing.case_id);
  await expect(page.locator('.replay-outcome')).not.toContainText('Unavailable');
  await expect(page.locator('.outcome-verdict, .replay-case .observed-color')).toHaveCount(0);
  await page.getByRole('button', { name: 'Reveal subsequent observations' }).click();
  await expect(page.getByText('OBSERVED COMPARISON UNAVAILABLE', { exact: true })).toBeVisible();
  await expect(page.getByText(/missing values are never zero-filled/)).toBeVisible();
  await expect(page.locator('.replay-outcome')).toContainText('Unavailable');
  expect(await page.locator('.paired-bars i:nth-child(2)').count()).toBeLessThan(10);
  await page.getByRole('button', { name: 'Hide subsequent observations' }).click();
  await expect(page.locator('.replay-outcome')).not.toContainText('Unavailable');
  await expect(page.locator('.outcome-verdict, .replay-case .observed-color')).toHaveCount(0);
});

test('failed forecast URL and delayed or corrupt replay fail visibly without crashing', async ({ page }) => {
  const errors = []; page.on('pageerror', e => errors.push(e.message));
  await page.route('**/data/forecast.json', r => r.fulfill({ status: 404, body: 'Missing' }));
  await page.goto('/');
  await expect(page.getByText('Forecast file could not be loaded (404).')).toBeVisible();
  await page.unroute('**/data/forecast.json'); await page.reload();
  await page.route('**/data/replay.json', async r => {
    await new Promise(resolve => setTimeout(resolve, 700));
    await r.fulfill({ status: 503, body: 'Unavailable' });
  });
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  await expect(page.getByText('Loading genuine OOF forecasts…')).toBeVisible();
  await expect(page.getByText('The historical replay artifact is unavailable.')).toBeVisible();
  await page.route('**/data/replay.json', r => r.fulfill({ json: { schema_version: '1.0.0', cases: [{}], calibration: {}, summary: {} } }));
  await page.reload();
  await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
  await expect(page.getByText(/Replay artifact is invalid/)).toBeVisible();
  await page.unroute('**/data/replay.json');
  await page.getByRole('button', { name: 'Retry replay' }).click();
  await expect(page.getByRole('button', { name: 'Reveal subsequent observations' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('a missing alternative hour excludes every window using it', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-11-11T06:00:00+05:30') });
  const forecast = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
  const missing = forecast.stations[0].forecasts.find(h => h.target_start_ist === '2026-11-11T15:00:00+05:30');
  missing.status = 'missing'; missing.pm25_prediction = null;
  const status = forecast.stations[0].data_status;
  status.available_forecast_hours -= 1;
  status.missing_target_starts_ist = forecast.stations[0].forecasts.filter(h => h.status === 'missing').map(h => h.target_start_ist);
  await page.route('**/data/forecast.json', r => r.fulfill({ json: forecast }));
  await page.goto('/'); await page.getByLabel('Planning date').selectOption('2026-11-11');
  await page.getByRole('button', { name: 'Compare time windows' }).click();
  await expect(page.locator('.alternatives tbody tr')).toHaveCount(7);
  await expect(page.locator('.alternatives tbody')).not.toContainText('2:00 pm – 4:00 pm');
  await expect(page.locator('.alternatives tbody')).not.toContainText('3:00 pm – 5:00 pm');
});

test('keyboard journey, narrow screens, 200 percent equivalent reflow and candidate replay', async ({ page }) => {
  await page.goto('/'); await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'Skip to content' })).toBeFocused();
  await page.getByLabel('Monitoring station').focus();
  await page.keyboard.press('m'); await page.keyboard.press('Tab');
  await expect(page.getByLabel('Planning date')).toBeFocused();
  await page.getByRole('button', { name: 'Compare time windows' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.comparison-area')).toBeFocused();
  for (const width of [720, 390, 320]) {
    await page.setViewportSize({ width, height: 900 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Evidence & sources' }).click();
    await expect(page.getByText('Frozen; not continuously updated')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Historical replay', exact: true }).click();
    await page.locator('.replay-case summary').click();
    await expect(page.locator('.replay-case table')).toBeVisible();
    await expect(page.locator('.replay-case table')).toContainText('Selected');
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.getByRole('button', { name: 'Plan an activity', exact: true }).click();
  }
});
