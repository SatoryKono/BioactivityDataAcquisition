"""Replay reconstructability and drift metrics."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

__all__ = [
    "REPLAY_DRIFT_EVENTS_TOTAL",
    "REPLAY_DUPLICATE_OVERWRITE_RISK_TOTAL",
    "REPLAY_LAG_SECONDS",
    "REPLAY_RECONSTRUCTABILITY_EVENTS_TOTAL",
]

REPLAY_RECONSTRUCTABILITY_EVENTS_TOTAL = Counter(
    "bioetl_replay_reconstructability_events_total",
    "Total replay reconstructability observations recorded during manifest assembly",
    ["pipeline", "replay_capability", "strict_requirement", "status"],
)

REPLAY_DRIFT_EVENTS_TOTAL = Counter(
    "bioetl_replay_drift_events_total",
    "Total bounded replay drift observations recorded during manifest assembly",
    ["pipeline", "run_type", "replay_capability", "drift_type", "status"],
)

REPLAY_DUPLICATE_OVERWRITE_RISK_TOTAL = Counter(
    "bioetl_replay_duplicate_overwrite_risk_total",
    "Total accepted replay manifests exposing duplicate or overwrite write risk",
    ["pipeline", "run_type", "risk_type"],
)

REPLAY_LAG_SECONDS = Gauge(
    "bioetl_replay_lag_seconds",
    "Current bounded replay lag observed during manifest assembly",
    ["pipeline", "run_type", "replay_capability", "status"],
)
