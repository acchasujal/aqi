import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { completeWindow, enumerateWindows, isExpired, matchedValidation, overlapsUnavailable, replayOutcomeCounts, schoolSportsDayPlan, stationMapPositions, unavailablePeriodError, validateForecast, validateReplay, validateBaselineComparison, observationAge } from '../src/domain.ts';

const actual = JSON.parse(readFileSync(new URL('../public/data/forecast.json', import.meta.url), 'utf8'));
const replay = JSON.parse(readFileSync(new URL('../public/data/replay.json', import.meta.url), 'utf8'));
const baseline = JSON.parse(readFileSync(new URL('../public/data/baseline_comparison.json', import.meta.url), 'utf8'));

test('real replay validates complete ranking, paired outcomes and declared coverage', () => {
  assert.equal(validateReplay(replay).cases.length, 1848);
});

test('historical outcome categories reconcile and use the alternative-only denominator', () => {
  const counts = replayOutcomeCounts(validateReplay(replay).cases);
  assert.equal(counts.lower + counts.higher + counts.equal + counts.missing, replay.cases.length);
  assert.equal(counts.lower + counts.higher + counts.equal, replay.summary.paired_outcome_cases);
  assert.equal(counts.missing, replay.summary.missing_outcome_cases);
  assert.equal(counts.changedWithOutcomes, replay.summary.selected_alternative_cases);
  assert.ok(Math.abs(counts.lowerChanged / counts.changedWithOutcomes - replay.summary.lower_observed_fraction) < 1e-12);
  assert.deepEqual(counts, { lower: 822, higher: 455, equal: 192, missing: 379, changedWithOutcomes: 1291, lowerChanged: 822 });
});

test('replay rejects corrupt clocks, rankings, outcomes, coverage and invented calibration', () => {
  for (const mutate of [
    r => { r.cases[0].hours[0].prediction = -1; },
    r => { r.cases[0].hours[0].target_start_ist = r.cases[0].issue_time_ist; },
    r => { r.cases[0].windows.reverse(); },
    r => { r.cases[0].selected.mean_prediction += 1; },
    r => { r.cases[0].selected.mean_observed = 999; },
    r => { r.summary.paired_outcome_cases = 0; },
    r => { r.calibration.status = 'calibrated'; },
    r => { r.cases[0].hours = null; },
  ]) {
    const corrupt = structuredClone(replay); mutate(corrupt);
    assert.throws(() => validateReplay(corrupt));
  }
});

test('observation age is elapsed time, independent of a freshness threshold', () => {
  assert.equal(observationAge('2026-11-02T23:00:00+05:30', Date.parse('2026-11-09T12:00:00+05:30')), 157);
  assert.equal(observationAge(null), null);
});

test('baseline comparison validates pooled and per-origin sensitivity results', () => {
  const result = validateBaselineComparison(baseline);
  assert.equal(result.full_replay.cases, 1848);
  assert.equal(result.heldout.cases, 192);
  assert.equal(result.heldout.usual_cleanest.direction, 'interval_includes_zero');
  assert.equal(result.heldout.usual_cleanest.origin_level.favor_airwindow + result.heldout.usual_cleanest.origin_level.favor_baseline + result.heldout.usual_cleanest.origin_level.ties, 8);
  assert.equal(result.heldout.usual_cleanest.origin_level.tie_tolerance, 0.01);
  const corrupt = structuredClone(baseline);
  corrupt.heldout.latest_window.cluster_bootstrap_95[0] = NaN;
  assert.throws(() => validateBaselineComparison(corrupt), /Baseline comparison artifact is invalid/);
  const badOriginCounts = structuredClone(baseline);
  badOriginCounts.full_replay.latest_window.origin_level.ties += 1;
  assert.throws(() => validateBaselineComparison(badOriginCounts), /Baseline comparison artifact is invalid/);
});
const hour = (n, value) => ({ target_start_ist: `2030-01-01T${String(n).padStart(2, '0')}:00:00+05:30`, target_end_ist: `2030-01-01T${String(n+1).padStart(2, '0')}:00:00+05:30`, pm25_prediction: value, status: value === null ? 'missing' : 'available', unit: 'µg/m³', forecast_horizon_hours: n, prediction_interval: null });
const station = (values) => ({ forecasts: values.map((v, i) => hour(i+8, v)) });

test('actual generated artifact passes browser boundary validation', () => {
  assert.equal(validateForecast(actual).stations.length, 4);
});

test('station locator projects only real artifact coordinates north-up at one distance scale', () => {
  const points = stationMapPositions(actual.stations);
  assert.deepEqual(Object.keys(points), actual.stations.map(s => s.station_id));
  const latitudes = actual.stations.map(s => s.latitude), longitudes = actual.stations.map(s => s.longitude);
  const centerLat = (Math.min(...latitudes) + Math.max(...latitudes)) / 2;
  const centerLon = (Math.min(...longitudes) + Math.max(...longitudes)) / 2;
  const eastScale = Math.cos(centerLat * Math.PI / 180);
  const scale = 340 / Math.max(Math.max(...latitudes) - Math.min(...latitudes), (Math.max(...longitudes) - Math.min(...longitudes)) * eastScale, 0.01);
  for (const station of actual.stations) {
    const point = points[station.station_id];
    assert.ok(Math.abs(point.x - (200 + (station.longitude - centerLon) * eastScale * scale)) < 1e-9);
    assert.ok(Math.abs(point.y - (200 - (station.latitude - centerLat) * scale)) < 1e-9);
    assert.ok(point.x > 0 && point.x < 400 && point.y > 0 && point.y < 400);
  }
  assert.ok(points['11606'].y < points['11611'].y);
  assert.ok(points['3409511'].x > points['3409510'].x);
  assert.deepEqual(stationMapPositions([]), {});
});

test('complete consecutive activity has exact mean maximum and peak', () => {
  const result = completeWindow(station([20, 50, 10]).forecasts, hour(8, 20).target_start_ist, 3);
  assert.equal(result.mean_prediction, 80/3);
  assert.equal(result.max_prediction, 50);
  assert.equal(result.peak_start_ist, hour(9, 50).target_start_ist);
  assert.equal(result.end_ist, hour(10, 10).target_end_ist);
});

test('duration and range boundaries enumerate only feasible complete hours', () => {
  const s = station([40, 20, 10, 30]);
  const windows = enumerateWindows(s, hour(8, 40).target_start_ist, hour(11, 30).target_end_ist, 2);
  assert.equal(windows.length, 3);
  assert.equal(windows[0].start_ist, hour(9, 20).target_start_ist);
  assert.deepEqual(windows.map(w => w.rank), [1, 2, 3]);
  assert.ok(windows.every(w => Date.parse(w.end_ist) <= Date.parse(hour(11, 30).target_end_ist)));
  assert.throws(() => enumerateWindows(s, hour(8, 40).target_start_ist, hour(8, 40).target_end_ist, 3), /does not fit/);
  assert.throws(() => enumerateWindows(s, hour(8, 40).target_start_ist, hour(11, 30).target_end_ist, 4), /one, two or three/);
});

const blocked = (id, start, end, label = 'Lunch break') => ({ id, label, start_ist: `2030-01-01T${start}:00+05:30`, end_ist: `2030-01-01T${end}:00+05:30` });

test('unavailable periods filter overlaps once while preserving empty-input behavior and tie order', () => {
  const s = station([10, 10, 10, 10, 10, 10]);
  const earliest = hour(8, 10).target_start_ist, latest = hour(13, 10).target_end_ist;
  const original = enumerateWindows(s, earliest, latest, 2);
  assert.deepEqual(enumerateWindows(s, earliest, latest, 2, []), original);
  assert.deepEqual(original.map(w => w.start_ist.slice(11, 16)), ['08:00', '09:00', '10:00', '11:00', '12:00']);
  const periods = [blocked('a', '09:00', '11:00'), blocked('b', '10:00', '12:00')];
  const feasible = enumerateWindows(s, earliest, latest, 2, periods);
  assert.deepEqual(feasible.map(w => w.start_ist.slice(11, 16)), ['12:00']);
  assert.deepEqual(feasible.map(w => w.rank), [1]);
  assert.equal(original.length - feasible.length, 4);
  assert.equal(overlapsUnavailable('2030-01-01T07:00:00+05:30', '2030-01-01T09:00:00+05:30', periods), false);
  assert.equal(overlapsUnavailable('2030-01-01T12:00:00+05:30', '2030-01-01T13:00:00+05:30', periods), false);
  assert.equal(enumerateWindows(s, earliest, latest, 2, [blocked('all', '08:00', '14:00')]).length, 0);
});

test('unavailable periods reject invalid times and never fill missing forecast hours', () => {
  const s = station([20, null, 10, 5]);
  const earliest = hour(8, 20).target_start_ist, latest = hour(11, 5).target_end_ist;
  assert.equal(enumerateWindows(s, earliest, latest, 2, [blocked('a', '08:00', '09:00')]).length, 1);
  assert.match(unavailablePeriodError(blocked('bad', '10:00', '10:00'), '2030-01-01', earliest, latest), /later than/);
  assert.match(unavailablePeriodError(blocked('bad', '07:00', '08:00'), '2030-01-01', earliest, latest), /forecast hours/);
  assert.match(unavailablePeriodError({ ...blocked('bad', '10:00', '11:00'), label: '' }, '2030-01-01', earliest, latest), /label/);
  assert.match(unavailablePeriodError({ ...blocked('bad', '10:00', '11:00'), end_ist: '2030-01-02T11:00:00+05:30' }, '2030-01-01', earliest, latest), /selected IST date/);
  assert.throws(() => enumerateWindows(s, earliest, latest, 2, [blocked('bad', '10:00', '10:00')]), /positive-length/);
});

test('school sports day demo selects a real two-hour window using the existing scheduler', () => {
  const now = Date.parse('2026-11-11T09:00:00+05:30');
  const plan = schoolSportsDayPlan(actual.stations, now);
  assert.deepEqual(plan, schoolSportsDayPlan(actual.stations, now));
  assert.equal(plan.duration, 2);
  assert.equal(plan.original.slice(11, 16), '10:00');
  assert.equal(plan.latest.slice(11, 16), '18:00');
  assert.equal(plan.latest.slice(0, 10), plan.date);
  assert.ok(Date.parse(plan.earliest) > now);
  const selected = actual.stations.find(s => s.station_id === plan.stationId);
  const original = completeWindow(selected.forecasts, plan.original, plan.duration);
  const windows = enumerateWindows(selected, plan.earliest, plan.latest, plan.duration);
  assert.ok(original);
  assert.ok(windows.length >= 2);
  assert.ok(windows.some(w => w.start_ist === original.start_ist));
  assert.equal(original.mean_prediction, original.hours.reduce((sum, h) => sum + h.pm25_prediction, 0) / 2);
});

test('sports day selection excludes missing hours and expires without substituting forecasts', () => {
  const s = { station_id: '11606', ...station([20, 30, null, 10, 15, 25]) };
  const now = Date.parse('2030-01-01T07:00:00+05:30');
  const plan = schoolSportsDayPlan([s], now);
  assert.equal(plan.original.slice(11, 16), '11:00');
  assert.equal(completeWindow(s.forecasts, hour(9, 30).target_start_ist, 2), null);
  assert.ok(enumerateWindows(s, plan.earliest, plan.latest, 2).every(w => w.hours.every(h => h.pm25_prediction !== null)));
  assert.equal(schoolSportsDayPlan([s], Date.parse('2030-01-01T14:00:00+05:30')), null);
});

test('missing observations are never treated as zero or bridged', () => {
  const s = station([20, null, 10, 5]);
  const windows = enumerateWindows(s, hour(8, 20).target_start_ist, hour(11, 5).target_end_ist, 2);
  assert.equal(windows.length, 1);
  assert.equal(windows[0].mean_prediction, 7.5);
  assert.equal(completeWindow(s.forecasts.filter((_, i) => i !== 1), hour(8, 20).target_start_ist, 2), null);
});

test('duplicates negative values and invalid hourly intervals are rejected independently', () => {
  assert.equal(completeWindow([hour(8, 1), hour(8, 2)], hour(8, 1).target_start_ist, 1), null);
  assert.equal(completeWindow([hour(8, -1)], hour(8, -1).target_start_ist, 1), null);
  const invalid = hour(8, 20); invalid.target_end_ist = hour(9, 20).target_end_ist;
  assert.equal(completeWindow([invalid], invalid.target_start_ist, 1), null);
});

test('original window remains independently retrievable outside move range', () => {
  const s = station([30, 20, 10, 40]);
  const original = completeWindow(s.forecasts, hour(8, 30).target_start_ist, 1);
  const alternatives = enumerateWindows(s, hour(9, 20).target_start_ist, hour(11, 40).target_end_ist, 1);
  assert.equal(original.mean_prediction, 30);
  assert.equal(alternatives[0].mean_prediction-original.mean_prediction, -20);
  assert.ok(!alternatives.some(w => w.start_ist === original.start_ist));
});

test('browser rejects invalid provenance clocks station mapping and unsupported units', () => {
  for (const mutate of [
    a => { a.pm_history_cutoff_ist = '2030-01-01T00:00:00+05:30'; },
    a => { a.stations[0].latitude = 19.5; },
    a => { a.stations[0].station_id = '11611'; },
    a => { a.stations[0].forecasts[0].unit = 'AQI'; },
    a => { a.stations[0].forecasts[0].forecast_horizon_hours = undefined; },
    a => { a.stations[0].forecasts[0].target_start_ist = '2026-11-08T16:00:00Z'; },
    a => { a.stations[0].data_status.available_forecast_hours = 0; },
    a => { a.stations[0].forecasts[0].prediction_interval = { lower: 1, upper: 100 }; },
  ]) {
    const changed = structuredClone(actual); mutate(changed);
    assert.throws(() => validateForecast(changed));
  }
});

test('expiry follows actual available artifact horizon and does not invent freshness', () => {
  const maxEnd = Math.max(...actual.stations.flatMap(s => s.forecasts.map(h => Date.parse(h.target_end_ist))));
  assert.equal(isExpired(actual, maxEnd-1), false);
  assert.equal(isExpired(actual, maxEnd), true);
  assert.equal(isExpired(actual, Date.parse(actual.model_issue_time_ist)), false);
  assert.equal(actual.stations[0].freshness.status, 'unknown');
});

test('validation benchmark is unavailable when current PM lead has no matching evidence', () => {
  const s = actual.stations[0];
  const window = completeWindow(s.forecasts, s.forecasts[20].target_start_ist, 2);
  const metric = matchedValidation(s, window, actual.model_issue_time_ist);
  assert.equal(metric.matched, false);
  assert.equal(metric.rmse, null);
  assert.match(metric.note, /outside comparable evidence/);
});
