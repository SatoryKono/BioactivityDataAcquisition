"""Infrastructure adapters for observability ports."""

from __future__ import annotations

from typing import Any, Self

import structlog
from structlog.stdlib import BoundLogger

from bioetl.infrastructure.observability import metrics
from bioetl.interfaces.observability import LoggingPortABC, MetricsPortABC, TracingPortABC


class StructuredLoggerImpl(LoggingPortABC):
    """Structured logger adapter built on top of structlog."""

    def __init__(self, logger: BoundLogger | None = None) -> None:
        self._logger = logger or structlog.get_logger()

    def info(self, msg: str, **ctx: Any) -> None:
        """Log info message with structured context."""
        self._logger.info(msg, **ctx)

    def error(self, msg: str, **ctx: Any) -> None:
        """Log error message with structured context."""
        self._logger.error(msg, **ctx)

    def debug(self, msg: str, **ctx: Any) -> None:
        """Log debug message with structured context."""
        self._logger.debug(msg, **ctx)

    def warning(self, msg: str, **ctx: Any) -> None:
        """Log warning message with structured context."""
        self._logger.warning(msg, **ctx)

    def apply_bind(self, **ctx: Any) -> Self:
        """Return logger bound with additional context."""
        return self.__class__(self._logger.bind(**ctx))


class TracingAdapterImpl(TracingPortABC):
    """No-op tracing adapter placeholder for distributed tracing backends."""

    def start_span(self, name: str) -> dict[str, str]:
        """Start a tracing span (no-op stub)."""
        return {"span": name}

    def end_span(self, span: Any) -> None:  # pragma: no cover - no-op
        """Finish a tracing span (no-op)."""
        _ = span

    def inject_context(
        self, headers: dict[str, str]
    ) -> None:  # pragma: no cover - no-op
        """Inject tracing context into headers (no-op stub)."""
        headers.update({"trace": "noop"})


__all__ = [
    "StructuredLoggerImpl",
    "PrometheusMetricsPortImpl",
    "TracingAdapterImpl",
]


class PrometheusMetricsPortImpl(MetricsPortABC):
    """Prometheus-backed implementation of the metrics port."""

    def __init__(self) -> None:
        self._counters: dict[str, Any] = {
            "client_request_total": metrics.CLIENT_REQUEST_TOTAL,
            "client_request_errors": metrics.CLIENT_REQUEST_ERRORS,
            "output_write_errors_total": metrics.OUTPUT_WRITE_ERRORS_TOTAL,
        }
        self._histograms: dict[str, Any] = {
            "client_request_duration_seconds": metrics.CLIENT_REQUEST_DURATION_SECONDS,
        }

    def inc_counter(self, name: str, labels: dict[str, str]) -> None:
        """Increment counter by name using provided labels."""

        counter = self._counters.get(name)
        if counter is None:
            raise KeyError(f"Unknown counter metric '{name}'")
        counter.labels(**labels).inc()

    def observe_histogram(
        self, name: str, value: float, labels: dict[str, str]
    ) -> None:
        """Record observation for histogram by name."""

        histogram = self._histograms.get(name)
        if histogram is None:
            raise KeyError(f"Unknown histogram metric '{name}'")
        histogram.labels(**labels).observe(value)

    def update_stage_duration(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
        duration_sec: float,
    ) -> None:
        """Update stage duration histogram."""
        metrics.STAGE_DURATION_SECONDS.labels(
            pipeline=pipeline,
            provider=provider,
            entity=entity,
            stage=stage,
            outcome=outcome,
        ).observe(duration_sec)

    def update_stage_total(
        self,
        *,
        pipeline: str,
        provider: str,
        entity: str,
        stage: str,
        outcome: str,
    ) -> None:
        """Increment stage execution counter."""
        metrics.STAGE_TOTAL.labels(
            pipeline=pipeline,
            provider=provider,
            entity=entity,
            stage=stage,
            outcome=outcome,
        ).inc()
