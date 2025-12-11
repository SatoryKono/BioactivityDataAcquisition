"""Client metrics contracts.

This module defines contracts for collecting and reporting metrics
from external client operations, including request counts, latencies,
and error rates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass(frozen=True)
class ClientMetrics:
    """Aggregated metrics for external client operations.

    Provides summary statistics for client operations over a time period.

    Attributes:
        requests_total: Total number of requests made.
        requests_success: Number of successful requests.
        requests_failed: Number of failed requests.
        retries_total: Total number of retry attempts.
        latency_seconds_avg: Average latency in seconds.
        latency_seconds_p50: 50th percentile latency.
        latency_seconds_p95: 95th percentile latency.
        latency_seconds_p99: 99th percentile latency.
    """

    requests_total: int
    requests_success: int
    requests_failed: int
    retries_total: int
    latency_seconds_avg: float
    latency_seconds_p50: float = 0.0
    latency_seconds_p95: float = 0.0
    latency_seconds_p99: float = 0.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage.

        Returns:
            Success rate (0.0 to 1.0) or 0.0 if no requests.
        """
        if self.requests_total == 0:
            return 0.0
        return self.requests_success / self.requests_total

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage.

        Returns:
            Error rate (0.0 to 1.0) or 0.0 if no requests.
        """
        if self.requests_total == 0:
            return 0.0
        return self.requests_failed / self.requests_total


@dataclass
class RequestMetricEvent:
    """Single request metric event.

    Captures metrics for a single request for later aggregation.

    Attributes:
        client_name: Name of the client.
        operation: Operation performed.
        success: Whether request succeeded.
        latency_seconds: Request latency in seconds.
        retry_count: Number of retries performed.
        error_type: Type of error if failed.
    """

    client_name: str
    operation: str
    success: bool
    latency_seconds: float
    retry_count: int = 0
    error_type: str | None = None


class ClientMetricsPortABC(ABC):
    """Port for collecting client metrics.

    Provides an interface for recording metrics from external client
    operations. Implementations should collect and aggregate these
    metrics for monitoring and alerting.

    Example:
        >>> metrics: ClientMetricsPortABC = ...
        >>> with metrics.timed_operation("chembl", "fetch_activities"):
        ...     result = client.fetch_activities()
        >>> metrics.record_request("chembl", "fetch_activities", success=True)
    """

    @abstractmethod
    def record_request(
        self,
        client_name: str,
        operation: str,
        *,
        success: bool,
        latency_seconds: float,
        retry_count: int = 0,
        error_type: str | None = None,
    ) -> None:
        """Record metrics for a single request.

        Args:
            client_name: Name of the client (e.g., "chembl").
            operation: Operation performed (e.g., "fetch_activities").
            success: Whether request succeeded.
            latency_seconds: Request latency in seconds.
            retry_count: Number of retries performed.
            error_type: Type of error if failed (e.g., "timeout").
        """
        ...

    @abstractmethod
    def get_metrics(self, client_name: str) -> ClientMetrics:
        """Get aggregated metrics for client.

        Args:
            client_name: Name of the client.

        Returns:
            Aggregated ClientMetrics for the client.
        """
        ...

    @abstractmethod
    @contextmanager
    def timed_operation(
        self,
        client_name: str,
        operation: str,
    ) -> Iterator[None]:
        """Context manager for timing operations.

        Automatically records latency when context exits.

        Args:
            client_name: Name of the client.
            operation: Operation being performed.

        Yields:
            None - timing is handled automatically.

        Example:
            >>> with metrics.timed_operation("chembl", "fetch"):
            ...     result = do_fetch()
        """
        ...

    @abstractmethod
    def reset_metrics(self, client_name: str | None = None) -> None:
        """Reset collected metrics.

        Args:
            client_name: Client to reset, or None for all.
        """
        ...


class InMemoryClientMetrics(ClientMetricsPortABC):
    """In-memory implementation of client metrics.

    Simple implementation that stores metrics in memory.
    Suitable for testing and development.
    """

    def __init__(self) -> None:
        """Initialize empty metrics store."""
        self._events: dict[str, list[RequestMetricEvent]] = {}

    def record_request(
        self,
        client_name: str,
        operation: str,
        *,
        success: bool,
        latency_seconds: float,
        retry_count: int = 0,
        error_type: str | None = None,
    ) -> None:
        """Record metrics for a single request."""
        if client_name not in self._events:
            self._events[client_name] = []

        self._events[client_name].append(
            RequestMetricEvent(
                client_name=client_name,
                operation=operation,
                success=success,
                latency_seconds=latency_seconds,
                retry_count=retry_count,
                error_type=error_type,
            )
        )

    def get_metrics(self, client_name: str) -> ClientMetrics:
        """Get aggregated metrics for client."""
        events = self._events.get(client_name, [])

        if not events:
            return ClientMetrics(
                requests_total=0,
                requests_success=0,
                requests_failed=0,
                retries_total=0,
                latency_seconds_avg=0.0,
            )

        total = len(events)
        success = sum(1 for e in events if e.success)
        failed = total - success
        retries = sum(e.retry_count for e in events)
        latencies = [e.latency_seconds for e in events]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        # Calculate percentiles
        sorted_latencies = sorted(latencies)
        p50 = sorted_latencies[int(len(sorted_latencies) * 0.5)] if sorted_latencies else 0.0
        p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)] if sorted_latencies else 0.0
        p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)] if sorted_latencies else 0.0

        return ClientMetrics(
            requests_total=total,
            requests_success=success,
            requests_failed=failed,
            retries_total=retries,
            latency_seconds_avg=avg_latency,
            latency_seconds_p50=p50,
            latency_seconds_p95=p95,
            latency_seconds_p99=p99,
        )

    @contextmanager
    def timed_operation(
        self,
        client_name: str,
        operation: str,
    ) -> Iterator[None]:
        """Context manager for timing operations."""
        import time

        start = time.perf_counter()
        success = True
        error_type = None

        try:
            yield
        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise
        finally:
            latency = time.perf_counter() - start
            self.record_request(
                client_name,
                operation,
                success=success,
                latency_seconds=latency,
                error_type=error_type,
            )

    def reset_metrics(self, client_name: str | None = None) -> None:
        """Reset collected metrics."""
        if client_name is None:
            self._events.clear()
        else:
            self._events.pop(client_name, None)


__all__ = [
    "ClientMetrics",
    "ClientMetricsPortABC",
    "InMemoryClientMetrics",
    "RequestMetricEvent",
]
