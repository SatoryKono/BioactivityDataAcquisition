# pyright: reportUninitializedInstanceVariable=false
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
    "HealthCheckProviderMixin",
]

import asyncio
import time
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters._health_check_observability import (
    handle_health_check_failure,
    handle_health_check_result,
    start_health_check,
)
from bioetl.infrastructure.adapters._health_check_policy import (
    _HealthCheckProbeOutcome,
    build_error_context,
    fallback_health_status,
    get_consecutive_health_failures,
    resolve_failure_health_status,
)
from bioetl.infrastructure.adapters.health_check_contract import (
    HEALTH_CHECK_ERRORS,
    HealthCheckContext,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        HealthCheckResult,
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
    logger: LoggerPort
    metrics: MetricsPort | None
    provider_name: str
    _logger: LoggerPort

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


class HealthCheckProviderMixin(HealthCheckMixin):
    """Extended mixin providing full health check implementation.

    Consolidates health check logic from BaseHttpAdapter and BaseSyncAdapter
    to eliminate code duplication. Uses abstract property _circuit_breaker
    to allow different circuit breaker access patterns.

    Implements Template Method pattern for health checks:
    - health_check(): Template method with try/except and observability
    - check_health(): Detailed result with latency and error info
    - _probe_health(): Override for provider-specific health probe
    - _fallback_health_status(): Fallback using circuit breaker state
    - _get_error_context(): Build error context for logging

    Subclasses MUST implement:
    - _circuit_breaker: Property returning the CircuitBreakerGuard instance

    Usage:
        class MyAdapter(HealthCheckProviderMixin, DataSourcePort):
            @property
            def _circuit_breaker(self) -> CircuitBreakerGuard:
                return self._http_client.circuit_breaker

            async def _probe_health(self) -> HealthStatus:
                # Provider-specific health probe
                ...

    """

    @property
    @abstractmethod
    def _circuit_breaker(self) -> CircuitBreakerPort:
        """Return the circuit breaker instance for health fallback.

        Subclasses MUST implement this property to provide access to
        their circuit breaker, regardless of how it's stored:
        - BaseHttpAdapter: return self._http_client.circuit_breaker
        - BaseSyncAdapter: return self.circuit_breaker

        Returns:
            CircuitBreakerPort instance for health status assessment.

        """
        ...

    async def health_check(self) -> HealthStatus:
        """Check API health status using Template Method pattern.

            Calls _probe_health() for provider-specific probe, falling back
            to _fallback_health_status() on any exception.

            Observability (via HealthCheckMixin):
        - HEALTHY: DEBUG log, healthy counter, latency histogram
        - DEGRADED: WARNING log, degraded counter, latency histogram
        - FAILED/UNHEALTHY: WARNING log with details, failure counter, latency histogram

            Returns:
                HealthStatus from probe or fallback.

        """
        ctx = self._start_health_check()
        try:
            status = await self._probe_health()
            self._handle_health_check_result(ctx, status)
            return status
        except HEALTH_CHECK_ERRORS as e:
            fallback_status = self._fallback_health_status()
            # Log and record metrics for the failure
            self._handle_health_check_failure(ctx, e)
            return self._resolve_failure_health_status(
                error=e,
                fallback_status=fallback_status,
            )

    def _resolve_failure_health_status(
        self,
        *,
        error: Exception,
        fallback_status: HealthStatus,
    ) -> HealthStatus:
        """Resolve final health status for failed probe without masking issues.

        Guardrail:
        - Probe exceptions never return ``HEALTHY``.
        - Transient transport/upstream failures downgrade to ``DEGRADED``
          unless circuit breaker already reports ``UNHEALTHY``.
        """
        return resolve_failure_health_status(
            error=error,
            fallback_status=fallback_status,
        )

    async def check_health(self) -> HealthCheckResult:
        """Run probe health check and return status, latency, and failure context."""
        # Import here to avoid circular imports
        from bioetl.domain.ports import HealthCheckResult

        ctx = self._start_health_check()
        probe_outcome = await self._collect_probe_outcome(ctx)
        return HealthCheckResult(
            status=probe_outcome.status,
            latency_ms=ctx.elapsed_seconds * 1000,
            provider=self.provider_name,
            endpoint=self._get_health_endpoint(),
            last_error=probe_outcome.last_error,
            consecutive_failures=probe_outcome.consecutive_failures,
        )

    async def _collect_probe_outcome(
        self,
        ctx: HealthCheckContext,
    ) -> _HealthCheckProbeOutcome:
        """Execute one provider probe and capture the normalized result state."""
        try:
            status = await self._probe_health()
            self._handle_health_check_result(ctx, status)
            return _HealthCheckProbeOutcome(status=status)
        except HEALTH_CHECK_ERRORS as error:
            self._handle_health_check_failure(ctx, error)
            return _HealthCheckProbeOutcome(
                status=self._resolve_failure_health_status(
                    error=error,
                    fallback_status=HealthStatus.UNHEALTHY,
                ),
                last_error=str(error),
                consecutive_failures=self._get_consecutive_health_failures(),
            )

    def _get_consecutive_health_failures(self) -> int:
        """Read circuit-breaker failure count with a conservative fallback."""
        return get_consecutive_health_failures(self._circuit_breaker)

    async def _probe_health(self) -> HealthStatus:
        """Perform provider-specific health probe.

        Subclasses SHOULD override this with a specific API call (e.g. /health).
        Default implementation returns fallback health status.

        Returns:
            HealthStatus from the health probe.

        """
        await asyncio.sleep(0)
        return self._fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state.

        Used as fallback when _probe_health() fails or is not implemented.

        Returns:
            HealthStatus based on circuit breaker state.

        """
        return fallback_health_status(self._circuit_breaker)

    def _get_error_context(
        self, operation: str
    ) -> JsonDict:  # Any: untyped API JSON record
        """Build error context with circuit breaker info.

        Args:
            operation: Operation name for context.

        Returns:
            Context dictionary for error handling.

        """
        del operation
        return build_error_context(self._circuit_breaker)
