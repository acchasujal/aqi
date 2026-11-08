import type { ForecastArtifact, ForecastHour, Station, TimeWindow } from './types.ts';

const HOUR = 3_600_000;
const IDS = ['11606', '11611', '3409510', '3409511'];
const LOCATIONS: Record<string, [number, number]> = { '11606': [19.23241, 72.86895], '11611': [19.19709, 72.82204], '3409510': [18.9767, 72.838], '3409511': [19.060498, 72.923356] };
const validIst = (value: unknown): value is string => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+05:30$/.test(value) && Number.isFinite(Date.parse(value));

export function validateForecast(value: unknown): ForecastArtifact {
  if (!value || typeof value !== 'object') throw new Error('Forecast artifact is not an object.');
  const a = value as ForecastArtifact;
  if (!['1.0.0', '1.1.0'].includes(a.schema_version)) throw new Error('Unsupported forecast schema.');
  if (!a.model || !a.uncertainty || !a.stations || !Array.isArray(a.stations) || a.stations.length !== 4) throw new Error('Forecast artifact is missing required metadata.');
  const issue = Date.parse(a.model_issue_time_ist);
  const cutoff = Date.parse(a.pm_history_cutoff_ist);
  const generated = Date.parse(a.generated_at_ist);
  if (![a.model_issue_time_ist, a.pm_history_cutoff_ist, a.generated_at_ist].every(validIst)) throw new Error('Information timestamps must carry explicit IST offsets.');
  if (![issue, cutoff, generated].every(Number.isFinite) || cutoff > issue || generated < issue) throw new Error('Forecast information timestamps are invalid.');
  if (new Set(a.stations.map(s => s.station_id)).size !== 4 || !IDS.every(id => a.stations.some(s => s.station_id === id))) throw new Error('Forecast must contain the four challenge stations.');
  for (const s of a.stations) {
    if (!s.station_name || !s.freshness || !s.data_status || !Array.isArray(s.validation) || !Array.isArray(s.forecasts)) throw new Error('Station metadata is incomplete.');
    const coordinate = LOCATIONS[s.station_id];
    if (!coordinate || Math.abs(s.latitude-coordinate[0]) > 1e-6 || Math.abs(s.longitude-coordinate[1]) > 1e-6) throw new Error('Station coordinates do not match the challenge monitors.');
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
