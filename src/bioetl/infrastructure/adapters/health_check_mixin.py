"""Health check mixin for unified observability in adapters.

Provides standardized logging and metrics for health_check() methods.
Used by both BaseHttpAdapter and BaseSyncAdapter for consistent behavior.

Observability Contract (RULES.md §4.8):
- SUCCESS: DEBUG log "health_check_passed", increment success counter
- FAILURE: WARNING log "health_check_failed" with details, increment failure counter
- LATENCY: Record duration histogram for all health checks

Architecture Note:
- HealthCheckMixin: Base observability helpers (_start_health_check, etc.)
- HealthCheckProviderMixin: Full health check implementation with abstract _circuit_breaker
  property. Eliminates duplication between BaseHttpAdapter and BaseSyncAdapter.
"""

from __future__ import annotations

import time
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.ports.health_check import HealthCheckResult
    from bioetl.domain.ports.resilience import CircuitBreakerPort


# Default health check timeout per RULES.md §11.3
DEFAULT_HEALTH_CHECK_TIMEOUT_SECONDS: float = 5.0


@runtime_checkable
class HealthCheckObservability(Protocol):
    """Protocol for adapters using HealthCheckMixin.

    Adapters must provide logger, metrics, and provider_name attributes.
    """

    logger: LoggerPort
    metrics: MetricsPort
    provider_name: str

    def _get_health_endpoint(self) -> str:
        """Return the health check endpoint path."""
        ...


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
    - _circuit_breaker: Property returning the CircuitBreaker instance

    Usage:
        class MyAdapter(HealthCheckProviderMixin, DataSourcePort):
            @property
            def _circuit_breaker(self) -> CircuitBreaker:
                return self.http_client.circuit_breaker

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
        - BaseHttpAdapter: return self.http_client.circuit_breaker
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
        - SUCCESS: DEBUG log, success counter, latency histogram
        - FAILURE: WARNING log with details, failure counter, latency histogram

        Returns:
            HealthStatus from probe or fallback.

        """
        ctx = self._start_health_check()
        try:
            status = await self._probe_health()
            self._handle_health_check_success(ctx, status)
            return status
        except Exception as e:
            fallback_status = self._fallback_health_status()
            # Log and record metrics for the failure
            self._handle_health_check_failure(ctx, e)
            return fallback_status

    async def check_health(self) -> HealthCheckResult:
        """Perform health check and return detailed result.

        This method provides enhanced health check with latency tracking
        and error details. It wraps the Template Method pattern used by
        health_check() with additional metrics.

        Observability (via HealthCheckMixin):
        - SUCCESS: DEBUG log, success counter, latency histogram
        - FAILURE: WARNING log with details, failure counter, latency histogram

        Returns:
            HealthCheckResult with status, latency, and error details.

        Note:
            This method never raises exceptions. All errors are caught
            and returned as UNHEALTHY status with error details.

        """
        # Import here to avoid circular imports
        from bioetl.domain.ports.health_check import HealthCheckResult

        ctx = self._start_health_check()
        last_error: str | None = None
        consecutive_failures = 0

        try:
            status = await self._probe_health()
            self._handle_health_check_success(ctx, status)
        except Exception as e:
            last_error = str(e)
            status = self._fallback_health_status()
            # Log and record metrics for the failure
            self._handle_health_check_failure(ctx, e)
            # Get failure count from circuit breaker
            try:
                consecutive_failures = self._circuit_breaker.get_failure_count()
            except Exception:
                consecutive_failures = 1

        latency_ms = ctx.elapsed_seconds * 1000

        return HealthCheckResult(
            status=status,
            latency_ms=latency_ms,
            provider=self.provider_name,
            endpoint=self._get_health_endpoint(),
            last_error=last_error,
            consecutive_failures=consecutive_failures,
        )

    async def _probe_health(self) -> HealthStatus:
        """Perform provider-specific health probe.

        Subclasses SHOULD override this with a specific API call (e.g. /health).
        Default implementation returns fallback health status.

        Returns:
            HealthStatus from the health probe.

        """
        return self._fallback_health_status()

    def _fallback_health_status(self) -> HealthStatus:
        """Get health status from circuit breaker state.

        Used as fallback when _probe_health() fails or is not implemented.

        Returns:
            HealthStatus based on circuit breaker state.

        """
        from bioetl.infrastructure.adapters.http.health import (
            assess_health_from_circuit_breaker,
        )

        try:
            return assess_health_from_circuit_breaker(self._circuit_breaker)
        except Exception:
            return HealthStatus.UNHEALTHY

    def _get_error_context(self, operation: str) -> dict[str, Any]:
        """Build error context with circuit breaker info.

        Args:
            operation: Operation name for context.

        Returns:
            Context dictionary for error handling.

        """
        try:
            cb_state = self._circuit_breaker.get_state().value
            cb_failures = self._circuit_breaker.get_failure_count()
        except Exception:
            cb_state = None
            cb_failures = 0

        return {
            "circuit_breaker_state": cb_state,
            "circuit_breaker_failures": cb_failures,
        }
