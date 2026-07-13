"""Tests for workflow-specific Prometheus metrics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    GAUGES,
    HISTOGRAMS,
    PrometheusMetrics,
)


pytestmark = pytest.mark.unit


def test_workflow_metrics_are_registered() -> None:
    assert "bioetl_workflow_current_status" in GAUGES
    assert "bioetl_workflow_expected" in GAUGES
    assert "bioetl_workflow_pipeline_expected" in GAUGES
    assert "bioetl_workflow_runs_total" in COUNTERS
    assert "bioetl_workflow_step_events_total" in COUNTERS
    assert "bioetl_workflow_reconciliation_rows_scanned_total" in COUNTERS
    assert "bioetl_workflow_reconciliation_rows_retained_total" in COUNTERS
    assert "bioetl_workflow_reconciliation_rows_deleted_total" in COUNTERS
    assert "bioetl_workflow_step_duration_seconds" in HISTOGRAMS


def test_workflow_current_status_uses_bounded_label_surface() -> None:
    metrics = PrometheusMetrics()
    with patch.dict(GAUGES, {"bioetl_workflow_current_status": MagicMock()}):
        labels = {
            "workflow": "activity_workflow",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        }

        metrics.set_gauge("bioetl_workflow_current_status", 0.0, labels)

        GAUGES["bioetl_workflow_current_status"].labels.assert_called_once_with(
            **labels
        )
        GAUGES["bioetl_workflow_current_status"].labels().set.assert_called_once_with(
            0.0
        )


def test_workflow_step_metrics_use_bounded_label_surface() -> None:
    metrics = PrometheusMetrics()
    with (
        patch.dict(COUNTERS, {"bioetl_workflow_step_events_total": MagicMock()}),
        patch.dict(HISTOGRAMS, {"bioetl_workflow_step_duration_seconds": MagicMock()}),
    ):
        labels = {
            "workflow": "activity_workflow",
            "step_kind": "transform",
            "status": "success",
            "pipeline_context": "chembl_activity",
            "run_type_context": "incremental",
            "provider_context": "chembl",
        }

        metrics.increment_counter("bioetl_workflow_step_events_total", 1, labels)
        metrics.observe_histogram("bioetl_workflow_step_duration_seconds", 0.2, labels)

        COUNTERS["bioetl_workflow_step_events_total"].labels.assert_called_once_with(
            **labels
        )
        HISTOGRAMS[
            "bioetl_workflow_step_duration_seconds"
        ].labels.assert_called_once_with(**labels)


def test_workflow_expected_uses_bounded_label_surface() -> None:
    metrics = PrometheusMetrics()
    with patch.dict(GAUGES, {"bioetl_workflow_expected": MagicMock()}):
        labels = {
            "workflow": "chembl_target",
            "provider": "chembl",
        }

        metrics.set_gauge("bioetl_workflow_expected", 1.0, labels)

        GAUGES["bioetl_workflow_expected"].labels.assert_called_once_with(**labels)
        GAUGES["bioetl_workflow_expected"].labels().set.assert_called_once_with(1.0)


def test_workflow_pipeline_expected_uses_bounded_label_surface() -> None:
    metrics = PrometheusMetrics()
    with patch.dict(GAUGES, {"bioetl_workflow_pipeline_expected": MagicMock()}):
        labels = {
            "workflow": "chembl_baseline",
            "pipeline": "chembl_target",
            "run_type": "backfill",
            "provider": "chembl",
        }

        metrics.set_gauge("bioetl_workflow_pipeline_expected", 1.0, labels)

        GAUGES["bioetl_workflow_pipeline_expected"].labels.assert_called_once_with(
            **labels
        )
        GAUGES[
            "bioetl_workflow_pipeline_expected"
        ].labels().set.assert_called_once_with(1.0)


def test_workflow_reconciliation_metrics_support_no_label_dispatch() -> None:
    metrics = PrometheusMetrics()
    counter = MagicMock()
    counter._labelnames = ()

    with patch.dict(
        COUNTERS,
        {"bioetl_workflow_reconciliation_rows_scanned_total": counter},
    ):
        metrics.increment_counter(
            "bioetl_workflow_reconciliation_rows_scanned_total",
            3,
            {},
        )

    counter.inc.assert_called_once_with(3)
    counter.labels.assert_not_called()


def test_workflow_reconciliation_metrics_reject_unexpected_labels() -> None:
    metrics = PrometheusMetrics()
    counter = MagicMock()
    counter._labelnames = ()

    with patch.dict(
        COUNTERS,
        {"bioetl_workflow_reconciliation_rows_scanned_total": counter},
    ):
        with pytest.raises(ValueError, match="does not accept labels: workflow"):
            metrics.increment_counter(
                "bioetl_workflow_reconciliation_rows_scanned_total",
                3,
                {"workflow": "chembl_baseline"},
            )

    counter.inc.assert_not_called()
    counter.labels.assert_not_called()


def test_workflow_metrics_reject_run_id_label() -> None:
    metrics = PrometheusMetrics()
    with patch.dict(GAUGES, {"bioetl_workflow_expected": MagicMock()}):
        with pytest.raises(ValueError, match="run_id"):
            metrics.set_gauge(
                "bioetl_workflow_expected",
                1.0,
                {
                    "workflow": "chembl_target",
                    "provider": "chembl",
                    "run_id": "run-1",
                },
            )
