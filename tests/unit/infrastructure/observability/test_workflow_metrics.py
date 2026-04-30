"""Tests for workflow-specific Prometheus metrics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.infrastructure.observability.prometheus_metrics import (
    COUNTERS,
    HISTOGRAMS,
    PrometheusMetrics,
)


def test_workflow_metrics_are_registered() -> None:
    assert "bioetl_workflow_runs_total" in COUNTERS
    assert "bioetl_workflow_step_events_total" in COUNTERS
    assert "bioetl_workflow_step_duration_seconds" in HISTOGRAMS


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
        }

        metrics.increment_counter("bioetl_workflow_step_events_total", 1, labels)
        metrics.observe_histogram("bioetl_workflow_step_duration_seconds", 0.2, labels)

        COUNTERS[
            "bioetl_workflow_step_events_total"
        ].labels.assert_called_once_with(**labels)
        HISTOGRAMS[
            "bioetl_workflow_step_duration_seconds"
        ].labels.assert_called_once_with(**labels)


def test_workflow_metrics_reject_run_id_label() -> None:
    metrics = PrometheusMetrics()
    with patch.dict(COUNTERS, {"bioetl_workflow_runs_total": MagicMock()}):
        with pytest.raises(ValueError, match="run_id"):
            metrics.increment_counter(
                "bioetl_workflow_runs_total",
                1,
                {
                    "workflow": "activity_workflow",
                    "status": "success",
                    "run_id": "run-1",
                },
            )
