"""Provider health-check template extracted from the observability mixin."""

from __future__ import annotations

import asyncio
from abc import abstractmethod
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.decorators._retry_support import (
    _redact_transport_error_message,
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
from bioetl.infrastructure.adapters.health_check_mixin import HealthCheckMixin

if TYPE_CHECKING:
    from bioetl.domain.ports import CircuitBreakerPort, HealthCheckResult

__all__ = ["HealthCheckProviderMixin"]


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
                last_error=_redact_transport_error_message(str(error)),
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
