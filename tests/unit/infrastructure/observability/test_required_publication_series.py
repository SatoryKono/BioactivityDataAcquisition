"""Required control-plane series must be present as measured zeros."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from bioetl.infrastructure.observability.prometheus_metric_label_dispatch import (
    normalize_metric_dispatch_labels,
)
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    COUNTERS,
    GAUGES,
)
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.required_publication_series import (
    ensure_required_control_plane_publication_series,
)

pytestmark = pytest.mark.unit

_PIPELINE = "seed_pub_chembl_assay"
_RUN_TYPE = "backfill"


def _sample_value(name: str, labels: Mapping[str, str]) -> float:
    family = COUNTERS.get(name) or GAUGES[name]
    resolved = normalize_metric_dispatch_labels(name, dict(labels))
    for metric in family.collect():
        for sample in metric.samples:
            if sample.name != name:
                continue
            if sample.labels == resolved:
                return float(sample.value)
    raise AssertionError(f"missing sample {name} {resolved!r}")


def test_ensure_required_series_exports_measured_zeros() -> None:
    ensure_required_control_plane_publication_series(
        pipeline=_PIPELINE,
        run_type=_RUN_TYPE,
    )

    assert (
        _sample_value(
            "bioetl_control_plane_ledger_appends_total",
            {
                "pipeline": _PIPELINE,
                "event_type": "run_finished",
                "status": "success",
            },
        )
        == 0.0
    )
    assert (
        _sample_value(
            "bioetl_replay_duplicate_overwrite_risk_total",
            {
                "pipeline": _PIPELINE,
                "run_type": _RUN_TYPE,
                "risk_type": "duplicate",
            },
        )
        == 0.0
    )
    assert (
        _sample_value(
            "bioetl_replay_duplicate_overwrite_risk_total",
            {
                "pipeline": _PIPELINE,
                "run_type": _RUN_TYPE,
                "risk_type": "overwrite",
            },
        )
        == 0.0
    )
    assert (
        _sample_value(
            "bioetl_manifest_ledger_integrity_ratio",
            {
                "pipeline": _PIPELINE,
                "run_type": _RUN_TYPE,
                "integrity_type": "consistent",
            },
        )
        == 0.0
    )
    assert (
        _sample_value(
            "bioetl_control_plane_checkpoint_present",
            {"pipeline": _PIPELINE, "run_type": _RUN_TYPE},
        )
        == 0.0
    )


def test_ensure_required_series_skips_unknown_and_blank_pipeline() -> None:
    ensure_required_control_plane_publication_series(
        pipeline="unknown",
        run_type=_RUN_TYPE,
    )
    ensure_required_control_plane_publication_series(
        pipeline="   ",
        run_type=_RUN_TYPE,
    )
    with pytest.raises(AssertionError, match="missing sample"):
        _sample_value(
            "bioetl_control_plane_ledger_appends_total",
            {
                "pipeline": "unknown",
                "event_type": "run_finished",
                "status": "success",
            },
        )


def test_ensure_required_series_does_not_clobber_integrity_ratio() -> None:
    labels = {
        "pipeline": _PIPELINE,
        "run_type": _RUN_TYPE,
        "integrity_type": "inconsistent",
    }
    PrometheusMetrics().set_gauge(
        "bioetl_manifest_ledger_integrity_ratio",
        0.25,
        labels,
    )
    ensure_required_control_plane_publication_series(
        pipeline=_PIPELINE,
        run_type=_RUN_TYPE,
    )
    assert _sample_value("bioetl_manifest_ledger_integrity_ratio", labels) == 0.25
