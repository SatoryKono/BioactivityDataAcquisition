"""Ensure required control-plane series exist before a full Pushgateway snapshot.

Prometheus Counters and Gauges are omitted from exposition until a child is
created. A missing child is indistinguishable from a lost publication. A measured
zero (child present, value 0) means "no events". This helper creates the
required children without changing observed non-zero values.
"""

from __future__ import annotations

from collections.abc import Mapping

from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
)
from bioetl.domain.ports import MetricLabels, resolve_metric_labels
from bioetl.infrastructure.observability.prometheus_metric_label_dispatch import (
    normalize_metric_dispatch_labels,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import GAUGES
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics

_MANIFEST_WRITES = "bioetl_control_plane_manifest_writes_total"
_LEDGER_APPENDS = "bioetl_control_plane_ledger_appends_total"
_REPLAY_RISK = "bioetl_replay_duplicate_overwrite_risk_total"
_INTEGRITY_RATIO = "bioetl_manifest_ledger_integrity_ratio"
_CHECKPOINT_PRESENT = "bioetl_control_plane_checkpoint_present"

_STATUSES = ("success", "failed")
_RISK_TYPES = ("duplicate", "overwrite")
_INTEGRITY_TYPES = ("consistent", "inconsistent")
_LEDGER_SEED_EVENTS = (RUN_FINISHED_EVENT, RUN_FAILED_EVENT)

__all__ = ["ensure_required_control_plane_publication_series"]


def _label_key(metric: object, labels: Mapping[str, str]) -> tuple[str, ...]:
    labelnames = getattr(metric, "_labelnames", ())
    return tuple(str(labels[name]) for name in labelnames)


def _child_exists(metric: object, labels: Mapping[str, str]) -> bool:
    children = getattr(metric, "_metrics", None)
    if not isinstance(children, dict):
        return False
    return _label_key(metric, labels) in children


def _ensure_counter(name: str, labels: MetricLabels) -> None:
    resolved = normalize_metric_dispatch_labels(name, resolve_metric_labels(labels))
    PrometheusMetrics().increment_counter(name, 0, dict(resolved))


def _ensure_gauge_zero_if_absent(name: str, labels: MetricLabels) -> None:
    gauge = GAUGES[name]
    resolved = normalize_metric_dispatch_labels(name, resolve_metric_labels(labels))
    if _child_exists(gauge, resolved):
        return
    gauge.labels(**resolved)


def ensure_required_control_plane_publication_series(
    *,
    pipeline: str,
    run_type: str,
) -> None:
    """Create required checkpoint/manifest/ledger/risk/integrity children.

    Counters are incremented by zero so existing totals stay unchanged.
    Gauges are set to 0 only when the labelled child does not yet exist.
    """
    if not pipeline.strip() or pipeline.strip().lower() == "unknown":
        return
    pipeline = pipeline.strip()
    run_type_value = run_type.strip() or "unknown"

    for status in _STATUSES:
        _ensure_counter(
            _MANIFEST_WRITES,
            {
                "pipeline": pipeline,
                "run_type": run_type_value,
                "status": status,
            },
        )
    for event_type in _LEDGER_SEED_EVENTS:
        for status in _STATUSES:
            _ensure_counter(
                _LEDGER_APPENDS,
                {
                    "pipeline": pipeline,
                    "event_type": event_type,
                    "status": status,
                },
            )
    for risk_type in _RISK_TYPES:
        _ensure_counter(
            _REPLAY_RISK,
            {
                "pipeline": pipeline,
                "run_type": run_type_value,
                "risk_type": risk_type,
            },
        )
    for integrity_type in _INTEGRITY_TYPES:
        _ensure_gauge_zero_if_absent(
            _INTEGRITY_RATIO,
            {
                "pipeline": pipeline,
                "run_type": run_type_value,
                "integrity_type": integrity_type,
            },
        )
    _ensure_gauge_zero_if_absent(
        _CHECKPOINT_PRESENT,
        {"pipeline": pipeline, "run_type": run_type_value},
    )
