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
"""Tests for BatchTracingManagerService."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.domain.ports.noop import NoOpTracing
from bioetl.domain.types import BatchID


pytestmark = pytest.mark.unit


@pytest.fixture
def mock_context() -> MagicMock:
    ctx = MagicMock()
    ctx.run_id = "test-run-001"
    ctx.run_type.value = "incremental"
    return ctx


@pytest.fixture
def mock_config() -> MagicMock:
    cfg = MagicMock()
    cfg.pipeline_name = "chembl_activity"
    cfg.entity_type = "activity"
    return cfg


@pytest.fixture
def mock_tracer() -> MagicMock:
    tracer = MagicMock()
    otel = MagicMock()
    span = MagicMock()
    otel.start_as_current_span.return_value = span
    tracer.get_tracer.return_value = otel
    return tracer


@pytest.fixture
def service(
    mock_tracer: MagicMock, mock_context: MagicMock, mock_config: MagicMock
) -> BatchTracingManagerService:
    return BatchTracingManagerService(
        tracer=mock_tracer,
        context=mock_context,
        config=mock_config,
        initial_batch_size=100,
        adaptive_sizing_enabled=False,
    )


def test_start_execution_span(service: BatchTracingManagerService) -> None:
    """Execution span is created with pipeline attributes."""
    span = service.start_execution_span()

    assert span is not None
    cast(MagicMock, span).__enter__.assert_called_once()


def test_start_batch_span(service: BatchTracingManagerService) -> None:
    """Batch span is created with batch_id and record_count."""
    span = service.start_batch_span(
        batch_id=BatchID(UUID("12345678-1234-5678-1234-567812345678")),
        record_count=50,
        start_index=0,
    )

    assert span is not None
    cast(MagicMock, span).__enter__.assert_called_once()


def test_start_layer_span(service: BatchTracingManagerService) -> None:
    """Layer span is created with correct count attribute key."""
    batch_id = BatchID(UUID("12345678-1234-5678-1234-567812345678"))
    span = service.start_layer_span("write_bronze", batch_id=batch_id, count=50)
    assert span is not None

    span2 = service.start_layer_span(
        "transform", batch_id=batch_id, count=50, input_count=True
    )
    assert span2 is not None


def test_end_span_success(service: BatchTracingManagerService) -> None:
    """End span without error just calls __exit__."""
    span = MagicMock()
    service.end_span(span)

    span.__exit__.assert_called_once_with(None, None, None)
    span.set_attribute.assert_not_called()


def test_end_span_with_error(service: BatchTracingManagerService) -> None:
    """End span with error records exception and sets error attribute."""
    span = MagicMock()
    error = ValueError("test error")
    service.end_span(span, error=error)

    span.set_attribute.assert_called_with("error", True)
    span.record_exception.assert_called_once_with(error)
    span.__exit__.assert_called_once()


def test_end_span_none_is_noop(service: BatchTracingManagerService) -> None:
    """End span with None span is a no-op."""
    service.end_span(None)  # Should not raise


def test_set_execution_stats(service: BatchTracingManagerService) -> None:
    """Set execution stats applies attributes to span."""
    span = MagicMock()
    service.set_execution_stats(
        span,
        total_fetched=1000,
        total_bronze=950,
        total_silver=900,
        total_gold=850,
        total_quarantined=50,
        batch_size_reductions=2,
        min_batch_size_used=50,
        memory_decision_trace=(
            {
                "decision_index": 1,
                "record_index": 100,
                "stage": "pressure_check",
                "old_batch_size": 100,
                "new_batch_size": 50,
                "adaptive_sizing_enabled": True,
                "monitor_available": True,
                "config_available": True,
                "pressure_state": True,
                "monitor_mode": "psutil",
                "reason": "monitor_pressure_detected",
            },
        ),
    )

    assert span.set_attribute.call_count == 11
    span.add_event.assert_called_once_with(
        "bioetl.memory.decision",
        attributes={
            "bioetl.memory.decision_index": 1,
            "bioetl.memory.record_index": 100,
            "bioetl.memory.stage": "pressure_check",
            "bioetl.memory.old_batch_size": 100,
            "bioetl.memory.new_batch_size": 50,
            "bioetl.memory.reason": "monitor_pressure_detected",
            "bioetl.memory.monitor_mode": "psutil",
            "bioetl.memory.adaptive_sizing_enabled": True,
            "bioetl.memory.monitor_available": True,
            "bioetl.memory.config_available": True,
            "bioetl.memory.pressure_state": True,
        },
    )


def test_set_execution_stats_none_span(service: BatchTracingManagerService) -> None:
    """Set execution stats with None span is a no-op."""
    result = service.set_execution_stats(
        None,
        total_fetched=0,
        total_bronze=0,
        total_silver=0,
        total_gold=0,
        total_quarantined=0,
        batch_size_reductions=0,
        min_batch_size_used=0,
        memory_decision_trace=(),
    )

    assert result is None


def test_real_tracer_accepts_non_empty_memory_decision_trace(
    mock_context: MagicMock,
    mock_config: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real tracing must not change successful terminal statistics."""
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    from bioetl.infrastructure.observability import tracing

    if not tracing.otel_available:
        pytest.skip("OpenTelemetry is not available")

    exporter = InMemorySpanExporter()
    monkeypatch.setattr(
        tracing,
        "_build_telemetry_exporter",
        lambda: exporter,
    )
    tracer = tracing.OpenTelemetryTracer("bioetl-batch-contract")
    manager = BatchTracingManagerService(
        tracer=tracer,
        context=mock_context,
        config=mock_config,
        initial_batch_size=100,
        adaptive_sizing_enabled=True,
    )
    span = manager.start_execution_span()
    try:
        manager.set_execution_stats(
            span,
            total_fetched=5,
            total_bronze=5,
            total_silver=5,
            total_gold=5,
            total_quarantined=0,
            batch_size_reductions=1,
            min_batch_size_used=50,
            memory_decision_trace=(
                {
                    "decision_index": 1,
                    "record_index": 5,
                    "stage": "pressure_check",
                    "old_batch_size": 100,
                    "new_batch_size": 50,
                    "adaptive_sizing_enabled": True,
                    "monitor_available": True,
                    "config_available": True,
                    "pressure_state": True,
                    "monitor_mode": "psutil",
                    "reason": "monitor_pressure_detected",
                },
            ),
        )
    finally:
        manager.end_span(span)
        tracer.close()

    finished_spans = exporter.get_finished_spans()
    assert len(finished_spans) == 1
    root_span = finished_spans[0]
    assert root_span.attributes["bioetl.total_bronze"] == 5
    assert root_span.attributes["bioetl.total_silver"] == 5
    assert root_span.attributes["bioetl.total_gold"] == 5
    assert [event.name for event in root_span.events] == ["bioetl.memory.decision"]


def test_noop_tracing(mock_context: MagicMock, mock_config: MagicMock) -> None:
    """Explicit NoOpTracing keeps the service safe without hidden defaults."""
    svc = BatchTracingManagerService(
        tracer=NoOpTracing(),
        context=mock_context,
        config=mock_config,
        initial_batch_size=100,
        adaptive_sizing_enabled=False,
    )

    assert isinstance(svc._tracer, NoOpTracing)


def test_batch_tracing_manager_requires_explicit_tracer(
    mock_context: MagicMock, mock_config: MagicMock
) -> None:
    """The application layer must not silently build tracing defaults."""
    with pytest.raises(TypeError, match="requires explicit tracer injection"):
        BatchTracingManagerService(
            tracer=None,
            context=mock_context,
            config=mock_config,
            initial_batch_size=100,
            adaptive_sizing_enabled=False,
        )


def test_end_span_with_shutdown(service: BatchTracingManagerService) -> None:
    """Shutdown span sets shutdown attribute."""
    span = MagicMock()
    service.end_span_with_shutdown(span)

    span.set_attribute.assert_called_with("bioetl.shutdown", True)
    span.__exit__.assert_called_once()
