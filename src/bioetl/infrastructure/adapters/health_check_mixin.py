# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
# Annotation-only host surface: do NOT assign None defaults — dataclass subclasses
# inherit those as field defaults (e.g. CrossRef mailto after logger). PD7 residual.
"""Health check mixin for unified observability in adapters.

Provides standardized logging and metrics for health_check() methods.
Used by both BaseHttpAdapter and BaseSyncAdapter for consistent behavior.

Observability Contract (RULES.md §4.8):
- HEALTHY: DEBUG log "health_check_passed", increment healthy counter
- DEGRADED: WARNING log "health_check_degraded", increment degraded counter
- FAILED/UNHEALTHY: WARNING log "health_check_failed"/"health_check_unhealthy", increment failure counter
- LATENCY: Record duration histogram for all health checks

Architecture Note:
- HealthCheckMixin: Base observability helpers (_start_health_check, etc.)
- HealthCheckProviderMixin: Full health check implementation with abstract _circuit_breaker
  property. Eliminates duplication between BaseHttpAdapter and BaseSyncAdapter.
"""

from __future__ import annotations

__all__ = [
    "HEALTH_CHECK_ERRORS",
    "HealthCheckContext",
    "HealthCheckMixin",
]

import time
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters._health_check_observability import (
    handle_health_check_failure,
    handle_health_check_result,
    start_health_check,
)
from bioetl.infrastructure.adapters.health_check_contract import (
    HEALTH_CHECK_ERRORS,
    HealthCheckContext,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
    )

# Preserve the module-level clock seam used by health-check tests.
HEALTH_CHECK_MONOTONIC = time.monotonic


class HealthCheckMixin:
    """Mixin providing unified health check observability.

    Provides standardized logging and metrics for health checks.
    Used by both BaseHttpAdapter and BaseSyncAdapter.

    Metrics emitted:
    - health_check_success_total{provider}: Counter of HEALTHY checks
    - health_check_degraded_total{provider}: Counter of DEGRADED checks
    - health_check_failures_total{provider}: Counter of failed/UNHEALTHY checks
    - health_check_latency_seconds{provider}: Histogram of check durations

    Usage:
        class MyAdapter(HealthCheckMixin, BaseHttpAdapter):
            async def health_check(self) -> HealthStatus:
                ctx = self._start_health_check()
                try:
                    status = await self._probe_health()
                    self._handle_health_check_result(ctx, status)
                    return status
                except HEALTH_CHECK_ERRORS as e:
                    return self._handle_health_check_failure(ctx, e)

    """

    # Annotation-only host surface. Do NOT assign None defaults: dataclass
    # subclasses inherit those as field defaults (e.g. CrossRef mailto after logger).
    logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]
    metrics: MetricsPort | None  # pyright: ignore[reportUninitializedInstanceVariable]
    provider_name: str  # pyright: ignore[reportUninitializedInstanceVariable]
    _logger: LoggerPort  # pyright: ignore[reportUninitializedInstanceVariable]

    def _get_metrics(self) -> MetricsPort | None:
        """Get metrics port for best-effort health-check telemetry.

        Returns:
            MetricsPort when configured, otherwise None.

        """
        return self.metrics

    def _start_health_check(self) -> HealthCheckContext:
        """Start a health check context for timing.

        Returns:
            HealthCheckContext with start time and provider info.

        """
        return start_health_check(
            provider_name=self.provider_name,
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

    def _handle_health_check_result(
        self,
        ctx: HealthCheckContext,
        status: HealthStatus,
    ) -> None:
        """Handle completed health check with status-aware logging and metrics.

        Args:
            ctx: Health check context with timing info.
            status: The resulting health status.

        """
        handle_health_check_result(
            logger=self._logger,
            metrics=self.metrics,
            ctx=ctx,
            status=status,
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
        return handle_health_check_failure(
            logger=self._logger,
            metrics=self.metrics,
            ctx=ctx,
            error=error,
        )
