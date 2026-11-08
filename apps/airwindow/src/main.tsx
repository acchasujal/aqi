import { StrictMode, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { ForecastArtifact, ForecastHour, ReplayArtifact, ReplayCase, Station, TimeWindow } from './types.ts';
import { completeWindow, dateKey, dateLabel, enumerateWindows, isExpired, matchedValidation, differenceLabel, numberLabel, stampLabel, timeLabel, validateForecast } from './domain.ts';
import './styles.css';

type Page = 'plan' | 'replay' | 'evidence';
type Plan = { stationId: string; date: string; duration: number; original: string; earliest: string; latest: string };
type Comparison = { plan: Plan; original: TimeWindow; windows: TimeWindow[]; best: TimeWindow; difference: number };
const STATION_SHORT: Record<string, string> = { '11606': 'Borivali East', '11611': 'Malad West', '3409510': 'Byculla', '3409511': 'Shivaji Nagar' };
const Clock = () => <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/></svg>;
const Arrow = () => <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M5 12h14m-5-5 5 5-5 5"/></svg>;
const Shield = () => <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6l8-3Z"/><path d="M12 8v5m0 3v1"/></svg>;
const Print = () => <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M7 8V3h10v5M7 16H4V9h16v7h-3M7 13h10v8H7z"/></svg>;

function defaultPlan(station: Station): Plan {
  const futureHours = station.forecasts.filter(h => Date.parse(h.target_start_ist) > Date.now());
  const dates = [...new Set(futureHours.map(h => dateKey(h.target_start_ist)))];
  const date = dates.find(d => futureHours.filter(h => dateKey(h.target_start_ist) === d && h.status === 'available').length >= 20) || dates[0] || '';
  const hours = futureHours.filter(h => dateKey(h.target_start_ist) === date);
  const original = hours.find(h => h.target_start_ist.slice(11, 16) === '10:00') || hours[0];
  const first = hours.find(h => h.target_start_ist.slice(11, 16) === '08:00') || hours[0];
  const end = hours.find(h => h.target_end_ist.slice(11, 16) === '18:00')?.target_end_ist || hours.at(-1)?.target_end_ist;
  return { stationId: station.station_id, date, duration: 2, original: original?.target_start_ist || '', earliest: first?.target_start_ist || '', latest: end || '' };
}

function App() {
  const [artifact, setArtifact] = useState<ForecastArtifact | null>(null);
  const [replay, setReplay] = useState<ReplayArtifact | null>(null);
  const [loadError, setLoadError] = useState('');
  const [replayError, setReplayError] = useState('');
  const [page, setPage] = useState<Page>('plan');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [formError, setFormError] = useState('');
  const [brief, setBrief] = useState(false);
  const resultsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('./data/forecast.json', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error(`Forecast file could not be loaded (${r.status}).`);
      return r.json();
    }).then(raw => {
      const data = validateForecast(raw);
      setArtifact(data);
      setPlan(defaultPlan(data.stations[0]));
    }).catch((error: Error) => { if (error.name !== 'AbortError') setLoadError(error.message); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (page === 'plan' && !comparison) return;
    if (replay || replayError) return;
    const controller = new AbortController();
    fetch('./data/replay.json', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error('The historical replay artifact is unavailable.');
      return r.json();
    }).then((data: ReplayArtifact) => {
      if (data.schema_version !== '1.0.0' || !Array.isArray(data.cases) || !data.calibration || !data.summary) throw new Error('Replay metadata is invalid.');
      setReplay(data);
    }).catch((error: Error) => { if (error.name !== 'AbortError') setReplayError(error.message); });
    return () => controller.abort();
  }, [page, comparison, replay, replayError]);

  const station = artifact?.stations.find(s => s.station_id === plan?.stationId);
  const comparedStation = artifact?.stations.find(s => s.station_id === comparison?.plan.stationId);
  const dates = useMemo(() => station ? [...new Set(station.forecasts.filter(h => Date.parse(h.target_start_ist) > Date.now()).map(h => dateKey(h.target_start_ist)))] : [], [station]);
  const dayHours = station?.forecasts.filter(h => dateKey(h.target_start_ist) === plan?.date && Date.parse(h.target_start_ist) > Date.now()) || [];
  const expired = artifact ? isExpired(artifact) : false;

  function compare(event?: React.FormEvent) {
    event?.preventDefault();
    if (!plan || !station) return;
    try {
      if (expired) throw new Error('This forecast period has ended. Use Historical replay or load a newer artifact.');
      if (Date.parse(plan.original) <= Date.now()) throw new Error('The original activity start has already passed. Choose a future slot or explore Historical replay.');
      const original = completeWindow(station.forecasts, plan.original, plan.duration);
      if (!original) throw new Error('The original activity needs complete forecast hours. Choose another start or a shorter duration.');
      if (Date.parse(plan.earliest) <= Date.now()) throw new Error('The feasible range begins in the past. Choose a future start or explore Historical replay.');
      const windows = enumerateWindows(station, plan.earliest, plan.latest, plan.duration);
      if (!windows.length) throw new Error('No complete consecutive forecast windows fit this range. Missing hours are never filled.');
      const best = windows[0];
      const originalRank = windows.find(w => w.start_ist === original.start_ist)?.rank || 0;
      setComparison({ plan: { ...plan }, original: { ...original, rank: originalRank }, windows, best, difference: best.mean_prediction - original.mean_prediction });
      setFormError('');
      setBrief(false);
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 30);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not compare this activity.');
      setComparison(null);
    }
  }

  function updatePlan(change: Partial<Plan>) {
    if (plan) setPlan({ ...plan, ...change });
    setComparison(null); setBrief(false); setFormError('');
  }

  function changeStation(id: string) {
    const s = artifact?.stations.find(item => item.station_id === id);
    if (s) { setPlan(defaultPlan(s)); setComparison(null); setFormError(''); }
  }
  function changeDate(date: string) {
    if (!station || !plan) return;
    const dateStation = { ...station, forecasts: station.forecasts.filter(h => dateKey(h.target_start_ist) === date) };
    setPlan({ ...defaultPlan(dateStation), duration: plan.duration });
    setComparison(null);
  }

  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header no-print"><div className="header-inner">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('plan'); }} aria-label="AirWindow home"><span className="brand-mark"><i/><i/><i/></span><span>AirWindow<span className="brand-city">MUMBAI</span></span><span className="version-pill">2.0</span></a>
      <nav aria-label="Main navigation">{(['plan', 'replay', 'evidence'] as Page[]).map(p => <button key={p} className={page === p ? 'nav-active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => { setPage(p); setBrief(false); }}>{p === 'plan' ? 'Plan an activity' : p === 'replay' ? 'Historical replay' : 'Evidence & sources'}</button>)}</nav>
      <span className="header-caption"><span className="status-dot"/> Independent challenge prototype</span>
    </div></header>

    <main id="main" className={brief ? 'main brief-open' : 'main'}>
      {loadError ? <section className="load-state"><Shield/><p className="eyebrow">Forecast unavailable</p><h1>A plan needs real data.</h1><p>{loadError}</p><p>No substitute forecast has been generated. Check the versioned forecast artifact and rebuild the application.</p><button className="primary-button" onClick={() => location.reload()}>Try again</button></section>
      : !artifact || !plan ? <section className="load-state" aria-live="polite"><div className="loading-ring"/><p>Loading the forecast and its evidence…</p></section>
      : page === 'plan' ? <>
        <section className="hero no-print"><div className="hero-copy"><p className="eyebrow"><span/> A LITTLE MORE ROOM TO PLAN</p><h1>Should you move<br/>your outdoor event?</h1><p className="hero-description">Compare the hours that work for you.<br/>See the forecast difference. Know when the evidence is too thin to change your plan.</p></div>
          <div className="hero-note"><span className="note-kicker">THE AIRWINDOW APPROACH</span><div className="small-orbit"><span/><span/><span/></div><p>A lower number<br/>is a starting point.<br/><strong>Evidence comes next.</strong></p><a href="#how-it-works" onClick={e => { e.preventDefault(); setPage('evidence'); }}>Why we sometimes abstain <span>↗</span></a></div>
        </section>

        <div className="snapshot-bar no-print"><span className="snapshot-label"><Clock/> Forecast snapshot</span><span>Issued {stampLabel(artifact.model_issue_time_ist)}</span><span className="snapshot-divider"/><span>Four monitored stations · hourly PM2.5</span><span className="snapshot-tag">{expired ? 'Forecast period ended' : 'Frozen forecast snapshot'}</span></div>

        {expired && <div className="form-error no-print" role="status">This frozen forecast period has ended. New planning is disabled until a newer artifact is exported. <button className="text-button" onClick={() => setPage('replay')}>Explore historical replay ?</button></div>}

        {station && <section className="planner no-print" aria-labelledby="planner-heading"><div className="section-heading"><div><p className="eyebrow">01 / YOUR EVENT</p><h2 id="planner-heading">Start with the plan you already have.</h2></div><span className="quiet-tag">All times in IST · UTC+05:30</span></div>
          <form onSubmit={compare}>
            <div className="form-grid">
              <label className="station-field">Monitoring station<select value={plan.stationId} onChange={e => changeStation(e.target.value)}>{artifact.stations.map(s => <option key={s.station_id} value={s.station_id}>{STATION_SHORT[s.station_id] || s.station_name}</option>)}</select></label>
              <label>Planning date<select value={plan.date} onChange={e => changeDate(e.target.value)}>{dates.map(d => <option key={d} value={d}>{dateLabel(`${d}T12:00:00+05:30`)}</option>)}</select></label>
              <label>Activity duration<select value={plan.duration} onChange={e => updatePlan({ duration: Number(e.target.value) })}>{[1, 2, 3].map(d => <option key={d} value={d}>{d} {d === 1 ? 'hour' : 'hours'}</option>)}</select></label>
              <label>Original start<select value={plan.original} onChange={e => updatePlan({ original: e.target.value })}>{dayHours.map(h => <option key={h.target_start_ist} value={h.target_start_ist}>{timeLabel(h.target_start_ist)}</option>)}</select></label>
              <label>Earliest feasible start<select value={plan.earliest} onChange={e => updatePlan({ earliest: e.target.value })}>{dayHours.map(h => <option key={h.target_start_ist} value={h.target_start_ist}>{timeLabel(h.target_start_ist)}</option>)}</select></label>
              <label>Latest feasible end<select value={plan.latest} onChange={e => updatePlan({ latest: e.target.value })}>{dayHours.map(h => <option key={h.target_end_ist} value={h.target_end_ist}>{timeLabel(h.target_end_ist)}{dateKey(h.target_end_ist) !== plan.date ? ' (+1 day)' : ''}</option>)}</select></label>
            </div>
            <div className="form-bottom"><div className="station-detail"><span className="location-pin">◎</span><p><strong>{station.station_name}</strong><span>Station {station.station_id} · {station.latitude.toFixed(5)}° N, {station.longitude.toFixed(5)}° E<br/>Last PM observation: {stampLabel(station.last_observation_ist)}</span></p></div><button className="primary-button" type="submit">Compare time windows <Arrow/></button></div>
            {formError && <p className="form-error" role="alert">{formError}</p>}
          </form>
        </section>}

        {!comparison && <section className="how-strip no-print"><div className="how-number">01</div><div><h3>Keep the original in view.</h3><p>We compare complete, consecutive forecast hours with your existing schedule.</p></div><div className="how-number">02</div><div><h3>Let evidence have a say.</h3><p>A better-ranked forecast is never presented as a guarantee or a health recommendation.</p></div></section>}

        {comparison && comparedStation && <div ref={resultsRef} className="comparison-area">
          <div className="section-heading no-print"><div><p className="eyebrow">02 / THE COMPARISON</p><h2>Your original. A possible alternative.</h2></div><button className="text-button" onClick={() => { setBrief(true); setTimeout(() => document.getElementById('event-brief')?.scrollIntoView({ behavior: 'smooth' }), 30); }}><Print/> Create event brief</button></div>
          <div className="decision-banner no-print"><span className="decision-icon"><Shield/></span><div><span className="decision-label">{comparison.difference >= 0 ? 'NO CLEAR WINNER' : 'INSUFFICIENT EVIDENCE'}</span><h3>{comparison.difference >= 0 ? 'Your current slot is already as well ranked.' : 'A lower forecast. An unproven scheduling improvement.'}</h3><p>{comparison.difference >= 0 ? 'No feasible alternative has a lower predicted mean than your original schedule.' : `The best alternative is ${differenceLabel(-comparison.difference)} µg/m³ lower in the forecast. Independent, comparable decision calibration is unavailable, so AirWindow abstains from recommending a move.`}</p></div><span className="uncalibrated-tag">No calibrated probability</span></div>
          <div className="comparison-grid no-print"><WindowCard title="Original schedule" window={comparison.original} original/><WindowCard title={comparison.best.start_ist === comparison.original.start_ist ? 'Best-ranked feasible window' : 'Best predicted alternative'} window={comparison.best} difference={comparison.difference}/></div>
          <section className="trajectory-section no-print"><div className="section-heading"><div><p className="eyebrow">THE SHAPE OF THE DAY</p><h3>Hourly forecast, in context</h3></div><span className="chart-legend"><i/> Forecast PM2.5 <span>µg/m³</span></span></div><HourlyChart forecasts={comparedStation.forecasts.filter(h => dateKey(h.target_start_ist) === comparison.plan.date)} original={comparison.original} best={comparison.best}/><p className="chart-caption">Shading marks the original and best-ranked windows. These are forecast concentrations at the monitor, not personal exposure.</p></section>
          <ReliabilityPanel artifact={artifact} station={comparedStation} comparison={comparison} replay={replay}/>
          <section className="alternatives no-print"><div className="section-heading"><div><p className="eyebrow">KEEP YOUR OPTIONS OPEN</p><h3>All feasible windows</h3></div><span className="quiet-tag">{comparison.windows.length} complete {comparison.plan.duration}-hour windows</span></div><div className="table-scroll"><table><thead><tr><th>Rank</th><th>Activity window · IST</th><th>Forecast mean</th><th>Highest hour</th><th>Vs original</th></tr></thead><tbody>{comparison.windows.map(w => <tr key={w.start_ist} className={w.start_ist === comparison.original.start_ist ? 'original-row' : ''}><td><span className={w.rank === 1 ? 'rank rank-first' : 'rank'}>{w.rank.toString().padStart(2, '0')}</span></td><td>{timeLabel(w.start_ist)} – {timeLabel(w.end_ist)}{w.start_ist === comparison.original.start_ist && <span className="row-tag">Original</span>}</td><td>{numberLabel(w.mean_prediction)} <small>µg/m³</small></td><td>{numberLabel(w.max_prediction)} <small>µg/m³</small></td><td className={w.mean_prediction < comparison.original.mean_prediction ? 'lower-value' : ''}>{w.mean_prediction === comparison.original.mean_prediction ? '—' : `${w.mean_prediction < comparison.original.mean_prediction ? '−' : '+'}${differenceLabel(Math.abs(w.mean_prediction - comparison.original.mean_prediction))}`} <small>{w.mean_prediction === comparison.original.mean_prediction ? '' : 'µg/m³'}</small></td></tr>)}</tbody></table></div>{!comparison.original.rank && <p className="panel-note">Your original schedule is outside the feasible move range and remains visible above.</p>}</section>
          {brief && <EventBrief artifact={artifact} station={comparedStation} comparison={comparison} onClose={() => setBrief(false)}/>}
        </div>}
        <section className="boundary-note no-print"><span>FOUR STATIONS. CLEAR LIMITS.</span><p>A monitoring station may not represent nearby streets, a school ground, or your exact location. This is an independent planning prototype. For health recommendations, consult <a href="https://cpcb.nic.in/" target="_blank" rel="noreferrer">official CPCB guidance ↗</a>.</p></section>
      </> : page === 'replay' ? <ReplayView replay={replay} error={replayError}/> : <EvidenceView artifact={artifact} replay={replay}/>}
    </main>
    <footer className="site-footer no-print"><div><span className="footer-brand">AirWindow Mumbai</span><p>Better-timed plans. Clearly stated limits.</p></div><div><a href="https://github.com/acchasujal/aqi/tree/feature/task008-final-gap-execution" target="_blank" rel="noreferrer">Source & methodology ↗</a><span>Built for the Google Mumbai Data Challenge · 2026</span></div></footer>
  </>;
}

function WindowCard({ title, window, original = false, difference }: { title: string; window: TimeWindow; original?: boolean; difference?: number }) {
  return <article className={`window-card ${original ? 'window-original' : 'window-alternative'}`}><div className="window-card-top"><span>{title}</span><span className="window-badge">{original ? 'YOUR PLAN' : `RANK ${window.rank.toString().padStart(2, '0')}`}</span></div><h3>{timeLabel(window.start_ist)}<span> — </span>{timeLabel(window.end_ist)}</h3><p className="window-date">{dateLabel(window.start_ist)} · IST</p><div className="window-value"><strong>{numberLabel(window.mean_prediction)}</strong><span>µg/m³<br/>predicted mean</span></div>{difference !== undefined && <p className="delta-line">{difference < 0 ? `↓ ${differenceLabel(-difference)} µg/m³ lower than original` : difference > 0 ? `↑ ${differenceLabel(difference)} µg/m³ above original` : 'Same predicted mean as original'}</p>}<div className="window-divider"/><div className="window-details"><span>Highest forecast hour<strong>{numberLabel(window.max_prediction)} µg/m³</strong></span><span>Peak interval starts<strong>{timeLabel(window.peak_start_ist)} IST</strong></span></div><div className="hour-chips">{window.hours.map(h => <span key={h.target_start_ist}>{timeLabel(h.target_start_ist)} <strong>{numberLabel(h.pm25_prediction)}</strong><small>µg/m³</small></span>)}</div></article>;
}

function HourlyChart({ forecasts, original, best }: { forecasts: ForecastHour[]; original?: TimeWindow; best?: TimeWindow }) {
  const values = forecasts.map(h => h.pm25_prediction).filter((v): v is number => v !== null && Number.isFinite(v));
  if (!values.length) return <p>No complete hourly forecast is available.</p>;
  const width = 1000, height = 220, left = 45, right = 20, top = 15, bottom = 34;
  const max = Math.max(...values, 1) * 1.18;
  const x = (i: number) => left + (width - left - right) * i / Math.max(forecasts.length - 1, 1);
  const y = (v: number) => height - bottom - (height - top - bottom) * v / max;
  const segments: string[] = []; let current = '';
  forecasts.forEach((h, i) => { if (h.status === 'available' && h.pm25_prediction !== null) current += `${current ? ' L' : 'M'}${x(i)},${y(h.pm25_prediction)}`; else { if (current) segments.push(current); current = ''; } });
  if (current) segments.push(current);
  const range = (w?: TimeWindow) => { if (!w) return null; const indices = forecasts.flatMap((h, i) => Date.parse(h.target_start_ist) >= Date.parse(w.start_ist) && Date.parse(h.target_start_ist) < Date.parse(w.end_ist) ? [i] : []); return indices.length ? { x: x(indices[0]) - 12, width: x(indices.at(-1)!) - x(indices[0]) + 24 } : null; };
  const o = range(original), b = range(best);
  return <div className="hourly-chart"><svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Hourly forecast PM2.5 chart. Exact values are available in the table below.">{[0, 1, 2, 3].map(i => { const value = max * i / 3; return <g key={i}><line x1={left} y1={y(value)} x2={width-right} y2={y(value)} className="chart-grid"/><text x={left-10} y={y(value)+4} textAnchor="end">{Math.round(value)}</text></g>; })}{o && <rect x={o.x} y={top} width={o.width} height={height-top-bottom} className="original-shade"/>}{b && <rect x={b.x} y={top} width={b.width} height={height-top-bottom} className="best-shade"/>}{segments.map((d, i) => <path key={i} d={d} className="forecast-line"/>)}{forecasts.map((h, i) => <g key={h.target_start_ist}>{h.pm25_prediction !== null && h.status === 'available' && <circle cx={x(i)} cy={y(h.pm25_prediction)} r="3.5" className="forecast-dot"><title>{timeLabel(h.target_start_ist)} IST: {numberLabel(h.pm25_prediction)} µg/m³ forecast</title></circle>}{i % 3 === 0 && <text x={x(i)} y={height-9} textAnchor="middle">{timeLabel(h.target_start_ist)}</text>}</g>)}</svg><details className="chart-data"><summary>Read all hourly values</summary><div className="hourly-values">{forecasts.map(h => <span key={h.target_start_ist}><strong>{timeLabel(h.target_start_ist)} IST</strong>{h.pm25_prediction === null ? 'Missing forecast' : `${numberLabel(h.pm25_prediction)} µg/m³ forecast`}</span>)}</div></details></div>;
}

function ReliabilityPanel({ artifact, station, comparison, replay }: { artifact: ForecastArtifact; station: Station; comparison: Comparison; replay: ReplayArtifact | null }) {
  const profiles = replay?.reliability_profiles?.filter(p => p.station_id === station.station_id && p.duration_hours === comparison.plan.duration) || [];
  const lead = (Date.parse(comparison.best.start_ist) - Date.parse(artifact.model_issue_time_ist)) / 3_600_000;
  const pmLead = (Date.parse(comparison.best.start_ist) - Date.parse(station.last_observation_ist || artifact.pm_history_cutoff_ist)) / 3_600_000;
  const matching = profiles.find(p => lead >= p.lead_min_hours && lead <= p.lead_max_hours && pmLead >= p.pm_lead_min_hours && pmLead <= p.pm_lead_max_hours);
  const validation = matchedValidation(station, comparison.best, artifact.model_issue_time_ist);
  return <section className="reliability-panel no-print" aria-labelledby="reliability-heading"><div><p className="eyebrow">03 / BEFORE YOU CHANGE ANYTHING</p><h2 id="reliability-heading">Can you trust this comparison?</h2><p>Historical forecast accuracy and a reliable scheduling decision are different questions. We keep both visible.</p><div className="evidence-status"><Shield/><span>Decision calibration <strong>Not independently validated</strong></span></div></div><div className="evidence-grid"><div><span>Comparable decision cases</span><strong>{matching ? matching.cases.toLocaleString('en-IN') : 'Not established'}</strong><small>{matching ? `${matching.origins} origins · descriptive evidence only` : 'Station, duration and both information clocks must match'}</small></div><div><span>Station validation RMSE</span><strong>{numberLabel(validation?.rmse)} <small>µg/m³</small></strong><small>{validation.matched ? `${validation.rows.toLocaleString('en-IN')} labels · ${validation.note} · full target` : validation.note}</small></div><div><span>Forecast lead for alternative</span><strong>{numberLabel(lead)} <small>hours from issue</small></strong><small>{numberLabel(pmLead)} hours from last PM observation</small></div><div><span>Uncertainty intervals</span><strong>Not shown</strong><small>No independently validated decision probability or forecast interval</small></div></div><p className="reliability-footnote">{matching ? `Comparable historical paired-difference errors are descriptive; they do not establish that this live alternative will be better. ${replay?.calibration.reason || ''}` : 'The available historical decision cases do not establish comparable, independently calibrated evidence for this live issue time and PM age. A numerically lower forecast alone does not justify a confident recommendation.'}</p></section>;
}

function EventBrief({ artifact, station, comparison, onClose }: { artifact: ForecastArtifact; station: Station; comparison: Comparison; onClose: () => void }) {
  const metric = matchedValidation(station, comparison.best, artifact.model_issue_time_ist);
  return <section id="event-brief" className="event-brief"><div className="brief-toolbar no-print"><span>Your event brief</span><div><button className="text-button" onClick={onClose}>Close brief</button><button className="primary-button" onClick={() => window.print()}><Print/> Print / save PDF</button></div></div><div className="brief-paper"><div className="brief-masthead"><span className="footer-brand">AirWindow Mumbai</span><span>EVENT PLANNING BRIEF</span></div><h2>A plan, with its evidence attached.</h2><p className="brief-station">{STATION_SHORT[station.station_id]} · {dateLabel(comparison.original.start_ist)} · {comparison.plan.duration}-hour activity</p><div className="brief-status"><strong>{comparison.difference >= 0 ? 'NO CLEAR WINNER' : 'INSUFFICIENT EVIDENCE'}</strong><p>{comparison.difference >= 0 ? 'The original is already as well ranked as the alternatives.' : 'The alternative has a lower predicted concentration. AirWindow abstains from recommending a move because decision reliability has not been independently validated.'}</p></div><div className="brief-comparison"><div><span>Original schedule</span><h3>{timeLabel(comparison.original.start_ist)} – {timeLabel(comparison.original.end_ist)} IST</h3><p><strong>{numberLabel(comparison.original.mean_prediction)}</strong> µg/m³ forecast mean</p><small>Highest hour: {numberLabel(comparison.original.max_prediction)} µg/m³</small></div><div><span>Best predicted alternative</span><h3>{timeLabel(comparison.best.start_ist)} – {timeLabel(comparison.best.end_ist)} IST</h3><p><strong>{numberLabel(comparison.best.mean_prediction)}</strong> µg/m³ forecast mean</p><small>Highest hour: {numberLabel(comparison.best.max_prediction)} µg/m³</small></div></div><p className="brief-difference">Predicted difference: <strong>{comparison.difference < 0 ? '−' : comparison.difference > 0 ? '+' : ''}{differenceLabel(Math.abs(comparison.difference))} µg/m³</strong> · selected minus original</p><dl className="brief-meta"><div><dt>Forecast issued</dt><dd>{stampLabel(artifact.model_issue_time_ist)}</dd></div><div><dt>Latest PM observation</dt><dd>{stampLabel(station.last_observation_ist)}</dd></div><div><dt>Model</dt><dd>{artifact.model.id} · {artifact.model.version}</dd></div><div><dt>Station</dt><dd>{station.station_id} · {station.latitude.toFixed(5)}, {station.longitude.toFixed(5)}</dd></div><div><dt>Validation</dt><dd>{metric.matched ? `${numberLabel(metric.rmse)} µg/m³ full-target RMSE; ${metric.note}; not decision calibration` : `Matched station validation unavailable. ${metric.note}`}</dd></div><div><dt>Artifact</dt><dd>{artifact.artifact_id}</dd></div></dl><p className="brief-disclaimer">Monitoring-station forecasts may not represent nearby streets or the event location. No period is labelled safe or medically recommended. This comparison is not a personal exposure estimate. Refer to official CPCB/government guidance for health recommendations.</p><div className="brief-end">Independent Google Mumbai Data Challenge prototype · All times IST · Hourly PM2.5, µg/m³</div></div></section>;
}

function ReplayView({ replay, error }: { replay: ReplayArtifact | null; error: string }) {
  const [stationId, setStationId] = useState('11606');
  const [duration, setDuration] = useState(2);
  const [caseId, setCaseId] = useState('');
  const cases = replay?.cases.filter(c => c.station_id === stationId && c.duration_hours === duration) || [];
  const item = cases.find(c => c.case_id === caseId) || cases.at(-1);
  return <section className="replay-page"><p className="eyebrow">HISTORICAL DECISION REPLAY</p><h1>Would the move<br/>have worked?</h1><p className="page-intro">Revisit historical forecast simulations and later observations. Generated retrospectively with history frozen at the recorded origin. Every eligible historical case counts, including the moves that did not work.</p><span className="retrospective-tag">Retrospective evaluation · released historical observations</span>
    {!replay ? <div className="empty-panel"><h2>Replay is unavailable.</h2><p>{error || 'Loading genuine OOF forecasts…'}</p><p>No historical outcomes have been invented.</p></div> : <><div className="replay-summary"><div><span>Eligible historical cases</span><strong>{replay.summary.cases.toLocaleString('en-IN')}</strong><small>{replay.summary.origins} origins; {replay.summary.paired_outcome_cases} paired outcomes; {replay.summary.missing_outcome_cases} missing</small></div><div><span>Lower observed concentration</span><strong>{replay.summary.lower_observed_fraction === null ? 'Unavailable' : `${numberLabel(replay.summary.lower_observed_fraction * 100)}%`}</strong><small>{replay.summary.selected_alternative_cases} numerical alternatives with outcomes; descriptive rate</small></div><div><span>Median realised difference</span><strong>{numberLabel(replay.summary.median_realised_difference)} <small>µg/m³</small></strong><small>Selected minus original · negative is lower</small></div><div><span>Median hindsight gap</span><strong>{numberLabel(replay.summary.hindsight_gap_median)} <small>µg/m³</small></strong><small>Selected minus best actually observed feasible slot</small></div></div>
      <p className="replay-warning"><Shield/> No schedule changes were endorsed as calibrated recommendations. These are historical outcomes, not a calibrated probability for your next event. {replay.calibration.reason}</p>
      <div className="replay-controls"><label>Station<select aria-label="Station" value={stationId} onChange={e => { setStationId(e.target.value); setCaseId(''); }}>{Object.entries(STATION_SHORT).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label>Duration<select aria-label="Duration" value={duration} onChange={e => { setDuration(Number(e.target.value)); setCaseId(''); }}>{[1, 2, 3].map(d => <option key={d} value={d}>{d} {d === 1 ? 'hour' : 'hours'}</option>)}</select></label><label>Historical forecast case<select aria-label="Historical forecast case" value={item?.case_id || ''} onChange={e => setCaseId(e.target.value)}>{cases.map(c => <option key={c.case_id} value={c.case_id}>{dateLabel(c.original_start_ist)} · {timeLabel(c.original_start_ist)} · {c.split}</option>)}</select></label></div>
      {item ? <ReplayCaseView item={item}/> : <div className="empty-panel"><h2>No eligible case for this selection.</h2><p>Missing historical forecasts or observations are not filled.</p></div>}
      <details className="method-details"><summary>See the replay design and all station/duration results</summary><p>Predeclared school-event scenarios use the original 09:00 slot and feasible 08:00–18:00 range on each available target day. One-, two- and three-hour activities are evaluated. The selected window is chosen using forecasts only; observed outcomes are joined afterwards. Historical publication timing is proxied by interval end. Cases and outcomes are retained even when the selected alternative is worse.</p><div className="table-scroll"><table><thead><tr><th>Station</th><th>Duration</th><th>Split</th><th>Cases</th><th>Origins</th><th>Lower observed</th><th>Median difference</th></tr></thead><tbody>{replay.by_station_duration.map((r, i) => <tr key={i}><td>{STATION_SHORT[r.station_id || ''] || r.station_id}</td><td>{r.duration_hours}h</td><td>{r.split}</td><td>{r.cases}</td><td>{r.origins}</td><td>{r.lower_observed_fraction === null ? 'Unavailable' : `${numberLabel(r.lower_observed_fraction * 100)}%`}</td><td>{numberLabel(r.median_realised_difference)} µg/m³</td></tr>)}</tbody></table></div></details></>}
  </section>;
}

function ReplayCaseView({ item }: { item: ReplayCase }) {
  const max = Math.max(...item.hours.flatMap(h => [h.prediction, h.observed]).filter((v): v is number => v !== null && Number.isFinite(v)), 1);
  return <section className="replay-case"><div className="section-heading"><div><p className="eyebrow">HISTORICAL FORECAST SIMULATION</p><h2>{STATION_SHORT[item.station_id]} · {dateLabel(item.original_start_ist)}</h2></div><span className="quiet-tag">{item.split} origin</span></div><div className="replay-clock"><span>Simulated issue/origin <strong>{stampLabel(item.issue_time_ist)}</strong></span><span>PM cutoff <strong>{stampLabel(item.pm_history_cutoff_ist)}</strong></span></div><div className="replay-outcome"><div><span>Original forecast / actual</span><h3>{timeLabel(item.original_start_ist)} – {timeLabel(item.original_end_ist)} IST</h3><p><strong>{numberLabel(item.original.mean_prediction)}</strong><span>forecast</span><strong className="observed-color">{numberLabel(item.original.mean_observed)}</strong><span>observed µg/m³</span></p></div><Arrow/><div><span>Selected forecast / actual</span><h3>{timeLabel(item.selected_start_ist)} – {timeLabel(item.selected_end_ist)} IST</h3><p><strong>{numberLabel(item.selected.mean_prediction)}</strong><span>forecast</span><strong className="observed-color">{numberLabel(item.selected.mean_observed)}</strong><span>observed µg/m³</span></p></div></div><div className="outcome-verdict"><span>{item.observed_difference === null ? 'OBSERVED COMPARISON UNAVAILABLE' : item.observed_difference < 0 ? 'LOWER AFTERWARDS' : item.observed_difference > 0 ? 'HIGHER AFTERWARDS' : 'NO OBSERVED DIFFERENCE'}</span>{item.observed_difference === null ? <p>Complete subsequent observations are unavailable for this paired comparison. This case remains in the record; missing values are never zero-filled.</p> : <p>The selected slot was <strong>{numberLabel(Math.abs(item.observed_difference))} µg/m³ {item.observed_difference < 0 ? 'lower' : item.observed_difference > 0 ? 'higher' : 'different'}</strong> in subsequently observed mean PM2.5. This is a retrospective outcome, not a measured health benefit.</p>}</div><div className="replay-hour-grid">{item.hours.map(h => <div key={h.target_start_ist}><span>{timeLabel(h.target_start_ist)}</span><div className="paired-bars"><i style={{ height: `${Math.max(h.prediction / max * 100, 1)}%` }} title={`Forecast ${numberLabel(h.prediction)} µg/m³`}/>{h.observed !== null && <i style={{ height: `${Math.max(h.observed / max * 100, 1)}%` }} title={`Observed ${numberLabel(h.observed)} µg/m³`}/>}</div><small><b>{numberLabel(h.prediction)}</b> forecast<br/><b className="observed-color">{numberLabel(h.observed)}</b> observed<br/>µg/m³</small></div>)}</div><p className="chart-caption"><span className="mini-key forecast-key"/> Forecast at issue <span className="mini-key observed-key"/> Observation recorded later · All hourly intervals in IST</p><p className="panel-note">Origin {item.fold_id} · Decision state at issue: {item.decision_status.replaceAll('_', ' ')} · Hindsight gap: {numberLabel(item.hindsight_gap)} µg/m³</p></section>;
}

function EvidenceView({ artifact, replay }: { artifact: ForecastArtifact; replay: ReplayArtifact | null }) {
  return <section className="evidence-page"><p className="eyebrow">EVIDENCE, WITHOUT THE FINE PRINT</p><h1>Know what the<br/>forecast can support.</h1><p className="page-intro">AirWindow helps a school coordinator compare possible schedules. The measurements, model forecast and historical evaluation each have a different role.</p><div className="evidence-thesis"><Shield/><div><h2>Abstention is part of the product.</h2><p>A lower predicted concentration is not enough to prove that moving an event will help. We require paired historical decisions at comparable stations, durations and information ages, evaluated on independent chronological origins, before showing a calibrated recommendation.</p><strong>Current decision calibration: {replay?.calibration.status.replaceAll('_', ' ') || 'not available'}</strong></div></div><div className="trust-columns"><section><p className="eyebrow">THE FORECAST</p><h2>A versioned artifact.<br/>A traceable model.</h2><dl><div><dt>Model</dt><dd>{artifact.model.id}</dd></div><div><dt>Version</dt><dd>{artifact.model.version}</dd></div><div><dt>Issued</dt><dd>{stampLabel(artifact.model_issue_time_ist)}</dd></div><div><dt>PM history cutoff</dt><dd>{stampLabel(artifact.pm_history_cutoff_ist)}</dd></div><div><dt>Generated</dt><dd>{stampLabel(artifact.generated_at_ist)}</dd></div><div><dt>Weather inputs</dt><dd>{artifact.weather.used ? `${artifact.weather.provider} · ${artifact.weather.model}` : 'Not used'}</dd></div><div><dt>Forecast intervals</dt><dd>{artifact.uncertainty.status.replaceAll('_', ' ')}</dd></div></dl></section><section><p className="eyebrow">THE LIMITS</p><h2>Four monitors.<br/>No invented detail.</h2><ul className="honest-list"><li>Forecasts describe the named monitoring station. Nearby streets or school grounds may differ.</li><li>Missing forecast hours remain missing. Windows must contain complete, consecutive hours.</li><li>Hourly PM2.5 is displayed in µg/m³. No unsupported AQI conversion or health category is applied.</li><li>Historical full-target RMSE includes extreme labels. It measures point error, not decision certainty.</li><li>Historical first-publication times and archive interval semantics remain unverified.</li></ul></section></div><section className="station-register"><div className="section-heading"><div><p className="eyebrow">THE FOUR ACTUAL STATIONS</p><h2>Coverage you can inspect.</h2></div></div><div className="station-register-grid">{artifact.stations.map(s => <article key={s.station_id}><span className="station-code">{s.station_id}</span><h3>{STATION_SHORT[s.station_id]}</h3><p>{s.latitude.toFixed(5)}° N<br/>{s.longitude.toFixed(5)}° E</p><small>Last PM observation</small><strong>{stampLabel(s.last_observation_ist)}</strong><p className="station-age">{numberLabel(s.freshness.observation_age_hours)} hours old at issue</p><span className="quiet-tag">{s.data_status.available_forecast_hours}/{s.data_status.expected_forecast_hours} forecast hours</span></article>)}</div></section><details className="method-details"><summary>Artifact identifiers & provenance</summary><dl className="fingerprint-list"><dt>Forecast artifact</dt><dd>{artifact.artifact_id}</dd><dt>Source commit</dt><dd>{artifact.model.git_commit || 'Unavailable'}</dd><dt>Training data SHA-256</dt><dd>{artifact.model.training_data_sha256 || 'Unavailable'}</dd>{replay && <><dt>Replay OOF SHA-256</dt><dd>{replay.provenance.oof_sha256}</dd><dt>Prediction lineage</dt><dd>{replay.provenance.prediction_lineage}</dd><dt>Historical availability assumption</dt><dd>{replay.provenance.availability_assumption}</dd></>}</dl></details><div className="sources-footer"><a href="https://github.com/acchasujal/aqi/tree/feature/task008-final-gap-execution" target="_blank" rel="noreferrer">Reproduce the code & methods ↗</a><a href="https://zindi.world/competitions/google-mumbai-data-challenge" target="_blank" rel="noreferrer">Official challenge ↗</a><a href="https://cpcb.nic.in/" target="_blank" rel="noreferrer">Official CPCB guidance ↗</a></div></section>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
