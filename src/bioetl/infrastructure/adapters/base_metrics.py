"""Base metrics instrumentation for adapters.

Provides standardized SLA metrics collection for all HTTP adapters.
Implements RULES.md observability requirements for adapter monitoring.

Metrics collected:
- adapter_request_duration_seconds: Histogram of request durations
- adapter_requests_total: Counter of total requests (success/error)
"""

from __future__ import annotations

__all__ = ["ADAPTER_REQUEST_ERRORS", "AdapterMetricsRecorder"]


import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import BioETLError
from bioetl.infrastructure.observability._prometheus_metric_label_normalizers import (
    normalize_adapter_endpoint_label,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


ADAPTER_REQUEST_ERRORS = (
    BioETLError,
    OSError,
    ConnectionError,
    TimeoutError,
    RuntimeError,
    ValueError,
    TypeError,
)


@dataclass
class AdapterMetricsRecorder:
    """Metrics instrumentation for adapter requests.

    Collects SLA-relevant metrics for adapter HTTP requests including
    latency histograms and request counters with success/error status.

    Args:
        metrics: MetricsPort implementation for recording metrics.
        provider: Provider name for metric labels (e.g., "chembl", "uniprot").

    Example:
        >>> from bioetl.domain.ports.noop import NoOpMetrics
        >>> metrics = AdapterMetricsRecorder(NoOpMetrics(), "chembl")
        >>> with metrics.measure_request("/activity"):
        ...     # perform HTTP request
        ...     pass

    """

    metrics: MetricsPort | None
    provider: str

    @contextmanager
    def measure_request(self, endpoint: str) -> Iterator[None]:
        """Measure request duration and record metrics.

        Context manager that records the duration of an HTTP request
        and increments appropriate success/error counters.

        Args:
            endpoint: API endpoint being called (e.g., "/activity", "/compound").

        Yields:
            None - execution context for the request.

        Records:
            - adapter_request_duration_seconds: Histogram with provider/endpoint labels
            - adapter_requests_total: Counter with provider/endpoint/status labels

        Returns:
            Iterator over results.
        """
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except ADAPTER_REQUEST_ERRORS:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            normalized_endpoint = normalize_adapter_endpoint_label(endpoint)
            labels = {"provider": self.provider, "endpoint": normalized_endpoint}
            if self.metrics is not None:
                self.metrics.observe_histogram(
                    "bioetl_adapter_request_duration_seconds",
                    duration,
                    labels,
                )

                self.metrics.increment_counter(
                    "bioetl_adapter_requests_total",
                    1,
                    {**labels, "status": status},
                )

    def record_batch_size(self, endpoint: str, size: int) -> None:
        """Record batch size for a request.

        Useful for monitoring effective batch sizes, especially when
        adapters reduce batch size during degraded health states.

        Args:
            endpoint: API endpoint being called.
            size: Number of records in the batch.

        Records:
            - adapter_batch_size: Histogram with provider/endpoint labels

        """
        if self.metrics is None:
            return
        normalized_endpoint = normalize_adapter_endpoint_label(endpoint)
        self.metrics.observe_histogram(
            "bioetl_adapter_batch_size",
            float(size),
            {"provider": self.provider, "endpoint": normalized_endpoint},
        )

    def record_dropped_duplicates(self, entity_type: str, count: int = 1) -> None:
        """Record dropped duplicate records during deduplication.

        Tracks how many records are dropped due to duplicate keys.
        Useful for monitoring deduplication effectiveness and identifying
        potential data quality issues.

        Args:
            entity_type: Entity type being deduplicated (e.g., 'publication_term').
            count: Number of duplicates dropped (default 1).

        Records:
            - adapter_dropped_duplicates_total: Counter with provider/entity_type labels

        """
        if self.metrics is None:
            return
        self.metrics.increment_counter(
            "bioetl_adapter_dropped_duplicates_total",
            count,
            {"provider": self.provider, "entity_type": entity_type},
        )

    def record_fallback_outcome(
        self,
        operation: str,
        *,
        candidates: int,
        hits: int,
    ) -> None:
        """Record fallback attempt/hit counters and hit-rate gauge.

        Tracks how many fallback candidates were attempted and how many
        resulted in a successful hit. Emits attempt/hit counters and a
        derived hit-rate gauge clamped to [0.0, 1.0].

        Args:
            operation: Name of the fallback operation being tracked
                (e.g., "title_fallback", "doi_resolution").
            candidates: Total number of fallback candidates attempted.
                Clamped to zero if negative.
            hits: Number of successful fallback hits.
                Clamped to [0, candidates].

        """
        total_candidates = max(candidates, 0)
        total_hits = max(0, min(hits, total_candidates))
        labels = {"provider": self.provider, "operation": operation}

        if self.metrics is None:
            return

        if total_candidates > 0:
            self.metrics.increment_counter(
                "bioetl_adapter_fallback_attempts_total",
                total_candidates,
                labels,
            )
        if total_hits > 0:
            self.metrics.increment_counter(
                "bioetl_adapter_fallback_hits_total",
                total_hits,
                labels,
            )

        hit_rate = (total_hits / total_candidates) if total_candidates else 0.0
        self.metrics.set_gauge("bioetl_adapter_fallback_hit_rate", hit_rate, labels)
