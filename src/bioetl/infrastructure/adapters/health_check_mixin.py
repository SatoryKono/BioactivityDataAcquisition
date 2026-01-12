"""Health check mixin for unified observability in adapters.

Provides standardized logging and metrics for health_check() methods.
Used by both BaseHttpAdapter and BaseSyncAdapter for consistent behavior.

Observability Contract (RULES.md §4.8):
- SUCCESS: DEBUG log "health_check_passed", increment success counter
- FAILURE: WARNING log "health_check_failed" with details, increment failure counter
- LATENCY: Record duration histogram for all health checks
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort


# Default health check timeout per RULES.md §11.3
DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS: float = 5.0


@dataclass
class HealthCheckContext:
    """Context for health check operations.

    Holds timing and result data for observability purposes.

    Attributes:
        start_time: Monotonic timestamp when check started.
        provider: Provider name for metric labels.
        endpoint: Health check endpoint for logging.

    """

    start_time: float = field(default_factory=time.monotonic)
    provider: str = ""
    endpoint: str = ""

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since start."""
        return time.monotonic() - self.start_time


class HealthCheckMixin:
    """Mixin providing unified health check observability.

    Provides standardized logging and metrics for health checks.
    Used by both BaseHttpAdapter and BaseSyncAdapter.

    Metrics emitted:
    - health_check_success_total{provider}: Counter of successful checks
    - health_check_failures_total{provider}: Counter of failed checks
    - health_check_latency_seconds{provider}: Histogram of check durations

    Usage:
        class MyAdapter(HealthCheckMixin, BaseHttpAdapter):
            async def health_check(self) -> HealthStatus:
                ctx = self._start_health_check()
                try:
                    status = await self._probe_health()
                    self._handle_health_check_success(ctx, status)
                    return status
                except Exception as e:
                    return self._handle_health_check_failure(ctx, e)

    """

    # Type hints for attributes provided by the implementing class
    logger: LoggerPort
    metrics: MetricsPort | None
    provider_name: str

    def _get_metrics(self) -> MetricsPort:
        """Get metrics port, falling back to NoOpMetrics if None.

        Returns:
            MetricsPort instance (never None).

        """
        from bioetl.domain.ports.noop import NoOpMetrics

        return self.metrics if self.metrics is not None else NoOpMetrics()

    def _start_health_check(self) -> HealthCheckContext:
        """Start a health check context for timing.

        Returns:
            HealthCheckContext with start time and provider info.

        """
        return HealthCheckContext(
            start_time=time.monotonic(),
            provider=self.provider_name,
            endpoint=self._get_health_endpoint(),
        )

    def _get_health_endpoint(self) -> str:
        """Get the health check endpoint for this adapter.

        Subclasses SHOULD override this to return the specific endpoint
        used for health probes. Default returns empty string.

        Returns:
            Health check endpoint path.

        """
        return ""

    def _handle_health_check_success(
        self,
        ctx: HealthCheckContext,
        status: HealthStatus,
    ) -> None:
        """Handle successful health check with logging and metrics.

        Logs at DEBUG level and increments success counter.

        Args:
            ctx: Health check context with timing info.
            status: The resulting health status.

        """
        elapsed = ctx.elapsed_seconds
        labels = {"provider": ctx.provider}

        # Log success at DEBUG level
        self.logger.debug(
            "health_check_passed",
            provider=ctx.provider,
            endpoint=ctx.endpoint,
            status=status.value,
            latency_seconds=elapsed,
        )

        # Record metrics
        metrics = self._get_metrics()
        metrics.increment_counter(
            "health_check_success_total",
            1,
            labels,
        )
        metrics.observe_histogram(
            "health_check_latency_seconds",
            elapsed,
            labels,
        )

    def _handle_health_check_failure(
        self,
        ctx: HealthCheckContext,
        error: Exception,
    ) -> HealthStatus:
        """Handle health check failure with logging and metrics.

        Logs at WARNING level with error details and increments failure counter.

        Args:
            ctx: Health check context with timing info.
            error: The exception that caused the failure.

        Returns:
            HealthStatus.UNHEALTHY as fallback status.

        """
        elapsed = ctx.elapsed_seconds
        labels = {"provider": ctx.provider}

        # Log failure at WARNING level with full context
        self.logger.warning(
            "health_check_failed",
            provider=ctx.provider,
            endpoint=ctx.endpoint,
            error_type=type(error).__name__,
            error_message=str(error),
            latency_seconds=elapsed,
        )

        # Record metrics
        metrics = self._get_metrics()
        metrics.increment_counter(
            "health_check_failures_total",
            1,
            labels,
        )
        metrics.observe_histogram(
            "health_check_latency_seconds",
            elapsed,
            labels,
        )

        return HealthStatus.UNHEALTHY
