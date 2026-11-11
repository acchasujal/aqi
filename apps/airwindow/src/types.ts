export type ForecastHour = {
  target_start_ist: string;
  target_end_ist: string;
  pm25_prediction: number | null;
  unit: string;
  forecast_horizon_hours: number;
  status: 'available' | 'missing';
  prediction_interval: { lower: number; upper: number } | null;
};
export type Validation = {
  horizon_hours: number;
  status: 'measured' | 'not_available';
  primary_metric: 'full_target_rmse';
  rmse: number | null;
  n_targets: number | null;
  folds: number | null;
  fold_rmse_std: number | null;
};
export type Station = {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  last_observation_ist: string | null;
  freshness: { status: string; observation_age_hours: number | null; stale_after_hours: number | null; note: string };
  data_status: { status: string; expected_forecast_hours: number; available_forecast_hours: number; missing_target_starts_ist: string[]; note: string };
  validation: Validation[];
  forecasts: ForecastHour[];
};
export type ForecastArtifact = {
  schema_version: string;
  artifact_id: string;
  generated_at_ist: string;
  model_issue_time_ist: string;
  pm_history_cutoff_ist: string;
  model: { id: string; version: string; git_commit: string | null; training_data_sha256: string | null };
  weather: { used: boolean; provider: string | null; model: string | null; issue_time_ist: string | null };
  uncertainty: { status: string };
  stations: Station[];
};
export type TimeWindow = {
  start_ist: string;
  end_ist: string;
  mean_prediction: number;
  max_prediction: number;
  peak_start_ist: string;
  hours: ForecastHour[];
  rank: number;
};
export type DecisionState = 'ROBUST IMPROVEMENT' | 'TENTATIVE IMPROVEMENT' | 'NO CLEAR WINNER' | 'INSUFFICIENT EVIDENCE';
export type ReplayWindow = { start_ist: string; end_ist: string; mean_prediction: number; max_prediction: number; mean_observed: number | null; rank: number };
export type ReplayCase = {
  case_id: string; station_id: string; station_name: string; duration_hours: number; fold_id: string; split: string;
  issue_time_ist: string; pm_history_cutoff_ist: string; last_pm_end_ist: string;
  original_start_ist: string; original_end_ist: string; feasible_start_ist: string; feasible_end_ist: string;
  selected_start_ist: string; selected_end_ist: string; predicted_difference: number; observed_difference: number | null;
  hindsight_gap: number | null; decision_status: string; decision_reason?: string;
  hours: { target_start_ist: string; target_end_ist: string; prediction: number; observed: number | null }[];
  windows: ReplayWindow[]; original: ReplayWindow; selected: ReplayWindow;
};
export type EvidenceSummary = {
  station_id?: string; duration_hours?: number; split?: string; lead_min_hours?: number; lead_max_hours?: number;
  cases: number; origins: number; selected_alternative_cases: number; lower_observed_fraction: number | null;
  paired_outcome_cases?: number; missing_outcome_cases?: number; recommended_cases?: number;
  median_realised_difference: number | null; hindsight_gap_median: number | null; rmse?: number; validation_rows?: number;
};
export type ReplayArtifact = {
  schema_version: string; artifact_id: string; generated_at_ist: string;
  model: { id: string; version: string; git_commit: string | null };
  provenance: { oof_sha256: string; prediction_lineage: string; availability_assumption: string; independent_calibration: boolean };
  calibration: { status: string; reason: string; probability: null; interval: null };
  summary: EvidenceSummary;
  by_station_duration: EvidenceSummary[];
  reliability_profiles?: { station_id: string; duration_hours: number; lead_min_hours: number; lead_max_hours: number; pm_lead_min_hours: number; pm_lead_max_hours: number; cases: number; origins: number; median_absolute_difference_error: number | null; status: string }[];
  cases: ReplayCase[];
};
export type BaselineResult = {
  paired_cases: number; origins: number; airwindow_mean: number | null; baseline_mean: number | null;
  mean_delta: number | null; median_delta: number | null; cluster_bootstrap_95: [number | null, number | null];
  direction: string;
};
export type BaselinePanel = {
  cases: number; usual_cleanest_supported_cases: number;
  usual_cleanest: BaselineResult; latest_window: BaselineResult;
};
export type BaselineComparison = {
  schema_version: string; title: string; source_replay_sha256: string;
  method: Record<string, string>; full_replay: BaselinePanel; heldout: BaselinePanel; limitations: string[];
};
