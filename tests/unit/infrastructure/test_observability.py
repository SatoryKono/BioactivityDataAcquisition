# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Focused unit tests for retained observability facade seams."""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.infrastructure.observability import metrics as metrics_module
from bioetl.infrastructure.observability import metrics_collector as collector_module
from bioetl.infrastructure.observability.metrics import MetricsCollector


pytestmark = pytest.mark.unit


class _FakeCounter:
    def __init__(self) -> None:
        self.increments: list[int | None] = []

    def inc(self, amount: int | None = None) -> None:
        self.increments.append(amount)


class _FakeMetric:
    def __init__(self) -> None:
        self.label_calls: list[dict[str, Any]] = []
        self.counter = _FakeCounter()

    def labels(self, **labels: Any) -> _FakeCounter:
        self.label_calls.append(labels)
        return self.counter


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


def test_record_processed_uses_only_public_low_cardinality_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metric = _FakeMetric()
    monkeypatch.setattr(collector_module, "RECORDS_PROCESSED_TOTAL", metric)
    collector = MetricsCollector(pipeline_name="pipeline-a", registry=object())

    collector.record_processed(layer="silver", count=7, run_type="full")

    assert metric.label_calls == [
        {"pipeline": "pipeline-a", "stage": "silver", "run_type": "full"}
    ]
    assert metric.counter.increments == [7]
    assert collector.registry is not None


def test_record_error_uses_error_taxonomy_and_stage_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metric = _FakeMetric()
    monkeypatch.setattr(collector_module, "ERRORS_TOTAL", metric)
    collector = MetricsCollector(pipeline_name="pipeline-b")

    collector.record_error(error_code="SCHEMA_DRIFT", stage="gold")

    assert metric.label_calls == [
        {"pipeline": "pipeline-b", "stage": "gold", "error_code": "SCHEMA_DRIFT"}
    ]
    assert metric.counter.increments == [None]
