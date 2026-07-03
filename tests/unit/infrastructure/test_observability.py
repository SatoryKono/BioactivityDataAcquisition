"""Focused unit tests for retained observability facade seams."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.observability import metrics as metrics_module
from bioetl.infrastructure.observability.metrics import MetricsCollector


pytestmark = pytest.mark.unit


def test_metrics_module_reexports_collector() -> None:
    """The retained public metrics facade must expose ``MetricsCollector``."""
    assert metrics_module.MetricsCollector is MetricsCollector


def test_metrics_collector_initialization_retains_pipeline_context() -> None:
    """Facade collector should keep the configured pipeline context."""
    collector = MetricsCollector(pipeline_name="test_pipeline")

    assert collector.pipeline_name == "test_pipeline"
    assert collector.registry is None


def test_record_processed_increments_counter_with_public_labels() -> None:
    """Public collector facade must increment the processed counter."""
    collector = MetricsCollector(pipeline_name="observability-root-processed")
    labels = {
        "pipeline": collector.pipeline_name,
        "stage": "bronze",
        "run_type": "incremental",
    }
    counter = metrics_module.RECORDS_PROCESSED_TOTAL.labels(**labels)
    before = counter._value.get()

    collector.record_processed(layer="bronze", count=3)

    assert counter._value.get() == before + 3


def test_record_error_increments_error_counter_with_public_labels() -> None:
    """Public collector facade must increment the error counter."""
    collector = MetricsCollector(pipeline_name="observability-root-errors")
    labels = {
        "pipeline": collector.pipeline_name,
        "stage": "processing",
        "error_code": "VALIDATION_ERROR",
    }
    counter = metrics_module.ERRORS_TOTAL.labels(**labels)
    before = counter._value.get()

    collector.record_error(error_code="VALIDATION_ERROR")

    assert counter._value.get() == before + 1
