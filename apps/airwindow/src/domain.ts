import type { BaselineComparison, ForecastArtifact, ForecastHour, ReplayArtifact, Station, TimeWindow } from './types.ts';

const HOUR = 3_600_000;
const IDS = ['11606', '11611', '3409510', '3409511'];
const LOCATIONS: Record<string, [number, number]> = { '11606': [19.23241, 72.86895], '11611': [19.19709, 72.82204], '3409510': [18.9767, 72.838], '3409511': [19.060498, 72.923356] };
const validIst = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+05:30$/.test(value) && Number.isFinite(Date.parse(value));

export function observationAge(timestamp: string | null, now = Date.now()): number | null {
  return timestamp && validIst(timestamp) ? Math.max(0, (now - Date.parse(timestamp)) / HOUR) : null;
}

// Validate the retrospective payload before any component reads nested values.
// The Python contract remains authoritative at export; these checks also guard
// failed/incorrect static URLs and corrupted browser responses.
export function validateReplay(value: unknown): ReplayArtifact {
  const r = value as ReplayArtifact;
  const fail = () => { throw new Error('Replay artifact is invalid. Check the versioned replay file and manifest.'); };
  const finite = (n: unknown): n is number => typeof n === 'number' && Number.isFinite(n);
  const concentration = (n: unknown) => finite(n) && n >= 0;
  const equal = (a: number, b: number) => Math.abs(a - b) < 1e-7;
  if (!r || r.schema_version !== '1.0.0' || !Array.isArray(r.cases) || !r.cases.length || !r.provenance || !r.calibration || !r.summary || !Array.isArray(r.by_station_duration)) fail();
  if (r.calibration.status !== 'not_calibrated' || r.calibration.probability !== null || r.calibration.interval !== null || r.provenance.independent_calibration !== false || typeof r.calibration.reason !== 'string') fail();
  if (!r.by_station_duration.every(p => p && IDS.includes(p.station_id!) && [1, 2, 3].includes(p.duration_hours!) && typeof p.split === 'string' && finite(p.cases) && finite(p.origins) && (p.lower_observed_fraction === null || finite(p.lower_observed_fraction))) || (r.reliability_profiles !== undefined && (!Array.isArray(r.reliability_profiles) || !r.reliability_profiles.every(p => p && IDS.includes(p.station_id) && finite(p.cases) && finite(p.origins))))) fail();
  const ids = new Set<string>();
  for (const c of r.cases) {
    if (!c || typeof c.case_id !== 'string' || ids.has(c.case_id) || !IDS.includes(c.station_id) || ![1, 2, 3].includes(c.duration_hours) || !Array.isArray(c.hours) || !c.hours.length || !Array.isArray(c.windows) || !c.windows.length || !c.original || !c.selected) fail();
    ids.add(c.case_id);
    if (![c.issue_time_ist, c.pm_history_cutoff_ist, c.last_pm_end_ist, c.original_start_ist, c.original_end_ist, c.selected_start_ist, c.selected_end_ist, c.feasible_start_ist, c.feasible_end_ist].every(validIst) || Date.parse(c.pm_history_cutoff_ist) > Date.parse(c.issue_time_ist) || Date.parse(c.last_pm_end_ist) > Date.parse(c.pm_history_cutoff_ist)) fail();
    let previous = -Infinity;
    for (const h of c.hours) {
      if (!h || !validIst(h.target_start_ist) || !validIst(h.target_end_ist) || Date.parse(h.target_start_ist) <= Date.parse(c.issue_time_ist) || Date.parse(h.target_start_ist) <= previous || Date.parse(h.target_end_ist) - Date.parse(h.target_start_ist) !== HOUR || !concentration(h.prediction) || (h.observed !== null && !concentration(h.observed))) fail();
      previous = Date.parse(h.target_start_ist);
    }
    const forecasts: ForecastHour[] = c.hours.map(h => ({ target_start_ist: h.target_start_ist, target_end_ist: h.target_end_ist, pm25_prediction: h.prediction, status: 'available', unit: 'µg/m³', forecast_horizon_hours: 1, prediction_interval: null }));
    const expected = enumerateWindows({ forecasts } as Station, c.feasible_start_ist, c.feasible_end_ist, c.duration_hours);
    if (expected.length !== c.windows.length || new Set(c.windows.map(w => w?.start_ist)).size !== expected.length) fail();
    for (const [i, w] of c.windows.entries()) {
      const e = expected.find(e => e.start_ist === w?.start_ist);
      // Python and JS summation can order effectively equal means differently.
      if (!w || !e || w.end_ist !== e.end_ist || w.rank !== i + 1 || !equal(w.mean_prediction, e.mean_prediction) || !equal(w.max_prediction, e.max_prediction) || (i > 0 && w.mean_prediction < c.windows[i - 1].mean_prediction - 1e-7)) fail();
    }
    for (const w of [c.original, c.selected, ...c.windows]) {
      const e = completeWindow(forecasts, w.start_ist, c.duration_hours);
      if (!e || e.end_ist !== w.end_ist || !equal(e.mean_prediction, w.mean_prediction) || !equal(e.max_prediction, w.max_prediction)) fail();
      const observed = c.hours.filter(h => h.target_start_ist >= w.start_ist && h.target_start_ist < w.end_ist).map(h => h.observed);
      if (observed.some(n => n === null) ? w.mean_observed !== null : !finite(w.mean_observed) || !equal(w.mean_observed, (observed as number[]).reduce((a, b) => a + b, 0) / c.duration_hours)) fail();
    }
    if (c.original.start_ist !== c.original_start_ist || c.original.end_ist !== c.original_end_ist || c.selected.start_ist !== c.selected_start_ist || c.selected.end_ist !== c.selected_end_ist || c.selected.start_ist !== (c.windows[0].mean_prediction < c.original.mean_prediction ? c.windows[0].start_ist : c.original.start_ist) || !equal(c.predicted_difference, c.selected.mean_prediction - c.original.mean_prediction)) fail();
    if (c.original.mean_observed === null || c.selected.mean_observed === null ? c.observed_difference !== null : !finite(c.observed_difference) || !equal(c.observed_difference, c.selected.mean_observed - c.original.mean_observed)) fail();
  }
  const paired = r.cases.filter(c => c.observed_difference !== null);
  const alternatives = paired.filter(c => c.selected_start_ist !== c.original_start_ist);
  if (r.summary.cases !== r.cases.length || r.summary.origins !== new Set(r.cases.map(c => c.fold_id)).size || r.summary.paired_outcome_cases !== paired.length || r.summary.missing_outcome_cases !== r.cases.length - paired.length || r.summary.selected_alternative_cases !== alternatives.length || r.summary.recommended_cases !== 0 || r.cases.some(c => c.decision_status === 'ROBUST IMPROVEMENT') || !equal(r.summary.lower_observed_fraction!, alternatives.filter(c => c.observed_difference! < 0).length / alternatives.length)) fail();
  return r;
}

export function validateBaselineComparison(value: unknown): BaselineComparison {
  const c = value as BaselineComparison;
  const fail = () => { throw new Error('Baseline comparison artifact is invalid. Rebuild it from the frozen replay.'); };
  const finiteOrNull = (n: unknown) => n === null || (typeof n === 'number' && Number.isFinite(n));
  if (!c || c.schema_version !== '1.0.0' || typeof c.source_replay_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(c.source_replay_sha256) || !c.method || !Array.isArray(c.limitations) || c.limitations.length < 3) fail();
  for (const panel of [c.full_replay, c.heldout]) {
    if (!panel || !Number.isInteger(panel.cases) || panel.cases < 0 || !Number.isInteger(panel.usual_cleanest_supported_cases) || panel.usual_cleanest_supported_cases < 0 || panel.usual_cleanest_supported_cases > panel.cases) fail();
    for (const result of [panel.usual_cleanest, panel.latest_window]) {
      if (!result || !Number.isInteger(result.paired_cases) || result.paired_cases < 0 || !Number.isInteger(result.origins) || result.origins < 0 || !finiteOrNull(result.airwindow_mean) || !finiteOrNull(result.baseline_mean) || !finiteOrNull(result.mean_delta) || !finiteOrNull(result.median_delta) || !Array.isArray(result.cluster_bootstrap_95) || result.cluster_bootstrap_95.length !== 2 || !result.cluster_bootstrap_95.every(finiteOrNull) || !['interval_below_zero', 'interval_above_zero', 'interval_includes_zero', 'unavailable'].includes(result.direction)) fail();
      if (result.paired_cases === 0 && (result.mean_delta !== null || result.cluster_bootstrap_95.some(v => v !== null))) fail();
      if (result.paired_cases > 0 && (result.mean_delta === null || result.cluster_bootstrap_95.some(v => v === null) || result.origins < 2)) fail();
    }
  }
  if (c.full_replay.cases !== 1848 || c.heldout.cases !== 192 || c.heldout.usual_cleanest_supported_cases !== c.heldout.cases) fail();
  return c;
}

export function validateForecast(value: unknown): ForecastArtifact {
  if (!value || typeof value !== 'object') throw new Error('Forecast artifact is not an object.');
  const a = value as ForecastArtifact;
  if (!['1.0.0', '1.1.0'].includes(a.schema_version)) throw new Error('Unsupported forecast schema.');
  if (!a.model || typeof a.model.id !== 'string' || typeof a.model.version !== 'string' || !a.weather || typeof a.weather.used !== 'boolean' || !a.uncertainty || typeof a.uncertainty.status !== 'string' || !a.stations || !Array.isArray(a.stations) || a.stations.length !== 4) throw new Error('Forecast artifact is missing required metadata.');
  const issue = Date.parse(a.model_issue_time_ist);
  const cutoff = Date.parse(a.pm_history_cutoff_ist);
  const generated = Date.parse(a.generated_at_ist);
  if (![a.model_issue_time_ist, a.pm_history_cutoff_ist, a.generated_at_ist].every(validIst)) throw new Error('Information timestamps must carry explicit IST offsets.');
  if (![issue, cutoff, generated].every(Number.isFinite) || cutoff > issue || generated < issue) throw new Error('Forecast information timestamps are invalid.');
  if (new Set(a.stations.map(s => s.station_id)).size !== 4 || !IDS.every(id => a.stations.some(s => s.station_id === id))) throw new Error('Forecast must contain the four challenge stations.');
  for (const s of a.stations) {
    if (!s.station_name || !s.freshness || !s.data_status || !Array.isArray(s.validation) || !Array.isArray(s.forecasts)) throw new Error('Station metadata is incomplete.');
    const coordinate = LOCATIONS[s.station_id];
    if (!coordinate || !Number.isFinite(s.latitude) || !Number.isFinite(s.longitude) || Math.abs(s.latitude-coordinate[0]) > 1e-6 || Math.abs(s.longitude-coordinate[1]) > 1e-6) throw new Error('Station coordinates do not match the challenge monitors.');
    if (s.last_observation_ist !== null && !validIst(s.last_observation_ist)) throw new Error('Observation time must carry an explicit IST offset.');
    if (s.last_observation_ist && Date.parse(s.last_observation_ist) > cutoff) throw new Error('Observation is after the PM history cutoff.');
    let previous = -Infinity;
    for (const h of s.forecasts) {
      const start = Date.parse(h.target_start_ist), end = Date.parse(h.target_end_ist);
      if (!validIst(h.target_start_ist) || !validIst(h.target_end_ist) || end - start !== HOUR || start <= issue || start <= previous || (previous !== -Infinity && start - previous !== HOUR)) throw new Error('Forecast hours must be future, unique and consecutive with IST offsets.');
      if (h.unit !== 'µg/m³') throw new Error('Forecast unit must be µg/m³.');
      if (!Number.isFinite(h.forecast_horizon_hours) || Math.abs((start - issue) / HOUR - h.forecast_horizon_hours) > 1e-6) throw new Error('Forecast lead does not match its issue time.');
      if (h.status === 'available' && (h.pm25_prediction === null || !Number.isFinite(h.pm25_prediction) || h.pm25_prediction < 0)) throw new Error('An available forecast has an invalid concentration.');
      if (h.status === 'missing' && h.pm25_prediction !== null) throw new Error('A missing forecast must remain missing.');
      if (!['missing', 'available'].includes(h.status)) throw new Error('Unknown forecast availability.');
      if (a.uncertainty.status !== 'calibrated' && h.prediction_interval !== null) throw new Error('Uncalibrated prediction interval must not be displayed.');
      previous = start;
    }
    const available = s.forecasts.filter(h => h.status === 'available').length;
    const missing = s.forecasts.filter(h => h.status === 'missing').map(h => h.target_start_ist);
    if (!s.forecasts.length || s.data_status.expected_forecast_hours !== s.forecasts.length || s.data_status.available_forecast_hours !== available || JSON.stringify(s.data_status.missing_target_starts_ist) !== JSON.stringify(missing)) throw new Error('Forecast completeness metadata does not match its records.');
  }
  return a;
}

export function completeWindow(forecasts: ForecastHour[], start: string, duration: number): TimeWindow | null {
  if (![1, 2, 3].includes(duration)) return null;
  const first = Date.parse(start);
  if (!Number.isFinite(first)) return null;
  if (new Set(forecasts.map(h => Date.parse(h.target_start_ist))).size !== forecasts.length) return null;
  const byTime = new Map(forecasts.map(h => [Date.parse(h.target_start_ist), h]));
  const hours: ForecastHour[] = [];
  for (let i = 0; i < duration; i++) {
    const row = byTime.get(first + i * HOUR);
    if (!row || row.status !== 'available' || row.pm25_prediction === null || !Number.isFinite(row.pm25_prediction) || row.pm25_prediction < 0 || Date.parse(row.target_end_ist) !== first + (i + 1) * HOUR) return null;
    hours.push(row);
  }
  const peak = hours.reduce((a, b) => a.pm25_prediction! >= b.pm25_prediction! ? a : b);
  return { start_ist: hours[0].target_start_ist, end_ist: hours.at(-1)!.target_end_ist,
    mean_prediction: hours.reduce((sum, h) => sum + h.pm25_prediction!, 0) / duration,
    max_prediction: peak.pm25_prediction!, peak_start_ist: peak.target_start_ist, hours, rank: 0 };
}

export function enumerateWindows(station: Station, earliest: string, latestEnd: string, duration: number): TimeWindow[] {
  if (![1, 2, 3].includes(duration)) throw new Error('Choose a one, two or three hour activity.');
  const left = Date.parse(earliest), right = Date.parse(latestEnd);
  if (!Number.isFinite(left) || !Number.isFinite(right) || right <= left) throw new Error('The feasible end must follow the earliest start.');
  if (right - left < duration * HOUR) throw new Error('The activity does not fit within your feasible range.');
  return station.forecasts.filter(h => Date.parse(h.target_start_ist) >= left && Date.parse(h.target_start_ist) + duration * HOUR <= right)
    .map(h => completeWindow(station.forecasts, h.target_start_ist, duration)).filter((w): w is TimeWindow => w !== null)
    .sort((a, b) => a.mean_prediction - b.mean_prediction || Date.parse(a.start_ist) - Date.parse(b.start_ist)).map((w, i) => ({ ...w, rank: i + 1 }));
}

// Choose a real, complete daytime comparison from the loaded artifact. Prefer
// 10:00 IST when it is still in the future; never fill missing forecast hours.
export function schoolSportsDayPlan(stations: Station[], now: number): { stationId: string; date: string; duration: number; original: string; earliest: string; latest: string } | null {
  const dates = [...new Set(stations.flatMap(s => s.forecasts.map(h => dateKey(h.target_start_ist))))].sort();
  let fallback: ReturnType<typeof schoolSportsDayPlan> = null;
  for (const date of dates) {
    for (const station of stations) {
      const day = station.forecasts.filter(h => dateKey(h.target_start_ist) === date && dateKey(h.target_end_ist) === date && h.target_start_ist.slice(11, 16) >= '08:00' && h.target_start_ist.slice(11, 16) < '18:00' && h.target_end_ist.slice(11, 16) <= '18:00' && Date.parse(h.target_start_ist) > now);
      if (day.length < 2) continue;
      const earliest = day[0].target_start_ist;
      const latest = day.at(-1)!.target_end_ist;
      const windows = enumerateWindows(station, earliest, latest, 2);
      if (windows.length < 2) continue;
      const original = [...windows].sort((a, b) => Math.abs(Number(a.start_ist.slice(11, 13)) - 10) - Math.abs(Number(b.start_ist.slice(11, 13)) - 10) || a.start_ist.localeCompare(b.start_ist))[0];
      const plan = { stationId: station.station_id, date, duration: 2, original: original.start_ist, earliest, latest };
      if (original.start_ist.slice(11, 16) === '10:00') return plan;
      fallback ??= plan;
    }
  }
  return fallback;
}

export function istDate(value: string): string { return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(value)); }
export function dateKey(value: string): string { return value.slice(0, 10); }
export function localTimestamp(date: string, hour: string): string { return `${date}T${hour}:00+05:30`; }
export function timeLabel(value: string): string { return new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', hour: 'numeric', minute: '2-digit', hour12: true }).format(new Date(value)); }
export function dateLabel(value: string): string { return new Intl.DateTimeFormat('en-IN', { timeZone: 'Asia/Kolkata', day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(value)); }
export function stampLabel(value: string | null): string { return value ? `${dateLabel(value)}, ${timeLabel(value)} IST` : 'Not available'; }
export function numberLabel(value: number | null | undefined, decimals = 1): string { return value === null || value === undefined || !Number.isFinite(value) ? 'Unavailable' : value.toLocaleString('en-IN', { maximumFractionDigits: decimals, minimumFractionDigits: decimals }); }
export function differenceLabel(value: number | null | undefined): string {
  return value === null || value === undefined || !Number.isFinite(value) ? 'Unavailable' : numberLabel(value, Math.abs(value) > 0 && Math.abs(value) < .1 ? 3 : 1);
}

export function isExpired(artifact: ForecastArtifact, now = Date.now()): boolean {
  return !artifact.stations.some(s => s.forecasts.some(h => h.status === 'available' && Date.parse(h.target_end_ist) > now));
}

export function matchedValidation(station: Station, window: TimeWindow, issueTime: string) {
  const observation = station.last_observation_ist;
  const all = station.validation.filter(v => v.status === 'measured' && v.rmse !== null && v.n_targets !== null);
  const benchmark = all.length ? `${Math.min(...all.map(v => v.horizon_hours))}–${Math.max(...all.map(v => v.horizon_hours))}h historical issue lead` : 'No historical benchmark';
  if (!observation) return { rmse: null, rows: 0, folds: 0, note: benchmark, matched: false };
  const requested = window.hours.map(h => (Date.parse(h.target_start_ist)-Date.parse(observation))/HOUR);
  const issueLeads = window.hours.map(h => (Date.parse(h.target_start_ist)-Date.parse(issueTime))/HOUR);
  const metrics = issueLeads.map(lead => all.find(v => Math.abs(v.horizon_hours-lead) < 1e-6));
  if (metrics.some(v => !v) || issueLeads.some((lead, i) => Math.abs(lead-requested[i]) > 1e-6)) return { rmse: null, rows: 0, folds: 0, note: `${benchmark}; current issue/PM clocks outside comparable evidence`, matched: false };
  const rows = metrics.reduce((sum, v) => sum + v!.n_targets!, 0);
  const rmse = Math.sqrt(metrics.reduce((sum, v) => sum + v!.rmse!**2*v!.n_targets!, 0)/rows);
  return { rmse, rows, folds: Math.max(...metrics.map(v => v!.folds || 0)), note: `${Math.min(...requested)}–${Math.max(...requested)}h PM lead; up to ${Math.max(...metrics.map(v => v!.folds || 0))} origins per lead`, matched: true };
}
