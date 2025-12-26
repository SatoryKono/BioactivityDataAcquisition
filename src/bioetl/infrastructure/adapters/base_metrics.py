"""Base metrics instrumentation for adapters.

Provides standardized SLA metrics collection for all HTTP adapters.
Implements RULES.md observability requirements for adapter monitoring.

Metrics collected:
- adapter_request_duration_seconds: Histogram of request durations
- adapter_requests_total: Counter of total requests (success/error)
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


@dataclass
class AdapterMetrics:
    """Metrics instrumentation for adapter requests.

    Collects SLA-relevant metrics for adapter HTTP requests including
    latency histograms and request counters with success/error status.

    Args:
        metrics: MetricsPort implementation for recording metrics.
        provider: Provider name for metric labels (e.g., "chembl", "uniprot").

    Example:
        >>> from bioetl.domain.ports.noop import NoOpMetrics
        >>> metrics = AdapterMetrics(NoOpMetrics(), "chembl")
        >>> with metrics.measure_request("/activity"):
        ...     # perform HTTP request
        ...     pass

    """

    metrics: MetricsPort
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

        """
        start = time.perf_counter()
        status = "success"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.perf_counter() - start
            labels = {"provider": self.provider, "endpoint": endpoint}

            self.metrics.observe_histogram(
                "adapter_request_duration_seconds",
                duration,
                labels,
            )

            self.metrics.increment_counter(
                "adapter_requests_total",
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
        self.metrics.observe_histogram(
            "adapter_batch_size",
            float(size),
            {"provider": self.provider, "endpoint": endpoint},
        )
