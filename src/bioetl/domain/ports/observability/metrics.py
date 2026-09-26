"""Metrics protocol ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable

MetricLabels = dict[str, str]

# Core allowlist from the domain metrics contract (#11223).
ALLOWED_CORE_METRIC_LABEL_KEYS = frozenset(
    {
        "provider",
        "pipeline",
        "entity",
        "layer",
        "stage",
        "status",
        "error_type",
    }
)

# Superseding contract: bounded metric-specific keys used by registered series.
# Keys outside CORE ∪ EXTENDED are rejected at the port boundary.
ALLOWED_EXTENDED_METRIC_LABEL_KEYS = frozenset(
    {
        "action",
        "adapter",
        "anomaly_type",
        "check_type",
        "comparison",
        "component",
        "decision_type",
        "disposition",
        "drift_type",
        "dry_run",
        "endpoint",
        "entity_type",
        "error_category",
        "error_code",
        "error_kind",
        "event",
        "event_type",
        "field",
        "final_reason",
        "flow_stage",
        "handling",
        "integrity_type",
        "invariant",
        "layer_filter",
        "loss_kind",
        "method",
        "metric",
        "mode",
        "monitor_mode",
        "operation",
        "outcome",
        "phase",
        "pipeline_context",
        "provider_context",
        "reason",
        "reason_code",
        "ref_type",
        "replay_capability",
        "replay_impact",
        "retry_kind",
        "retry_type",
        "risk_type",
        "rule_type",
        "run_type",
        "run_type_context",
        "selected_source",
        "severity",
        "source_kind",
        "state",
        "step_kind",
        "store",
        "strict_requirement",
        "surface",
        "table",
        "target",
        "terminal_status",
        "workflow",
    }
)

ALLOWED_METRIC_LABEL_KEYS = (
    ALLOWED_CORE_METRIC_LABEL_KEYS | ALLOWED_EXTENDED_METRIC_LABEL_KEYS
)

# High-cardinality / identity keys never accepted at the metrics port boundary.
FORBIDDEN_METRIC_LABEL_KEYS = frozenset(
    {
        "run_id",
        "run",
        "manifest_id",
        "lineage_fragment_id",
        "record_id",
        "record",
        "content_hash",
        "payload_hash",
        "request_id",
        "message",
        "raw_message",
        "raw_exception_message",
        "error",
        "error_message",
        "exception",
        "traceback",
        "path",
        "raw_path",
        "source_file",
        "file_path",
        "filesystem_path",
        "url",
        "raw_url",
        "uri",
        "query",
        "query_string",
        "dataset_hash",
        "source_batch_id",
    }
)


def resolve_metric_labels(
    labels: MetricLabels | None = None,
) -> MetricLabels:
    """Resolve canonical metric labels.

    Accepts only keys in :data:`ALLOWED_METRIC_LABEL_KEYS` (core seven keys
    plus the documented superseding extended bounded set). Raises
    :class:`ValueError` for forbidden identity/free-form keys or any
    unrecognized key. Returns a shallow copy so callers cannot mutate the
    resolved mapping through the input dict.

    Args:
        labels: Canonical metric labels dict.

    Returns:
        Resolved metric labels dict. Returns an empty dict if ``labels`` is None.
    """
    if not labels:
        return {}
    keys = frozenset(labels)
    forbidden = keys & FORBIDDEN_METRIC_LABEL_KEYS
    if forbidden:
        forbidden_names = ", ".join(sorted(forbidden))
        raise ValueError(
            f"Forbidden metric label key(s): {forbidden_names}"
        )
    unrecognized = keys - ALLOWED_METRIC_LABEL_KEYS
    if unrecognized:
        unrecognized_names = ", ".join(sorted(unrecognized))
        raise ValueError(
            f"Unrecognized metric label key(s): {unrecognized_names}"
        )
    return dict(labels)


@runtime_checkable
class MetricsPort(Protocol):
    """Port for metrics collection."""

    def observe_histogram(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Record an observed value in a histogram metric.

        Args:
            name: Histogram metric name.
            value: Observed numeric value to record.
            labels: Canonical metric labels.
        """
        ...

    def increment_counter(
        self,
        name: str,
        value: int,
        labels: MetricLabels | None = None,
    ) -> None:
        """Increment a counter metric by the given value.

        Args:
            name: Counter metric name.
            value: Amount to increment the counter by.
            labels: Canonical metric labels.
        """
        ...

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: MetricLabels | None = None,
    ) -> None:
        """Set a gauge metric to the given value.

        Args:
            name: Gauge metric name.
            value: New gauge value to set.
            labels: Canonical metric labels.
        """
        ...

    def close(self) -> None:
        """Flush pending metrics and release backend resources."""
        ...


@runtime_checkable
class ExecutorMetricsPort(Protocol):
    """Protocol for executors providing batch metrics."""

    records_fetched: int
    records_bronze: int
    records_silver: int
    records_gold: int
    records_quarantined: int


@dataclass(frozen=True, slots=True)
class MetricsServerRuntimeStatus:
    """Live metrics server runtime metadata."""

    running: bool
    port: int | None = None
    addr: str | None = None
    started_at: datetime | None = None


@runtime_checkable
class MetricsServerPort(Protocol):
    """Protocol for metrics server operations."""

    def start(
        self,
        port: int,
        addr: str = "127.0.0.1",
        *,
        started_at: datetime | None = None,
        fail_fast: bool = False,
        retry_count: int = 3,
        retry_delay: float = 1.0,
    ) -> bool:
        """Start the metrics HTTP server on the given port.

        Args:
            port: TCP port to bind the server to.
            addr: Bind address for the HTTP server. Defaults to ``127.0.0.1``.
                Pass ``0.0.0.0`` explicitly when the server must listen on all interfaces.
            started_at: Explicit application-owned startup timestamp for runtime
                status bookkeeping.
            fail_fast: If True, raise immediately on bind failure instead of retrying.
            retry_count: Number of times to retry on transient bind errors. Defaults to 3.
            retry_delay: Seconds to wait between retries. Defaults to 1.0.

        Returns:
            True if the server started successfully, False otherwise.
        """
        ...

    def is_running(self) -> bool:
        """Return True if the metrics server is currently accepting connections."""
        ...

    def get_runtime_status(self) -> MetricsServerRuntimeStatus:
        """Return the current in-process metrics server runtime metadata."""
        ...

    def reset(self) -> None:
        """Reset all collected metric values to their initial state."""
        ...


@runtime_checkable
class MetricsPublisherPort(Protocol):
    """Protocol for explicit metrics publication workflows."""

    def push_to_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
        metric_names: tuple[str, ...] | None = None,
    ) -> bool:
        """Publish the current metrics snapshot to a gateway backend."""
        ...

    def delete_from_gateway(
        self,
        *,
        gateway: str,
        run_label: str,
        grouping_key: MetricLabels | None = None,
    ) -> bool:
        """Delete the current bounded metrics snapshot from a gateway backend."""
        ...


@runtime_checkable
class HealthMetricsExpositionPort(Protocol):
    """Port for Prometheus text exposition on the health-server scrape path."""

    def build_exposition(self) -> str:
        """Return Prometheus text exposition body for ``GET /metrics``."""
        ...
