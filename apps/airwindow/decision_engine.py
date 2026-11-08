"""Deterministic activity windows and conservative decision evidence.

Ranking never reads actual observations. Replay outcomes are computed only after
the predicted window is selected. Calibration is a separate, explicit gate.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from typing import Any

STATES = ("ROBUST IMPROVEMENT", "TENTATIVE IMPROVEMENT", "NO CLEAR WINNER", "INSUFFICIENT EVIDENCE")


@dataclass(frozen=True)
class Hour:
    start: datetime
    end: datetime
    prediction: float | None
    observed: float | None = None

    def __post_init__(self) -> None:
        if self.start.utcoffset() != timedelta(hours=5, minutes=30) or self.end-self.start != timedelta(hours=1):
            raise ValueError("Every hour must be an explicit IST one-hour interval")
        if self.start.minute or self.start.second or self.start.microsecond:
            raise ValueError("Target intervals must start on an exact hour")
        for value in (self.prediction, self.observed):
            if value is not None and (not isfinite(value) or value < 0):
                raise ValueError("Concentrations must be finite and non-negative or missing")


@dataclass(frozen=True)
class Window:
    start: datetime
    end: datetime
    mean_prediction: float
    max_prediction: float
    peak_start: datetime
    hourly_predictions: tuple[float, ...]


def enumerate_windows(hours: Sequence[Hour], *, duration: int,
                      earliest_start: datetime, latest_end: datetime) -> list[Window]:
    """Return only complete contiguous forecast windows within hard boundaries."""
    if duration not in (1, 2, 3):
        raise ValueError("Activity duration must be one, two or three hours")
    if (earliest_start.utcoffset() != timedelta(hours=5, minutes=30)
            or latest_end.utcoffset() != timedelta(hours=5, minutes=30)
            or latest_end <= earliest_start):
        raise ValueError("Feasible range must be increasing explicit IST times")
    by_start = {hour.start: hour for hour in hours}
    if len(by_start) != len(hours):
        raise ValueError("Duplicate forecast hours")
    windows = []
    for start in sorted(by_start):
        end = start + timedelta(hours=duration)
        if start < earliest_start or end > latest_end:
            continue
        selected = [by_start.get(start+timedelta(hours=h)) for h in range(duration)]
        if any(hour is None or hour.prediction is None for hour in selected):
            continue
        values = tuple(float(hour.prediction) for hour in selected if hour is not None)
        peak = max(range(duration), key=lambda index: values[index])
        windows.append(Window(start, end, sum(values)/duration, max(values),
                              start+timedelta(hours=peak), values))
    return sorted(windows, key=lambda window: (window.mean_prediction, window.start))


def compare_schedule(hours: Sequence[Hour], *, original_start: datetime,
                     duration: int, earliest_start: datetime,
                     latest_end: datetime) -> tuple[Window, Window, list[Window]]:
    """Keep original visible even when it lies outside the alternative range."""
    original_windows = enumerate_windows(hours, duration=duration, earliest_start=original_start,
                                          latest_end=original_start+timedelta(hours=duration))
    if len(original_windows) != 1:
        raise ValueError("Original schedule has incomplete or missing forecast hours")
    original = original_windows[0]
    windows = enumerate_windows(hours, duration=duration, earliest_start=earliest_start, latest_end=latest_end)
    if not windows:
        raise ValueError("No complete activity window fits the feasible range")
    selected = windows[0] if windows[0].mean_prediction < original.mean_prediction else original
    return original, selected, windows


def observed_mean(window: Window, hours: Sequence[Hour]) -> float | None:
    """Retrospective outcome; this is never used to rank forecasts."""
    values = [hour.observed for hour in hours if window.start <= hour.start < window.end]
    expected = int((window.end-window.start).total_seconds()/3600)
    if len(values) != expected or any(value is None for value in values):
        return None
    return sum(float(value) for value in values if value is not None)/expected


def classify_decision(predicted_difference: float | None,
                      evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    """No probability or interval unless separately validated calibration exists.

    Two distinct origins are the mathematical minimum for resampling variation,
    not a sufficiency guarantee. The median absolute paired-difference error is
    a descriptive historical benchmark, not a calibrated significance threshold.
    """
    base = {"probability": None, "interval": None, "calibration_status": "not_calibrated"}
    if predicted_difference is None or not isfinite(predicted_difference):
        return {**base, "state": STATES[3], "reason": "A complete forecast comparison is unavailable."}
    if predicted_difference >= 0:
        return {**base, "state": STATES[2], "reason": "No alternative has a lower predicted mean than the original schedule."}
    if evidence is None or evidence.get("paired_outcome_origins", evidence.get("origins", 0)) < 2 or not evidence.get("comparable", True):
        return {**base, "state": STATES[3], "reason": "Too little comparable station, duration and lead evidence; no change is recommended."}
    typical_error = evidence.get("median_absolute_difference_error")
    if typical_error is None or not isfinite(typical_error):
        return {**base, "state": STATES[3], "reason": "Historical paired-difference errors are unavailable."}
    if -predicted_difference <= typical_error:
        return {**base, "state": STATES[2], "reason": "The predicted difference is no larger than the median historical error in comparable window differences."}
    calibration = evidence.get("calibration", {})
    # There is no approved calibration artifact in this release. This explicit
    # branch supports a future audited gate without converting descriptive rates
    # into probabilities or statistical guarantees.
    if (calibration.get("status") == "independently_validated"
            and calibration.get("approved_method_id")
            and calibration.get("comparison_passed") is True):
        return {**base, "state": STATES[0], "calibration_status": "independently_validated",
                "reason": "The comparison passes the separately validated decision rule."}
    return {**base, "state": STATES[1], "reason": "The predicted difference exceeds a typical historical comparison error, but independent calibration has not established a robust improvement."}
