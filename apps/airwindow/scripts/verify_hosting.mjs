import { chromium } from '@playwright/test';

const baseUrl = (process.env.AIRWINDOW_PUBLIC_URL || 'https://airwindow-99085.web.app').replace(/\/$/, '');
const browser = await chromium.launch({ channel: 'chrome', headless: true });
const context = await browser.newContext(); // isolated, signed-out browser context
const page = await context.newPage();
const errors = [];
page.on('pageerror', error => errors.push(error.message));
page.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
try {
  const response = await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60_000 });
  if (response?.status() !== 200) throw new Error(`Homepage returned HTTP ${response?.status()}`);
  const heading = page.getByRole('heading', { name: /Should you move/ });
  await heading.waitFor({ state: 'visible', timeout: 15_000 });
  const result = await page.evaluate(async () => {
    const read = async path => {
      const response = await fetch(path, { cache: 'no-store' });
      if (!response.ok) throw new Error(`${path} returned HTTP ${response.status}`);
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.toLowerCase().includes('application/json')) throw new Error(`${path} has unexpected content type ${contentType}`);
      const bytes = await response.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const sha256 = [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
      return { data: JSON.parse(new TextDecoder().decode(bytes)), bytes: bytes.byteLength, sha256, contentType };
    };
    const manifestResponse = await fetch('./data/manifest.json', { cache: 'no-store' });
    if (!manifestResponse.ok) throw new Error(`manifest.json returned HTTP ${manifestResponse.status}`);
    const manifest = await manifestResponse.json();
    const artifacts = {};
    for (const [key, file, hashField] of [
      ['forecast', 'forecast.json', 'forecast_sha256'],
      ['replay', 'replay.json', 'replay_sha256'],
      ['baseline', 'baseline_comparison.json', 'baseline_comparison_sha256'],
      ['fallback', 'forecast_fallback_task008.json', 'fallback_forecast_sha256'],
    ]) {
      const item = await read(`./data/${file}`);
      if (item.sha256 !== manifest[hashField]) throw new Error(`${file} SHA-256 does not match manifest`);
      artifacts[key] = { bytes: item.bytes, sha256: item.sha256, contentType: item.contentType, schemaVersion: item.data.schema_version };
    }
    return { manifest, artifacts };
  });
  if (errors.length) throw new Error(`Browser errors: ${errors.join('; ')}`);
  console.log(JSON.stringify({ url: baseUrl, browserContext: 'fresh signed-out context', status: response.status(), heading: await heading.innerText(), ...result, errors }, null, 2));
} finally {
  await context.close();
  await browser.close();
}
