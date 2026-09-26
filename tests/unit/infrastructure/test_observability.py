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
from bioetl.infrastructure.observability.metrics import MetricsCollector


pytestmark = pytest.mark.unit


class _FakeCounter:
    def __init__(self) -> None:
        self.increments: list[int | None] = []

    def inc(self, amount: int | None = None) -> None:
        self.increments.append(amount)


class _FakeMetricsPort:
    def __init__(self) -> None:
        self.counter_calls: list[tuple[str, float, dict[str, str]]] = []

    def increment_counter(
        self,
        name: str,
        value: float = 1,
        labels: dict[str, str] | None = None,
    ) -> None:
        self.counter_calls.append((name, float(value), dict(labels or {})))

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        del name, value, labels

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: dict[str, str] | None = None,
    ) -> None:
        del name, value, labels


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
    """Public collector facade must increment via MetricsPort."""
    metrics = _FakeMetricsPort()
    collector = MetricsCollector(
        pipeline_name="observability-root-processed",
        metrics=metrics,
    )

    collector.record_processed(layer="bronze", count=3)

    assert metrics.counter_calls == [
        (
            "bioetl_records_processed_total",
            3.0,
            {
                "pipeline": "observability-root-processed",
                "stage": "bronze",
                "run_type": "incremental",
            },
        )
    ]


def test_record_error_increments_error_counter_with_public_labels() -> None:
    """Public collector facade must increment errors via MetricsPort."""
    metrics = _FakeMetricsPort()
    collector = MetricsCollector(
        pipeline_name="observability-root-errors",
        metrics=metrics,
    )

    collector.record_error(error_code="VALIDATION_ERROR")

    assert metrics.counter_calls == [
        (
            "bioetl_errors_total",
            1.0,
            {
                "pipeline": "observability-root-errors",
                "stage": "processing",
                "error_code": "VALIDATION_ERROR",
            },
        )
    ]


def test_record_processed_uses_only_public_low_cardinality_labels() -> None:
    metrics = _FakeMetricsPort()
    collector = MetricsCollector(
        pipeline_name="pipeline-a",
        metrics=metrics,
        registry=object(),
    )

    collector.record_processed(layer="silver", count=7, run_type="full")

    assert metrics.counter_calls == [
        (
            "bioetl_records_processed_total",
            7.0,
            {"pipeline": "pipeline-a", "stage": "silver", "run_type": "full"},
        )
    ]
    assert collector.registry is not None


def test_record_error_uses_error_taxonomy_and_stage_labels() -> None:
    metrics = _FakeMetricsPort()
    collector = MetricsCollector(pipeline_name="pipeline-b", metrics=metrics)

    collector.record_error(error_code="SCHEMA_DRIFT", stage="gold")

    assert metrics.counter_calls == [
        (
            "bioetl_errors_total",
            1.0,
            {
                "pipeline": "pipeline-b",
                "stage": "gold",
                "error_code": "SCHEMA_DRIFT",
            },
        )
    ]
