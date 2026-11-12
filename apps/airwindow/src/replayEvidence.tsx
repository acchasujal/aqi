import type { ReplayArtifact, ReplayCase, ReplayWindow } from './types.ts';
import { numberLabel, replayOutcomeCounts, timeLabel } from './domain.ts';

export function ReplayEvidence({ replay }: { replay: ReplayArtifact }) {
  const counts = replayOutcomeCounts(replay.cases);
  const paired = counts.lower + counts.higher + counts.equal;
  const equalRetained = replay.cases.filter(item => item.observed_difference === 0 && item.selected_start_ist === item.original_start_ist).length;
  const categories = [
    ['Lower observed PM2.5', counts.lower, 'lower'],
    ['Higher observed PM2.5', counts.higher, 'higher'],
    ['Equal observed PM2.5', counts.equal, 'equal'],
    ['Insufficient observations', counts.missing, 'missing'],
  ] as const;
  return <section className="replay-evidence" aria-labelledby="replay-evidence-heading">
    <p className="eyebrow">LATER OBSERVATIONS · DESCRIPTIVE ONLY</p>
    <h2 id="replay-evidence-heading">How did AirWindow perform in historical replay?</h2>
    <div className="replay-evidence-stats">
      <div><strong>{replay.cases.length.toLocaleString('en-IN')}</strong><span>total cases</span></div>
      <div><strong>{paired.toLocaleString('en-IN')}</strong><span>paired outcomes</span></div>
      <div><strong>{counts.missing.toLocaleString('en-IN')}</strong><span>insufficient observations</span></div>
      <div><strong>{counts.lower.toLocaleString('en-IN')}</strong><span>lower observed</span></div>
      <div><strong>{(counts.higher + counts.equal).toLocaleString('en-IN')}</strong><span>higher or equal observed</span></div>
    </div>
    <p className="replay-evidence-rate"><strong>{counts.changedWithOutcomes ? `${numberLabel(counts.lowerChanged / counts.changedWithOutcomes * 100)}%` : 'Unavailable'}</strong> of {counts.changedWithOutcomes.toLocaleString('en-IN')} evaluable cases where a different window was selected had lower observed PM2.5. This is a historical fraction, not a probability of future success.</p>
    <p className="replay-evidence-medians">Median realised difference: {numberLabel(replay.summary.median_realised_difference)} µg/m³ (selected minus original). Median hindsight gap: {numberLabel(replay.summary.hindsight_gap_median)} µg/m³ (selected minus best later-observed feasible slot).</p>
    <div className="replay-distribution" role="img" aria-label={`Historical outcome distribution among ${replay.cases.length} cases: ${counts.lower} lower, ${counts.higher} higher, ${counts.equal} equal, ${counts.missing} with insufficient observations.`}>{categories.map(([label, count, kind]) => <div key={kind} className={`replay-distribution-${kind}`}><span>{label}</span><div className="replay-distribution-track"><i style={{ width: `${count / replay.cases.length * 100}%` }}/></div><strong>{count.toLocaleString('en-IN')}</strong></div>)}</div>
    <p className="replay-evidence-note">All {replay.cases.length.toLocaleString('en-IN')} cases are included in the distribution; {paired.toLocaleString('en-IN')} have paired observations. Equal outcomes include {equalRetained} cases where the original time was retained. Historical replay is not a randomized intervention. Missing observations limit evaluation. Numerical improvement does not establish a health benefit. Baseline confidence intervals have not established statistically significant superiority. Rescheduling cannot guarantee lower air pollution.</p>
  </section>;
}

export function ReplayWindowChart({ item, revealed }: { item: ReplayCase; revealed: boolean }) {
  const windows: [string, ReplayWindow][] = [['Original event', item.original], [item.selected_start_ist === item.original_start_ist ? 'Original retained' : 'Suggested event', item.selected]];
  const values = windows.flatMap(([, window]) => revealed && window.mean_observed !== null ? [window.mean_prediction, window.mean_observed] : [window.mean_prediction]);
  const scale = Math.max(1, ...values);
  return <figure className="replay-window-chart">
    <figcaption>{revealed ? 'Forecast versus later observation' : 'Forecast comparison · subsequent observations hidden'}</figcaption>
    <p>Window means · µg/m³ · shared scale 0–{numberLabel(scale)}</p>
    {windows.map(([label, window]) => <div className="replay-window-chart-group" key={label}>
      <h3>{label} <small>{timeLabel(window.start_ist)}–{timeLabel(window.end_ist)} IST</small></h3>
      <div className="replay-window-chart-row"><span>Forecast</span><div className="replay-window-chart-track"><i className="replay-window-chart-forecast" style={{ width: `${window.mean_prediction / scale * 100}%` }}/></div><strong>{numberLabel(window.mean_prediction)} µg/m³</strong></div>
      {revealed && <div className="replay-window-chart-row"><span>Observed</span><div className="replay-window-chart-track">{window.mean_observed !== null && <i className="replay-window-chart-observed" style={{ width: `${window.mean_observed / scale * 100}%` }}/>}</div><strong>{window.mean_observed === null ? 'Unavailable' : `${numberLabel(window.mean_observed)} µg/m³`}</strong></div>}
    </div>)}
    <p className="replay-window-chart-note">Bars share one concentration scale. {revealed ? 'Missing later observations remain unavailable.' : 'Later observations are hidden until you reveal them.'}</p>
  </figure>;
}
