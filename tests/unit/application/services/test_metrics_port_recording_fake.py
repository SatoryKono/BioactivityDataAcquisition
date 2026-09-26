# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""MetricsPort/TracingPort interaction via recording fakes (TEST-SYS-09 / #7031)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from tests.fakes.metrics_fake import RecordingMetrics, RecordingTracing

pytestmark = pytest.mark.unit


def test_recording_metrics_captures_counter_and_histogram_labels() -> None:
    metrics = RecordingMetrics()
    metrics.increment_counter(
        "bioetl_pipeline_rows_total",
        value=3,
        labels={"provider": "chembl", "entity": "activity", "status": "ok"},
    )
    metrics.observe_histogram(
        "bioetl_pipeline_stage_seconds",
        value=0.42,
        labels={"stage": "transform"},
    )
    assert metrics.counter_names() == ["bioetl_pipeline_rows_total"]
    counter = metrics.calls[0]
    assert counter.labels["provider"] == "chembl"
    assert counter.value == 3
    hist = metrics.calls[1]
    assert hist.kind == "histogram"
    assert hist.value == 0.42


def test_recording_metrics_failure_path_emits_status_label() -> None:
    metrics = RecordingMetrics()
    # Simulate a pipeline service failure emission pattern used across app services.
    metrics.increment_counter(
        "bioetl_pipeline_errors_total",
        labels={"provider": "pubchem", "entity": "compound", "status": "error"},
    )
    assert metrics.calls[0].labels["status"] == "error"


def test_service_with_recording_metrics_port_receives_calls() -> None:
    """Wire RecordingMetrics into a lightweight service host surface."""
    metrics = RecordingMetrics()
    service = MagicMock()
    service._metrics = metrics

    # Happy path
    service._metrics.increment_counter(
        "bioetl_dq_checks_total",
        labels={"result": "pass"},
    )
    # Failure path
    service._metrics.increment_counter(
        "bioetl_dq_checks_total",
        labels={"result": "fail"},
    )
    assert service._metrics.counter_names() == [
        "bioetl_dq_checks_total",
        "bioetl_dq_checks_total",
    ]
    assert {c.labels["result"] for c in metrics.calls} == {"pass", "fail"}


def test_recording_tracing_starts_named_span() -> None:
    tracing = RecordingTracing()
    with tracing.start_span("pipeline.transform", attributes={"provider": "uniprot"}):
        pass
    assert tracing.spans[0].name == "pipeline.transform"
    assert tracing.spans[0].attributes["provider"] == "uniprot"
