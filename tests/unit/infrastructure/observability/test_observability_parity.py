"""Parity contract tests for no-op and production observability adapters."""

from __future__ import annotations


import pytest
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

from bioetl.domain.ports import (
    LoggerPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.observability import tracing as tracing_module
from bioetl.infrastructure.observability.logging import create_logger
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics


def _build_metrics_adapter(kind: str) -> MetricsPort:
    if kind == "noop":
        return NoOpMetrics()
    if kind == "prometheus":
        return PrometheusMetrics()
    raise ValueError(f"Unknown metrics adapter kind: {kind}")


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["noop", "prometheus"])
def test_metrics_adapters_accept_canonical_labels(kind: str) -> None:
    """No-op and production metrics adapters should accept canonical labels."""
    metrics = _build_metrics_adapter(kind)
    assert isinstance(metrics, MetricsPort)

    histogram_variants = ({"labels": {"provider": "chembl", "endpoint": "/molecule"}},)
    counter_variants = (
        {
            "labels": {
                "provider": "chembl",
                "endpoint": "/molecule",
                "status": "success",
            }
        },
    )
    gauge_variants = ({"labels": {"provider": "chembl"}},)

    for kwargs in histogram_variants:
        metrics.observe_histogram(
            "bioetl_adapter_request_duration_seconds", 1.0, **kwargs
        )
    for kwargs in counter_variants:
        metrics.increment_counter("bioetl_adapter_requests_total", 1, **kwargs)
    for kwargs in gauge_variants:
        metrics.set_gauge("bioetl_provider_health_status", 1.0, **kwargs)


@pytest.mark.unit
@pytest.mark.parametrize("kind", ["noop", "prometheus"])
def test_metrics_adapters_reject_legacy_label_aliases(kind: str) -> None:
    """No-op and production metrics adapters should fail on removed label aliases."""
    metrics = _build_metrics_adapter(kind)

    with pytest.raises(TypeError):
        metrics.observe_histogram(
            "bioetl_adapter_request_duration_seconds",
            1.0,
            _labels={"provider": "chembl", "endpoint": "/molecule"},
        )
    with pytest.raises(TypeError):
        metrics.increment_counter(
            "bioetl_adapter_requests_total",
            1,
            tags={"provider": "chembl", "endpoint": "/molecule", "status": "success"},
        )


@pytest.mark.unit
def test_logger_adapters_share_same_contract_surface() -> None:
    """No-op and production logger adapters should support the same calls."""
    production_logger = create_logger(
        "test_pipeline", deterministic_uuid_from_callsite("test_observability_parity")
    )
    adapters: list[LoggerPort] = [NoOpLogger(), production_logger]

    for logger in adapters:
        assert isinstance(logger, LoggerPort)
        bound = logger.bind(run_id="run-1", pipeline="test_pipeline")
        bound.info("event_info", event="conflict_payload_event", stage="extract")
        bound.warning("event_warning", event="conflict_payload_event", stage="extract")
        bound.error("event_error", event="conflict_payload_event", stage="extract")
        bound.debug("event_debug", event="conflict_payload_event", stage="extract")
        bound.exception(
            "event_exception",
            event="conflict_payload_event",
            stage="extract",
        )


@pytest.mark.unit
def test_tracing_adapters_expose_otel_compatible_surface() -> None:
    """No-op and production tracing adapters should expose compatible API.

    Forces ConsoleSpanExporter (not OTLP) to avoid a 5-second gRPC
    flush timeout during close(). The API surface is identical regardless
    of exporter backend.
    """
    from unittest.mock import patch

    adapters: list[TracingPort] = [NoOpTracing()]
    if tracing_module.OTEL_AVAILABLE:
        # Disable OTLP so OpenTelemetryTracer uses ConsoleSpanExporter,
        # avoiding the gRPC connection attempt and 5s flush timeout.
        with patch.object(tracing_module, "OTLP_AVAILABLE", False):
            adapters.append(tracing_module.OpenTelemetryTracer("bioetl-test"))

    try:
        for tracing_adapter in adapters:
            assert isinstance(tracing_adapter, TracingPort)
            tracer = tracing_adapter.get_tracer("test.component")
            with tracer.start_as_current_span("test-span") as span:
                span.set_attribute("key", "value")
    finally:
        for tracing_adapter in adapters:
            tracing_adapter.close()
