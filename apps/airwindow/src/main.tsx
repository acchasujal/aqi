import { StrictMode, useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { BaselineComparison, ForecastArtifact, ForecastHour, ReplayArtifact, ReplayCase, Station, TimeWindow, UnavailablePeriod } from './types.ts';
import { completeWindow, dateKey, dateLabel, enumerateWindows, isExpired, matchedValidation, differenceLabel, numberLabel, overlapsUnavailable, schoolSportsDayPlan, stampLabel, stationMapPositions, timeLabel, unavailablePeriodError, validateForecast, validateReplay, validateBaselineComparison, observationAge } from './domain.ts';
import { ReplayEvidence, ReplayWindowChart } from './replayEvidence.tsx';
import './styles.css';

type Page = 'plan' | 'replay' | 'evidence';
type Plan = { stationId: string; date: string; duration: number; original: string; earliest: string; latest: string };
type Comparison = { plan: Plan; original: TimeWindow; windows: TimeWindow[]; best: TimeWindow | null; difference: number | null; periods: UnavailablePeriod[]; completeCount: number; excludedCount: number; originalConflict: boolean };
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
  const [now, setNow] = useState(Date.now);
  useEffect(() => { const timer = setInterval(() => setNow(Date.now()), 60_000); return () => clearInterval(timer); }, []);
  const [artifact, setArtifact] = useState<ForecastArtifact | null>(null);
  const [replay, setReplay] = useState<ReplayArtifact | null>(null);
  const [baseline, setBaseline] = useState<BaselineComparison | null>(null);
  const [loadError, setLoadError] = useState('');
  const [replayError, setReplayError] = useState('');
  const [baselineError, setBaselineError] = useState('');
  const [page, setPage] = useState<Page>('plan');
  const [plan, setPlan] = useState<Plan | null>(null);
  const [comparison, setComparison] = useState<Comparison | null>(null);
  const [formError, setFormError] = useState('');
  const [brief, setBrief] = useState(false);
  const [demoMode, setDemoMode] = useState<'live' | 'historical' | null>(null);
  const [periods, setPeriods] = useState<UnavailablePeriod[]>([]);
  const nextPeriodId = useRef(0);
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
      setReplay(validateReplay(data));
    }).catch((error: Error) => { if (error.name !== 'AbortError') setReplayError(error.message); });
    return () => controller.abort();
  }, [page, comparison, replay, replayError]);

  useEffect(() => {
    if (page !== 'replay' || baseline || baselineError) return;
    const controller = new AbortController();
    fetch('./data/baseline_comparison.json', { signal: controller.signal }).then(r => {
      if (!r.ok) throw new Error(`Baseline comparison could not be loaded (${r.status}).`);
      return r.json();
    }).then(raw => setBaseline(validateBaselineComparison(raw)))
      .catch((error: Error) => { if (error.name !== 'AbortError') setBaselineError(error.message); });
    return () => controller.abort();
  }, [page, baseline, baselineError]);

  const station = artifact?.stations.find(s => s.station_id === plan?.stationId);
  const comparedStation = artifact?.stations.find(s => s.station_id === comparison?.plan.stationId);
  const dates = useMemo(() => station ? [...new Set(station.forecasts.filter(h => Date.parse(h.target_start_ist) > now).map(h => dateKey(h.target_start_ist)))] : [], [station, now]);
  const dayHours = station?.forecasts.filter(h => dateKey(h.target_start_ist) === plan?.date && Date.parse(h.target_start_ist) > Date.now()) || [];
  const periodDomainStart = dayHours[0]?.target_start_ist || '';
  const periodDomainEnd = dayHours.filter(h => dateKey(h.target_end_ist) === plan?.date).at(-1)?.target_end_ist || '';
  const expired = artifact ? isExpired(artifact, now) : false;
  const demoPlan = artifact ? schoolSportsDayPlan(artifact.stations, now) : null;

  function compare(event?: React.FormEvent) {
    event?.preventDefault();
    if (plan) runComparison(plan, false);
  }

  function runComparison(candidate: Plan, demo: boolean, selectedPeriods = periods) {
    const selectedStation = artifact?.stations.find(s => s.station_id === candidate.stationId);
    if (!selectedStation) return;
    try {
      if (artifact && isExpired(artifact, Date.now())) throw new Error('This forecast period has ended. Use Historical replay or load a newer artifact.');
      if (Date.parse(candidate.original) <= Date.now()) throw new Error('The original activity start has already passed. Choose a future slot or explore Historical replay.');
      const original = completeWindow(selectedStation.forecasts, candidate.original, candidate.duration);
      if (!original) throw new Error('The original activity needs complete forecast hours. Choose another start or a shorter duration.');
      if (Date.parse(candidate.earliest) <= Date.now()) throw new Error('The feasible range begins in the past. Choose a future start or explore Historical replay.');
      const day = selectedStation.forecasts.filter(h => dateKey(h.target_start_ist) === candidate.date && Date.parse(h.target_start_ist) > Date.now() && dateKey(h.target_end_ist) === candidate.date);
      for (const period of selectedPeriods) {
        const issue = unavailablePeriodError(period, candidate.date, day[0]?.target_start_ist || '', day.at(-1)?.target_end_ist || '');
        if (issue) throw new Error(issue);
      }
      const complete = enumerateWindows(selectedStation, candidate.earliest, candidate.latest, candidate.duration);
      if (!complete.length) throw new Error('No complete consecutive forecast windows fit this range. Missing hours are never filled.');
      const windows = selectedPeriods.length ? enumerateWindows(selectedStation, candidate.earliest, candidate.latest, candidate.duration, selectedPeriods) : complete;
      const best = selectedPeriods.length && windows.length === 1 && windows[0].start_ist === original.start_ist ? null : windows[0] || null;
      const originalRank = windows.find(w => w.start_ist === original.start_ist)?.rank || 0;
      setComparison({ plan: { ...candidate }, original: { ...original, rank: originalRank }, windows, best, difference: best ? best.mean_prediction - original.mean_prediction : null, periods: selectedPeriods.map(p => ({ ...p })), completeCount: complete.length, excludedCount: complete.length - windows.length, originalConflict: overlapsUnavailable(original.start_ist, original.end_ist, selectedPeriods) });
      setFormError('');
      setBrief(false);
      setDemoMode(demo ? 'live' : null);
      setTimeout(() => { resultsRef.current?.focus({ preventScroll: true }); resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 30);
    } catch (error) {
      setFormError(error instanceof Error ? error.message : 'Could not compare this activity.');
      setComparison(null);
      setDemoMode(null);
    }
  }

  function startDemo() {
    if (!artifact) return;
    const selected = schoolSportsDayPlan(artifact.stations, Date.now());
    if (selected && !isExpired(artifact, Date.now())) {
      const lunch: UnavailablePeriod = { id: `period-${nextPeriodId.current++}`, label: 'Lunch break (example)', start_ist: `${selected.date}T12:00:00+05:30`, end_ist: `${selected.date}T13:00:00+05:30` };
      const selectedStation = artifact.stations.find(s => s.station_id === selected.stationId)!;
      const example = Date.parse(lunch.start_ist) >= Date.parse(selected.earliest) && Date.parse(lunch.end_ist) <= Date.parse(selected.latest) && enumerateWindows(selectedStation, selected.earliest, selected.latest, 2, [lunch]).length > 0 ? [lunch] : [];
      setPlan(selected);
      setPeriods(example);
      runComparison(selected, true, example);
    } else {
      setDemoMode('historical');
      setPage('replay');
      setBrief(false);
    }
  }

  function updatePlan(change: Partial<Plan>) {
    if (plan) setPlan({ ...plan, ...change });
    setComparison(null); setBrief(false); setFormError(''); setDemoMode(null);
  }

  function updatePeriod(id: string, change: Partial<UnavailablePeriod>) {
    setPeriods(current => current.map(period => period.id === id ? { ...period, ...change } : period));
    setComparison(null); setBrief(false); setFormError('');
  }

  function addPeriod() {
    if (periods.length >= 6) { setFormError('Use up to six unavailable periods for one event.'); return; }
    const hour = dayHours.find(h => h.target_start_ist.slice(11, 16) === '12:00' && dateKey(h.target_end_ist) === plan?.date) || dayHours.find(h => dateKey(h.target_end_ist) === plan?.date);
    if (!hour) { setFormError('No valid unavailable period fits the remaining hours on this date.'); return; }
    setPeriods([...periods, { id: `period-${nextPeriodId.current++}`, label: 'Unavailable period', start_ist: hour.target_start_ist, end_ist: hour.target_end_ist }]);
    setComparison(null); setBrief(false); setFormError('');
  }

  function changeStation(id: string) {
    const s = artifact?.stations.find(item => item.station_id === id);
    if (s) { setPlan(defaultPlan(s)); setPeriods([]); setComparison(null); setFormError(''); setBrief(false); setDemoMode(null); }
  }
  function changeDate(date: string) {
    if (!station || !plan) return;
    const dateStation = { ...station, forecasts: station.forecasts.filter(h => dateKey(h.target_start_ist) === date) };
    setPlan({ ...defaultPlan(dateStation), duration: plan.duration });
    setPeriods([]); setComparison(null); setFormError(''); setBrief(false); setDemoMode(null);
  }

  return <>
    <a className="skip-link" href="#main">Skip to content</a>
    <header className="site-header no-print"><div className="header-inner">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setPage('plan'); setDemoMode(null); }} aria-label="AirWindow home"><span className="brand-mark"><i/><i/><i/></span><span>AirWindow<span className="brand-city">MUMBAI</span></span><span className="version-pill">2.1</span></a>
      <nav aria-label="Main navigation">{(['plan', 'replay', 'evidence'] as Page[]).map(p => <button key={p} className={page === p ? 'nav-active' : ''} aria-current={page === p ? 'page' : undefined} onClick={() => { setPage(p); setBrief(false); setDemoMode(null); }}>{p === 'plan' ? 'Plan an activity' : p === 'replay' ? 'Historical replay' : 'Evidence & sources'}</button>)}</nav>
      <span className="header-caption"><span className="status-dot"/> Independent challenge prototype</span>
    </div></header>

    <main id="main" className={brief ? 'main brief-open' : 'main'}>
      {loadError ? <section className="load-state"><Shield/><p className="eyebrow">Forecast unavailable</p><h1>A plan needs real data.</h1><p>{loadError}</p><p>No substitute forecast has been generated. Check the versioned forecast artifact and rebuild the application.</p><button className="primary-button" onClick={() => location.reload()}>Try again</button></section>
      : !artifact || !plan ? <section className="load-state" aria-live="polite"><div className="loading-ring"/><p>Loading the forecast and its evidence…</p></section>
      : page === 'plan' ? <>
        <section className="hero no-print"><div className="hero-copy"><p className="eyebrow"><span/> A LITTLE MORE ROOM TO PLAN</p><h1>Should you move<br/>your outdoor event?</h1><p className="hero-description">For school sports coordinators comparing an existing booking.<br/>See the forecast difference. Know when the evidence is too thin to change your plan.</p></div>
          <div className="hero-note"><span className="note-kicker">THE AIRWINDOW APPROACH</span><div className="small-orbit"><span/><span/><span/></div><p>A lower number<br/>is a starting point.<br/><strong>Evidence comes next.</strong></p><a href="#how-it-works" onClick={e => { e.preventDefault(); setPage('evidence'); }}>Why we sometimes abstain <span>↗</span></a></div>
        </section>

        <div className="snapshot-bar no-print"><span className="snapshot-label"><Clock/> Forecast snapshot</span><span>Issued {stampLabel(artifact.model_issue_time_ist)}</span><span>PM observations through {stampLabel(artifact.pm_history_cutoff_ist)}</span><span>Valid through {stampLabel(artifact.stations[0].forecasts.at(-1)!.target_end_ist)}</span><span className="snapshot-tag">{expired ? 'Forecast period ended' : 'Frozen · not live'}</span></div>

        <section className="demo-invite no-print" aria-label="Guided school sports day demo"><div><p className="eyebrow">SEE AIRWINDOW IN ACTION</p><p>See how AirWindow compares a school's existing sports-day schedule with other available time windows.</p></div><button className="primary-button" type="button" onClick={startDemo}>{demoPlan && !expired ? 'Try a school sports day' : 'Explore a historical school sports day'} <Arrow/></button></section>

        {expired && <div className="form-error no-print" role="status">This forecast horizon ended {stampLabel(artifact.stations[0].forecasts.at(-1)!.target_end_ist)}. New planning is disabled until a newer validated artifact is exported. <button className="text-button" onClick={() => setPage('replay')}>Explore historical replay</button></div>}

        {station && <section className="planner no-print" aria-labelledby="planner-heading"><div className="section-heading"><div><p className="eyebrow">01 / YOUR EVENT</p><h2 id="planner-heading">Start with the plan you already have.</h2></div><span className="quiet-tag">All times in IST · UTC+05:30</span></div>
          <form onSubmit={compare}>
            <div className="form-grid">
              <label className="station-field">Monitoring station<select value={plan.stationId} onChange={e => changeStation(e.target.value)}>{artifact.stations.map(s => <option key={s.station_id} value={s.station_id}>{STATION_SHORT[s.station_id] || s.station_name}</option>)}</select><small className="station-proxy">Measurement proxy only; it may not represent your school ground or event venue.</small></label>
              <label>Planning date<select value={plan.date} onChange={e => changeDate(e.target.value)}>{dates.map(d => <option key={d} value={d}>{dateLabel(`${d}T12:00:00+05:30`)}</option>)}</select></label>
              <label>Activity duration<select value={plan.duration} onChange={e => updatePlan({ duration: Number(e.target.value) })}>{[1, 2, 3].map(d => <option key={d} value={d}>{d} {d === 1 ? 'hour' : 'hours'}</option>)}</select></label>
              <label>Original start<select value={plan.original} onChange={e => updatePlan({ original: e.target.value })}>{dayHours.map(h => <option key={h.target_start_ist} value={h.target_start_ist}>{timeLabel(h.target_start_ist)}</option>)}</select></label>
              <label>Earliest feasible start<select value={plan.earliest} onChange={e => updatePlan({ earliest: e.target.value })}>{dayHours.map(h => <option key={h.target_start_ist} value={h.target_start_ist}>{timeLabel(h.target_start_ist)}</option>)}</select></label>
              <label>Latest feasible end<select value={plan.latest} onChange={e => updatePlan({ latest: e.target.value })}>{dayHours.map(h => <option key={h.target_end_ist} value={h.target_end_ist}>{timeLabel(h.target_end_ist)}{dateKey(h.target_end_ist) !== plan.date ? ' (+1 day)' : ''}</option>)}</select></label>
            </div>
            <StationMap stations={artifact.stations} selected={station} now={now} expired={expired} onSelect={changeStation}/>
            <fieldset className="unavailable-fieldset"><legend>When is the ground unavailable?</legend><p>Add lunch, exams or maintenance periods on this planning date. Times are IST; changing the date or station clears these periods.</p>
              {periods.map((period, index) => {
                const issue = unavailablePeriodError(period, plan.date, periodDomainStart, periodDomainEnd);
                return <div className="unavailable-block" key={period.id}><label>Reason<input aria-label={`Reason for unavailable period ${index + 1}`} type="text" maxLength={40} value={period.label} onChange={e => updatePeriod(period.id, { label: e.target.value })}/></label><label>Starts<input aria-label={`Start of unavailable period ${index + 1}`} type="time" step={900} min={periodDomainStart.slice(11, 16)} max={periodDomainEnd.slice(11, 16)} value={period.start_ist.slice(11, 16)} aria-invalid={!!issue} onChange={e => updatePeriod(period.id, { start_ist: `${plan.date}T${e.target.value}:00+05:30` })}/></label><label>Ends<input aria-label={`End of unavailable period ${index + 1}`} type="time" step={900} min={periodDomainStart.slice(11, 16)} max={periodDomainEnd.slice(11, 16)} value={period.end_ist.slice(11, 16)} aria-invalid={!!issue} onChange={e => updatePeriod(period.id, { end_ist: `${plan.date}T${e.target.value}:00+05:30` })}/></label><button className="text-button" type="button" onClick={() => { setPeriods(periods.filter(p => p.id !== period.id)); setComparison(null); setBrief(false); setFormError(''); }}>Remove</button>{issue && <p className="unavailable-error" role="alert">{issue}</p>}</div>;
              })}
              <button className="text-button add-unavailable" type="button" onClick={addPeriod} disabled={!periodDomainEnd || periods.length >= 6}>+ Add unavailable period</button>
            </fieldset>
            <div className="form-bottom"><div className="station-detail"><span className="location-pin">◎</span><p><strong>{station.station_name}</strong><span>Station {station.station_id} · {station.latitude.toFixed(5)}° N, {station.longitude.toFixed(5)}° E<br/>Last PM observation: {stampLabel(station.last_observation_ist)}<br/>{numberLabel(observationAge(station.last_observation_ist))} hours old now; {numberLabel(station.freshness.observation_age_hours)} hours old at issue. No validated freshness threshold.</span></p></div><button className="primary-button" type="submit">Compare time windows <Arrow/></button></div>
            {formError && <p className="form-error" role="alert">{formError}</p>}
          </form>
        </section>}

        {!comparison && <section className="how-strip no-print"><div className="how-number">01</div><div><h3>Keep the original in view.</h3><p>We compare complete, consecutive forecast hours with your existing schedule.</p></div><div className="how-number">02</div><div><h3>Let evidence have a say.</h3><p>A better-ranked forecast is never presented as a guarantee or a health recommendation.</p></div></section>}

        {comparison && comparedStation && <div ref={resultsRef} tabIndex={-1} className="comparison-area">
          {demoMode === 'live' && <p className="demo-context no-print"><strong>Example event · School sports day</strong><span>Illustrative scheduling scenario using the genuine forecast; not a real school's booking.</span></p>}
          <div className="section-heading no-print"><div><p className="eyebrow">02 / THE COMPARISON</p><h2>{comparison.best ? 'Your original. A possible alternative.' : 'Your original. No feasible alternative.'}</h2></div><button className="text-button" onClick={() => { setBrief(true); setTimeout(() => document.getElementById('event-brief')?.scrollIntoView({ behavior: 'smooth' }), 30); }}><Print/> Create event brief</button></div>
          <div className="decision-banner no-print"><span className="decision-icon"><Shield/></span><div><span className="decision-label">{!comparison.best ? 'NO FEASIBLE ALTERNATIVE' : comparison.difference! >= 0 ? 'NO CLEAR WINNER' : 'INSUFFICIENT EVIDENCE'}</span><h3>{!comparison.best ? 'No feasible alternative fits your scheduling constraints.' : comparison.difference! >= 0 ? 'Your current slot is already as well ranked.' : 'A lower forecast. An unproven scheduling improvement.'}</h3><p>{!comparison.best ? 'The original booking remains visible. Adjust or remove unavailable periods to search again.' : comparison.difference! >= 0 ? 'No feasible alternative has a lower predicted mean than your original schedule.' : `The best alternative is ${differenceLabel(-comparison.difference!)} µg/m³ lower in the forecast. Independent, comparable decision calibration is unavailable, so AirWindow abstains from recommending a move.`}</p></div><span className="uncalibrated-tag">No calibrated probability</span></div>
          <section className="constraint-results no-print" aria-label="Scheduling constraint results"><strong>{comparison.completeCount} complete forecast windows evaluated. {comparison.excludedCount} excluded by scheduling constraints. {comparison.windows.length} feasible {comparison.windows.length === 1 ? 'window remains' : 'windows remain'}.</strong><p>{comparison.periods.length ? comparison.periods.map(p => `${p.label}: ${timeLabel(p.start_ist)}–${timeLabel(p.end_ist)} IST`).join(' · ') : 'No unavailable periods were applied.'}</p>{comparison.originalConflict && <p className="constraint-conflict">Original schedule: Conflicts with unavailable period. It remains visible but is not ranked as feasible.</p>}</section>
          <div className="comparison-grid no-print"><WindowCard title="Original schedule" window={comparison.original} original conflict={comparison.originalConflict}/>{comparison.best ? <WindowCard title={comparison.best.start_ist === comparison.original.start_ist ? 'Best-ranked feasible window' : 'Best predicted alternative'} window={comparison.best} difference={comparison.difference!}/> : <div className="empty-panel"><h3>No feasible alternative fits your scheduling constraints.</h3><p>Adjust the unavailable periods or scheduling range to explore other windows.</p></div>}</div>
          <section className="trajectory-section no-print"><div className="section-heading"><div><p className="eyebrow">THE SHAPE OF THE DAY</p><h3>Hourly forecast, in context</h3></div><span className="chart-legend"><i/> Forecast PM2.5 <span>µg/m³</span></span></div><HourlyChart forecasts={comparedStation.forecasts.filter(h => dateKey(h.target_start_ist) === comparison.plan.date)} original={comparison.original} best={comparison.best || undefined}/><p className="chart-caption">Shading marks the original and {comparison.best ? 'best-ranked' : 'any feasible'} windows. These are forecast concentrations at the monitor, not personal exposure.</p></section>
          {comparison.best && <ReliabilityPanel artifact={artifact} station={comparedStation} comparison={comparison} replay={replay}/>}
          <section className="alternatives no-print"><div className="section-heading"><div><p className="eyebrow">KEEP YOUR OPTIONS OPEN</p><h3>All feasible windows</h3></div><span className="quiet-tag">{comparison.windows.length} complete {comparison.plan.duration}-hour windows</span></div>{comparison.windows.length ? <div className="table-scroll"><table><thead><tr><th>Rank</th><th>Activity window · IST</th><th>Forecast mean</th><th>Highest hour</th><th>Vs original</th></tr></thead><tbody>{comparison.windows.map(w => <tr key={w.start_ist} className={w.start_ist === comparison.original.start_ist ? 'original-row' : ''}><td><span className={w.rank === 1 ? 'rank rank-first' : 'rank'}>{w.rank.toString().padStart(2, '0')}</span></td><td>{timeLabel(w.start_ist)} – {timeLabel(w.end_ist)}{w.start_ist === comparison.original.start_ist && <span className="row-tag">Original</span>}</td><td>{numberLabel(w.mean_prediction)} <small>µg/m³</small></td><td>{numberLabel(w.max_prediction)} <small>µg/m³</small></td><td className={w.mean_prediction < comparison.original.mean_prediction ? 'lower-value' : ''}>{w.mean_prediction === comparison.original.mean_prediction ? '—' : `${w.mean_prediction < comparison.original.mean_prediction ? '−' : '+'}${differenceLabel(Math.abs(w.mean_prediction - comparison.original.mean_prediction))}`} <small>{w.mean_prediction === comparison.original.mean_prediction ? '' : 'µg/m³'}</small></td></tr>)}</tbody></table></div> : <p className="panel-note">No feasible alternative fits your scheduling constraints.</p>}{!comparison.original.rank && <p className="panel-note">Your original schedule is outside the feasible set and remains visible above.</p>}</section>
          {brief && <EventBrief artifact={artifact} station={comparedStation} comparison={comparison} onClose={() => setBrief(false)}/>}
        </div>}
        <section className="boundary-note no-print"><span>FOUR STATIONS. CLEAR LIMITS.</span><p>A monitoring station may not represent nearby streets, a school ground, or your exact location. This is an independent planning prototype. For health recommendations, consult <a href="https://cpcb.nic.in/" target="_blank" rel="noreferrer">official CPCB guidance ↗</a>.</p></section>
      </> : page === 'replay' ? <ReplayView replay={replay} baseline={baseline} baselineError={baselineError} error={replayError} demo={demoMode === 'historical'} onRetry={() => setReplayError('')}/> : <EvidenceView artifact={artifact} replay={replay}/>}
    </main>
    <footer className="site-footer no-print"><div><span className="footer-brand">AirWindow Mumbai</span><p>Better-timed plans. Clearly stated limits.</p></div><div><a href="https://github.com/acchasujal/aqi/tree/main" target="_blank" rel="noreferrer">Source & methodology ↗</a><span>Built for the Google Mumbai Data Challenge · 2026</span></div></footer>
  </>;
}

function StationMap({ stations, selected, now, expired, onSelect }: { stations: Station[]; selected: Station; now: number; expired: boolean; onSelect: (id: string) => void }) {
  const positions = stationMapPositions(stations);
  return <section className="station-map">
    <div className="station-map-heading"><div><p className="eyebrow">FOUR ACTUAL MONITORS</p><h3 id="station-map-heading">Explore Mumbai's monitoring stations</h3></div><span className="quiet-tag">Geographic station locator</span></div>
    <div className="station-map-layout">
      <div className="station-map-plot" role="group" aria-label="Mumbai station locator">
        <svg viewBox="0 0 400 400" aria-hidden="true" focusable="false"><rect x="1" y="1" width="398" height="398" rx="3" className="map-frame"/><path d="M100 1v398M200 1v398M300 1v398M1 100h398M1 200h398M1 300h398" className="map-grid"/><path d="M345 56V25m0 0-7 10m7-10 7 10" className="map-north"/><text x="345" y="18" textAnchor="middle" className="map-north-label">N</text></svg>
        {stations.map((station, index) => <button key={station.station_id} type="button" className={`station-marker ${station.station_id === selected.station_id ? 'station-marker-selected' : ''}`} style={{ left: `${positions[station.station_id].x / 4}%`, top: `${positions[station.station_id].y / 4}%` }} data-station-id={station.station_id} data-latitude={station.latitude} data-longitude={station.longitude} data-map-x={positions[station.station_id].x} data-map-y={positions[station.station_id].y} aria-label={`${station.station_name}, station ${station.station_id}`} aria-pressed={station.station_id === selected.station_id} onClick={() => onSelect(station.station_id)}>{index + 1}</button>)}
      </div>
      <div className="station-map-info" aria-live="polite"><span className="station-map-kicker">SELECTED MONITORING STATION</span><h4>{selected.station_name}</h4><p>Station {selected.station_id} · {selected.latitude.toFixed(5)}° N, {selected.longitude.toFixed(5)}° E</p><dl><div><dt>Latest PM2.5 observation</dt><dd>{stampLabel(selected.last_observation_ist)}</dd></div><div><dt>Observation age</dt><dd>{numberLabel(observationAge(selected.last_observation_ist, now))} hours as of now</dd></div><div><dt>Forecast hours available</dt><dd>{selected.data_status.available_forecast_hours} of {selected.data_status.expected_forecast_hours}</dd></div><div><dt>Snapshot status</dt><dd>{expired ? 'Forecast period ended · explore historical replay' : 'Frozen forecast snapshot · not live'}</dd></div></dl><div className="station-map-legend"><strong>Map key</strong><p>Numbered markers show monitoring locations only; north is up. The selected marker is highlighted.</p><ol>{stations.map((station, index) => <li key={station.station_id}><span>{index + 1}</span>{station.station_name}</li>)}</ol></div></div>
    </div>
    <p className="station-map-disclaimer">Markers represent four monitoring stations. Forecasts describe station-level conditions, not pollution at individual schools or streets.</p>
  </section>;
}

function WindowCard({ title, window, original = false, conflict = false, difference }: { title: string; window: TimeWindow; original?: boolean; conflict?: boolean; difference?: number }) {
  return <article className={`window-card ${original ? 'window-original' : 'window-alternative'}`}><div className="window-card-top"><span>{title}</span><span className="window-badge">{original ? 'YOUR PLAN' : `RANK ${window.rank.toString().padStart(2, '0')}`}</span></div>{conflict && <p className="constraint-conflict">Conflicts with unavailable period</p>}<h3>{timeLabel(window.start_ist)}<span> — </span>{timeLabel(window.end_ist)}</h3><p className="window-date">{dateLabel(window.start_ist)} · IST</p><div className="window-value"><strong>{numberLabel(window.mean_prediction)}</strong><span>µg/m³<br/>predicted mean</span></div>{difference !== undefined && <p className="delta-line">{difference < 0 ? `↓ ${differenceLabel(-difference)} µg/m³ lower than original` : difference > 0 ? `↑ ${differenceLabel(difference)} µg/m³ above original` : 'Same predicted mean as original'}</p>}<div className="window-divider"/><div className="window-details"><span>Highest forecast hour<strong>{numberLabel(window.max_prediction)} µg/m³</strong></span><span>Peak interval starts<strong>{timeLabel(window.peak_start_ist)} IST</strong></span></div><div className="hour-chips">{window.hours.map(h => <span key={h.target_start_ist}>{timeLabel(h.target_start_ist)} <strong>{numberLabel(h.pm25_prediction)}</strong><small>µg/m³</small></span>)}</div></article>;
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
  if (!comparison.best) return null;
  const profiles = replay?.reliability_profiles?.filter(p => p.station_id === station.station_id && p.duration_hours === comparison.plan.duration) || [];
  const lead = (Date.parse(comparison.best.start_ist) - Date.parse(artifact.model_issue_time_ist)) / 3_600_000;
  const pmLead = (Date.parse(comparison.best.start_ist) - Date.parse(station.last_observation_ist || artifact.pm_history_cutoff_ist)) / 3_600_000;
  const matching = profiles.find(p => lead >= p.lead_min_hours && lead <= p.lead_max_hours && pmLead >= p.pm_lead_min_hours && pmLead <= p.pm_lead_max_hours);
  const validation = matchedValidation(station, comparison.best, artifact.model_issue_time_ist);
  return <section className="reliability-panel no-print" aria-labelledby="reliability-heading"><div><p className="eyebrow">03 / BEFORE YOU CHANGE ANYTHING</p><h2 id="reliability-heading">Can you trust this comparison?</h2><p>Historical forecast accuracy and a reliable scheduling decision are different questions. We keep both visible.</p><div className="evidence-status"><Shield/><span>Decision calibration <strong>Not independently validated</strong></span></div></div><div className="evidence-grid"><div><span>Comparable decision cases</span><strong>{matching ? matching.cases.toLocaleString('en-IN') : 'Not established'}</strong><small>{matching ? `${matching.origins} origins · descriptive evidence only` : 'Station, duration and both information clocks must match'}</small></div><div><span>Station validation RMSE</span><strong>{numberLabel(validation?.rmse)} <small>µg/m³</small></strong><small>{validation.matched ? `${validation.rows.toLocaleString('en-IN')} labels · ${validation.note} · full target` : validation.note}</small></div><div><span>Forecast lead for alternative</span><strong>{numberLabel(lead)} <small>hours from issue</small></strong><small>{numberLabel(pmLead)} hours from last PM observation</small></div><div><span>Uncertainty intervals</span><strong>Not shown</strong><small>No independently validated decision probability or forecast interval</small></div></div><p className="reliability-footnote">{matching ? `Comparable historical paired-difference errors are descriptive; they do not establish that this live alternative will be better. ${replay?.calibration.reason || ''}` : 'The available historical decision cases do not establish comparable, independently calibrated evidence for this live issue time and PM age. A numerically lower forecast alone does not justify a confident recommendation.'}</p></section>;
}

function EventBrief({ artifact, station, comparison, onClose }: { artifact: ForecastArtifact; station: Station; comparison: Comparison; onClose: () => void }) {
  const metric = comparison.best ? matchedValidation(station, comparison.best, artifact.model_issue_time_ist) : null;
  return <section id="event-brief" className="event-brief">
    <div className="brief-toolbar no-print"><span>Your event brief</span><div><button className="text-button" onClick={onClose}>Close brief</button><button className="primary-button" onClick={() => window.print()}><Print/> Print / save PDF</button></div></div>
    <div className="brief-paper">
      <div className="brief-masthead"><span className="footer-brand">AirWindow Mumbai</span><span>EVENT PLANNING BRIEF</span></div>
      <h2>A plan, with its evidence attached.</h2>
      <p className="brief-station">{STATION_SHORT[station.station_id]} · {dateLabel(comparison.original.start_ist)} · {comparison.plan.duration}-hour activity</p>
      <div className="brief-status"><strong>{!comparison.best ? 'NO FEASIBLE ALTERNATIVE' : comparison.difference! >= 0 ? 'NO CLEAR WINNER' : 'INSUFFICIENT EVIDENCE'}</strong><p>{!comparison.best ? 'No feasible alternative fits the declared scheduling constraints. The original booking remains visible.' : comparison.difference! >= 0 ? 'The original is already as well ranked as the alternatives.' : 'The alternative has a lower predicted concentration. AirWindow abstains from recommending a move because decision reliability has not been independently validated.'}</p></div>
      <div className="brief-comparison"><div><span>Original schedule</span><h3>{timeLabel(comparison.original.start_ist)} – {timeLabel(comparison.original.end_ist)} IST</h3><p><strong>{numberLabel(comparison.original.mean_prediction)}</strong> µg/m³ forecast mean</p><small>Peak at {timeLabel(comparison.original.peak_start_ist)} IST: {numberLabel(comparison.original.max_prediction)} µg/m³</small></div>{comparison.best ? <div><span>Best feasible alternative</span><h3>{timeLabel(comparison.best.start_ist)} – {timeLabel(comparison.best.end_ist)} IST</h3><p><strong>{numberLabel(comparison.best.mean_prediction)}</strong> µg/m³ forecast mean</p><small>Peak at {timeLabel(comparison.best.peak_start_ist)} IST: {numberLabel(comparison.best.max_prediction)} µg/m³</small></div> : <div><span>Feasible alternative</span><h3>None available</h3><p>Adjust unavailable periods and compare again.</p></div>}</div>
      {comparison.best && <p className="brief-difference">Predicted difference: <strong>{comparison.difference! < 0 ? '−' : comparison.difference! > 0 ? '+' : ''}{differenceLabel(Math.abs(comparison.difference!))} µg/m³</strong> · selected minus original</p>}
      <div className="brief-constraints"><strong>Ground availability</strong><p>{comparison.completeCount} complete forecast windows · {comparison.excludedCount} excluded · {comparison.windows.length} feasible.</p><p>{comparison.periods.length ? comparison.periods.map(period => `${period.label}: ${timeLabel(period.start_ist)}–${timeLabel(period.end_ist)} IST`).join(' · ') : 'No unavailable periods declared.'}</p><p>Original booking: {comparison.originalConflict ? 'Conflicts with unavailable period; retained for comparison.' : 'No conflict with unavailable periods.'}</p></div>
      <dl className="brief-meta"><div><dt>Forecast issued</dt><dd>{stampLabel(artifact.model_issue_time_ist)}</dd></div><div><dt>PM history cutoff</dt><dd>{stampLabel(artifact.pm_history_cutoff_ist)}</dd></div><div><dt>Latest PM observation</dt><dd>{stampLabel(station.last_observation_ist)}</dd></div><div><dt>Model</dt><dd>{artifact.model.id} · {artifact.model.version}</dd></div><div><dt>Station</dt><dd>{station.station_id} · {station.latitude.toFixed(5)}, {station.longitude.toFixed(5)}</dd></div><div><dt>Validation</dt><dd>{metric ? metric.matched ? `${numberLabel(metric.rmse)} µg/m³ full-target RMSE; ${metric.note}; not decision calibration` : `Matched station validation unavailable. ${metric.note}` : 'No feasible alternative to validate.'}</dd></div><div><dt>Artifact</dt><dd>{artifact.artifact_id}</dd></div></dl>
      <p className="brief-disclaimer">Monitoring-station forecasts may not represent nearby streets or the event location. No period is labelled safe or medically recommended. This comparison is not a personal exposure estimate. Refer to official CPCB/government guidance for health recommendations.</p>
      <div className="brief-end">Independent Google Mumbai Data Challenge prototype · All times IST · Hourly PM2.5, µg/m³</div>
    </div>
  </section>;
}

function ReplayView({ replay, baseline, baselineError, error, demo, onRetry }: { replay: ReplayArtifact | null; baseline: BaselineComparison | null; baselineError: string; error: string; demo: boolean; onRetry: () => void }) {
  const [stationId, setStationId] = useState('11606');
  const [duration, setDuration] = useState(2);
  const [caseId, setCaseId] = useState('');
  const [outcomeFilter, setOutcomeFilter] = useState<'all' | 'lower' | 'higher_equal' | 'missing'>('all');
  const [revealedCaseId, setRevealedCaseId] = useState<string | null>(null);
  const caseRef = useRef<HTMLElement>(null);
  const cases = replay?.cases.filter(c => c.station_id === stationId && c.duration_hours === duration && (outcomeFilter === 'all' || (outcomeFilter === 'missing' ? c.observed_difference === null : outcomeFilter === 'lower' ? c.observed_difference !== null && c.observed_difference < 0 : c.observed_difference !== null && c.observed_difference >= 0))) || [];
  const item = cases.find(c => c.case_id === caseId) || (demo ? cases.filter(c => c.observed_difference !== null).at(-1) : undefined) || cases.at(-1);
  const revealed = !!item && revealedCaseId === item.case_id;
  useEffect(() => {
    if (!demo || !item) return;
    const timer = setTimeout(() => { caseRef.current?.focus({ preventScroll: true }); caseRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 30);
    return () => clearTimeout(timer);
  }, [demo, replay]);
  return <section className="replay-page"><p className="eyebrow">HISTORICAL DECISION REPLAY</p><h1>Would the move<br/>have worked?</h1><p className="page-intro">Revisit historical forecast simulations and later observations. Generated retrospectively with history frozen at the recorded origin. Reveal each case to inspect what happened afterwards.</p><span className="retrospective-tag">Retrospective evaluation · released historical observations</span>
    {demo && <p className="demo-context"><strong>Example event · School sports day</strong><span>Genuine historical forecast simulation. Subsequent observations are hidden until you reveal them.</span></p>}
    {!replay ? <div className="empty-panel"><h2>{error ? 'Replay is unavailable.' : 'Loading historical replay'}</h2><p>{error || 'Loading genuine OOF forecasts…'}</p><p>No historical outcomes have been invented.</p>{error && <button className="primary-button" onClick={onRetry}>Retry replay</button>}</div> : <>
      <p className="replay-warning"><Shield/> Forecast-ranked schedules are not calibrated recommendations. {revealed && <>No schedule changes were endorsed as calibrated recommendations. These are historical outcomes, not a calibrated probability for your next event. {replay.calibration.reason}</>}</p>
      {revealed && <ReplayEvidence replay={replay}/>}
      {revealed && <BaselineComparisonPanel comparison={baseline} error={baselineError}/>}
      <div className="replay-outcome-filter"><label htmlFor="historical-outcome-filter">Historical outcome filter · uses later observations</label><select id="historical-outcome-filter" value={outcomeFilter} onChange={e => { setOutcomeFilter(e.target.value as typeof outcomeFilter); setCaseId(''); setRevealedCaseId(null); }}><option value="all">All cases</option><option value="lower">Lower observed PM2.5</option><option value="higher_equal">Higher or equal observed PM2.5</option><option value="missing">Insufficient observations</option></select><p>Filters are for hindsight exploration. Each case stays forecast-only until revealed.</p></div>
      <div className="replay-controls"><label>Station<select aria-label="Station" value={stationId} onChange={e => { setStationId(e.target.value); setCaseId(''); setRevealedCaseId(null); }}>{Object.entries(STATION_SHORT).map(([id, label]) => <option key={id} value={id}>{label}</option>)}</select></label><label>Duration<select aria-label="Duration" value={duration} onChange={e => { setDuration(Number(e.target.value)); setCaseId(''); setRevealedCaseId(null); }}>{[1, 2, 3].map(d => <option key={d} value={d}>{d} {d === 1 ? 'hour' : 'hours'}</option>)}</select></label><label>Historical forecast case<select aria-label="Historical forecast case" value={item?.case_id || ''} onChange={e => { setCaseId(e.target.value); setRevealedCaseId(null); }}>{cases.map(c => <option key={c.case_id} value={c.case_id}>{dateLabel(c.original_start_ist)} · {timeLabel(c.original_start_ist)} · {c.split}</option>)}</select></label></div>
      {item ? <ReplayCaseView key={item.case_id} item={item} revealed={revealed} focusRef={caseRef} onToggle={() => setRevealedCaseId(revealed ? null : item.case_id)}/> : <div className="empty-panel"><h2>No eligible case for this selection.</h2><p>Missing historical forecasts are not filled.</p></div>}
      {revealed && <details className="method-details"><summary>See the replay design and all station/duration results</summary><p>Predeclared school-event scenarios use the original 09:00 slot and feasible 08:00–18:00 range on each available target day. One-, two- and three-hour activities are evaluated. The selected window is chosen using forecasts only; observed outcomes are joined afterwards. Historical publication timing is proxied by interval end. Cases and outcomes are retained even when the selected alternative is worse.</p><div className="table-scroll"><table><thead><tr><th>Station</th><th>Duration</th><th>Split</th><th>Cases</th><th>Origins</th><th>Lower observed</th><th>Median difference</th></tr></thead><tbody>{replay.by_station_duration.map((r, i) => <tr key={i}><td>{STATION_SHORT[r.station_id || ''] || r.station_id}</td><td>{r.duration_hours}h</td><td>{r.split}</td><td>{r.cases}</td><td>{r.origins}</td><td>{r.lower_observed_fraction === null ? 'Unavailable' : `${numberLabel(r.lower_observed_fraction * 100)}%`}</td><td>{numberLabel(r.median_realised_difference)} µg/m³</td></tr>)}</tbody></table></div></details>}</>}
  </section>;
}

function BaselineComparisonPanel({ comparison, error }: { comparison: BaselineComparison | null; error: string }) {
  if (error) return <section className="baseline-panel" role="status"><h2>Baseline comparison unavailable</h2><p>{error} Historical replay remains available.</p></section>;
  if (!comparison) return <section className="baseline-panel" aria-live="polite"><h2>Comparing schedule baselines</h2><p>Loading the reproducible paired-origin comparison&#8230;</p></section>;
  const fmt = (value: number | null) => numberLabel(value, 2);
  const unit = '\u00b5g/m\u00b3';
  const pFmt = (value: number | null) => value === null ? 'Unavailable' : value.toFixed(3);
  const signed = (value: number | null) => value === null ? 'Unavailable' : `${value < 0 ? '−' : value > 0 ? '+' : ''}${fmt(Math.abs(value))}`;
  const includesZero = (interval: [number | null, number | null]) => interval[0] !== null && interval[1] !== null && interval[0] <= 0 && interval[1] >= 0;
  const cell = (name: string, result: BaselineComparison['full_replay']['usual_cleanest']) => <article key={name}><h3>{name}</h3>{result.paired_cases === 0 ? <p>No paired observed cases available.</p> : <><p><strong>{signed(result.mean_delta)} {unit}</strong><br/>mean paired difference: AirWindow minus baseline</p><p><strong>{signed(result.median_delta)} {unit}</strong><br/>median paired difference</p><p>{fmt(result.cluster_bootstrap_95[0])} to {fmt(result.cluster_bootstrap_95[1])} {unit} · 95% origin-cluster bootstrap</p><small>{result.paired_cases.toLocaleString('en-IN')} paired cases across {result.origins} origins · AirWindow {fmt(result.airwindow_mean)} vs baseline {fmt(result.baseline_mean)} {unit}</small><b className="baseline-verdict">{includesZero(result.cluster_bootstrap_95) ? 'Cluster-bootstrap interval includes zero; no established difference' : result.direction === 'interval_below_zero' ? 'Cluster-bootstrap interval is below zero in this retrospective sample' : 'Cluster-bootstrap interval is above zero in this retrospective sample'}</b><p className="origin-sensitivity"><strong>Origin-level direction:</strong> {result.origin_level.favor_airwindow} favour AirWindow, {result.origin_level.favor_baseline} favour the baseline, {result.origin_level.ties} tie (per-origin mean paired difference; tie tolerance ±{fmt(result.origin_level.tie_tolerance)} {unit}).</p><p className="origin-sensitivity"><strong>Equal-origin mean:</strong> {signed(result.origin_level.equal_origin_mean_delta)} {unit}; 95% Student-t sensitivity interval {fmt(result.origin_level.student_t_95[0])} to {fmt(result.origin_level.student_t_95[1])} {unit} {includesZero(result.origin_level.student_t_95) ? '(includes zero)' : '(excludes zero)'}. Exact two-sided sign-test p={pFmt(result.origin_level.exact_sign_test_two_sided_p)}; exploratory sensitivity only.</p></>}</article>;
  return <section className="baseline-panel" aria-labelledby="baseline-heading"><div className="baseline-heading"><p className="eyebrow">MODEL VS SIMPLE SCHEDULES</p><h2 id="baseline-heading">How did the forecast-ranked choice compare?</h2><p>Paired later-observed mean PM2.5 for the same station, duration and case. Negative differences favour AirWindow.</p></div><div className="baseline-tabs"><section><h3>Full replay · {comparison.full_replay.cases.toLocaleString('en-IN')} declared cases</h3><p className="baseline-method">Usual-cleanest uses earlier origins only; latest-window is the latest-starting complete candidate.</p><div className="baseline-cards">{cell('Usual cleanest window', comparison.full_replay.usual_cleanest)}{cell('Latest feasible window', comparison.full_replay.latest_window)}</div><small>Usual-cleanest baseline supported in {comparison.full_replay.usual_cleanest_supported_cases.toLocaleString('en-IN')} cases; paired outcome coverage is shown per result.</small></section><section><h3>Held-out confirmation · {comparison.heldout.cases} declared cases</h3><p className="baseline-method">The usual-cleanest time is chosen from development outcomes only; confirmation outcomes do not select it. This sample contains eight origins and was previously inspected by analysts.</p><div className="baseline-cards">{cell('Usual cleanest window', comparison.heldout.usual_cleanest)}{cell('Latest feasible window', comparison.heldout.latest_window)}</div></section></div><p className="baseline-caveat">All values are retrospective and are not a live recommendation probability or guarantee. Cases within origins overlap. Cluster-bootstrap and equal-origin Student-t intervals are sensitivities; neither establishes superiority. The small-sample sign test is exploratory. Missing observed outcomes stay outside paired estimates and remain counted in replay coverage.</p></section>;
}

function ReplayCaseView({ item, revealed, focusRef, onToggle }: { item: ReplayCase; revealed: boolean; focusRef: React.Ref<HTMLElement>; onToggle: () => void }) {
  return <section ref={focusRef} tabIndex={-1} className="replay-case"><div className="section-heading"><div><p className="eyebrow">HISTORICAL FORECAST SIMULATION</p><h2>{STATION_SHORT[item.station_id]} · {dateLabel(item.original_start_ist)}</h2></div><span className="quiet-tag">{item.split} origin</span></div><div className="replay-clock"><span>Simulated issue/origin <strong>{stampLabel(item.issue_time_ist)}</strong></span><span>PM cutoff <strong>{stampLabel(item.pm_history_cutoff_ist)}</strong></span></div><div className="replay-outcome"><div><span>Original forecast{revealed ? ' / actual' : ''}</span><h3>{timeLabel(item.original_start_ist)} – {timeLabel(item.original_end_ist)} IST</h3><p><strong>{numberLabel(item.original.mean_prediction)}</strong><span>forecast</span>{revealed && <><strong className="observed-color">{numberLabel(item.original.mean_observed)}</strong><span>observed µg/m³</span></>}</p></div><Arrow/><div><span>Selected forecast{revealed ? ' / actual' : ''}</span><h3>{timeLabel(item.selected_start_ist)} – {timeLabel(item.selected_end_ist)} IST</h3><p><strong>{numberLabel(item.selected.mean_prediction)}</strong><span>forecast</span>{revealed && <><strong className="observed-color">{numberLabel(item.selected.mean_observed)}</strong><span>observed µg/m³</span></>}</p></div></div><p className="replay-predicted-delta">Predicted difference: <strong>{item.predicted_difference < 0 ? "−" : item.predicted_difference > 0 ? "+" : ""}{numberLabel(Math.abs(item.predicted_difference))} µg/m³</strong> · suggested minus original</p><button className="primary-button reveal-button" aria-expanded={revealed} onClick={onToggle}>{revealed ? 'Hide subsequent observations' : 'Reveal subsequent observations'}</button>{revealed && <div className="outcome-verdict" role="status"><span>{item.observed_difference === null ? 'INSUFFICIENT OBSERVATIONS' : item.observed_difference < 0 ? 'LOWER OBSERVED PM2.5' : item.observed_difference > 0 ? 'HIGHER OBSERVED PM2.5' : 'NO OBSERVED DIFFERENCE'}</span>{item.observed_difference === null ? <p>Complete subsequent observations are unavailable for this paired comparison. This case remains in the record; missing values are never zero-filled.</p> : <p>The selected slot was <strong>{numberLabel(Math.abs(item.observed_difference))} µg/m³ {item.observed_difference < 0 ? 'lower' : item.observed_difference > 0 ? 'higher' : 'different'}</strong> in subsequently observed mean PM2.5. This is a retrospective outcome, not a measured health benefit.</p>}</div>}<ReplayWindowChart item={item} revealed={revealed}/><p className="panel-note">Origin {item.fold_id}{revealed && <> · Retrospective decision classification: {item.decision_status.replaceAll('_', ' ')} · Hindsight gap: {numberLabel(item.hindsight_gap)} µg/m³</>}</p><details className="method-details"><summary>All {item.windows.length} complete feasible forecast windows</summary><p>Ranked using forecasts only. Original: {timeLabel(item.original_start_ist)}–{timeLabel(item.original_end_ist)} IST. Selected (original retained on ties): {timeLabel(item.selected_start_ist)}–{timeLabel(item.selected_end_ist)} IST.</p><div className="table-scroll"><table><thead><tr><th>Forecast rank</th><th>Window · IST</th><th>Predicted mean</th><th>Maximum</th>{revealed && <th>Later observed mean</th>}</tr></thead><tbody>{item.windows.map(w => <tr key={w.start_ist}><td>{w.rank}{w.start_ist === item.selected_start_ist ? ' · Selected' : ''}</td><td>{timeLabel(w.start_ist)}–{timeLabel(w.end_ist)}{w.start_ist === item.original_start_ist ? ' · Original' : ''}</td><td>{numberLabel(w.mean_prediction)} µg/m³</td><td>{numberLabel(w.max_prediction)} µg/m³</td>{revealed && <td>{numberLabel(w.mean_observed)} µg/m³</td>}</tr>)}</tbody></table></div></details></section>;
}

function EvidenceView({ artifact, replay }: { artifact: ForecastArtifact; replay: ReplayArtifact | null }) {
  return <section className="evidence-page"><p className="eyebrow">EVIDENCE, WITHOUT THE FINE PRINT</p><h1>Know what the<br/>forecast can support.</h1><p className="page-intro">AirWindow helps a school coordinator compare possible schedules. The measurements, model forecast and historical evaluation each have a different role.</p><div className="evidence-thesis"><Shield/><div><h2>Abstention is part of the product.</h2><p>A lower predicted concentration is not enough to prove that moving an event will help. We require paired historical decisions at comparable stations, durations and information ages, evaluated on independent chronological origins, before showing a calibrated recommendation.</p><strong>Current decision calibration: {replay?.calibration.status.replaceAll('_', ' ') || 'not available'}</strong></div></div><div className="trust-columns"><section><p className="eyebrow">THE FORECAST</p><h2>A versioned artifact.<br/>A traceable model.</h2><dl><div><dt>Model</dt><dd>{artifact.model.id}</dd></div><div><dt>Version</dt><dd>{artifact.model.version}</dd></div><div><dt>Issued</dt><dd>{stampLabel(artifact.model_issue_time_ist)}</dd></div><div><dt>PM history cutoff</dt><dd>{stampLabel(artifact.pm_history_cutoff_ist)}</dd></div><div><dt>Snapshot status</dt><dd>Frozen; not continuously updated</dd></div><div><dt>Forecast horizon</dt><dd>{stampLabel(artifact.stations[0].forecasts[0].target_start_ist)} to {stampLabel(artifact.stations[0].forecasts.at(-1)!.target_end_ist)}; complete windows only</dd></div><div><dt>Generated</dt><dd>{stampLabel(artifact.generated_at_ist)}</dd></div><div><dt>Weather inputs</dt><dd>{artifact.weather.used ? `${artifact.weather.provider} · ${artifact.weather.model}` : 'Not used'}</dd></div><div><dt>Forecast intervals</dt><dd>{artifact.uncertainty.status.replaceAll('_', ' ')}</dd></div></dl></section><section><p className="eyebrow">THE LIMITS</p><h2>Four monitors.<br/>No invented detail.</h2><ul className="honest-list"><li>Forecasts describe the named monitoring station. The selected monitor is a measurement proxy and may not represent the actual school ground or event venue.</li><li>Missing forecast hours remain missing. Windows must contain complete, consecutive hours.</li><li>Hourly PM2.5 is displayed in µg/m³. No unsupported AQI conversion or health category is applied.</li><li>Historical full-target RMSE includes extreme labels. It measures point error, not decision certainty.</li><li>Historical first-publication times and archive interval semantics remain unverified.</li></ul></section></div><section className="station-register"><div className="section-heading"><div><p className="eyebrow">THE FOUR ACTUAL STATIONS</p><h2>Coverage you can inspect.</h2></div></div><div className="station-register-grid">{artifact.stations.map(s => <article key={s.station_id}><span className="station-code">{s.station_id}</span><h3>{STATION_SHORT[s.station_id]}</h3><p>{s.latitude.toFixed(5)}° N<br/>{s.longitude.toFixed(5)}° E</p><small>Last PM observation</small><strong>{stampLabel(s.last_observation_ist)}</strong><p className="station-age">{numberLabel(observationAge(s.last_observation_ist))} hours old now; {numberLabel(s.freshness.observation_age_hours)} hours old at issue</p><span className="quiet-tag">{s.data_status.available_forecast_hours}/{s.data_status.expected_forecast_hours} forecast hours</span></article>)}</div></section><details className="method-details"><summary>Historical validation rows, origins and lead-specific RMSE</summary><p>Historical benchmark only: issue time equals PM cutoff, with the exact lead listed below. These clocks do not match the current frozen forecast. Full-target RMSE uses unmodified labels, including extremes; it does not calibrate a scheduling decision. Origins can recur across leads; do not sum them as independent origins.</p><div className="table-scroll"><table><thead><tr><th>Station</th><th>Issue / PM lead (hours)</th><th>Full-target RMSE (µg/m³)</th><th>Labelled rows</th><th>Origins</th><th>Fold RMSE SD</th></tr></thead><tbody>{artifact.stations.flatMap(s => s.validation.map(v => <tr key={`${s.station_id}-${v.horizon_hours}`}><td>{STATION_SHORT[s.station_id]}</td><td>{v.horizon_hours}</td><td>{numberLabel(v.rmse)}</td><td>{v.n_targets ?? 'Unavailable'}</td><td>{v.folds ?? 'Unavailable'}</td><td>{numberLabel(v.fold_rmse_std)}</td></tr>))}</tbody></table></div></details><details className="method-details"><summary>Artifact identifiers & provenance</summary><dl className="fingerprint-list"><dt>Forecast artifact</dt><dd>{artifact.artifact_id}</dd><dt>Source commit</dt><dd>{artifact.model.git_commit || 'Unavailable'}</dd><dt>Training data SHA-256</dt><dd>{artifact.model.training_data_sha256 || 'Unavailable'}</dd>{replay && <><dt>Replay OOF SHA-256</dt><dd>{replay.provenance.oof_sha256}</dd><dt>Prediction lineage</dt><dd>{replay.provenance.prediction_lineage}</dd><dt>Historical availability assumption</dt><dd>{replay.provenance.availability_assumption}</dd></>}</dl></details><section className="google-tools"><p className="eyebrow">GOOGLE TOOLS & REPRODUCIBILITY</p><h2>Static delivery. Reproducible evidence.</h2><p><strong>Firebase Hosting</strong> serves the verified static application at <a href="https://airwindow-99085.web.app/" target="_blank" rel="noreferrer">airwindow-99085.web.app</a>. The application uses versioned local artifacts and requires no runtime API.</p><p><strong>Google Colab</strong> can run the <a href="https://colab.research.google.com/github/acchasujal/aqi/blob/main/apps/airwindow/notebooks/Decision_Replay.ipynb" target="_blank" rel="noreferrer">decision replay notebook</a>. It was executed locally; a Google-hosted Colab session has not been verified.</p></section><div className="sources-footer"><a href="https://github.com/acchasujal/aqi/tree/main" target="_blank" rel="noreferrer">Reproduce the code & methods ↗</a><a href="https://zindi.world/competitions/google-mumbai-data-challenge" target="_blank" rel="noreferrer">Official challenge ↗</a><a href="https://cpcb.nic.in/" target="_blank" rel="noreferrer">Official CPCB guidance ↗</a></div></section>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App/></StrictMode>);
