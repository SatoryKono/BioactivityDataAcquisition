"""Health check port for external API health monitoring.

Implements RULES.md §3.5 - Provider Health Monitoring.

Provides standardized health check interface for all data source adapters
with detailed health status information including latency and error tracking.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports.observability import LoggerPort

__all__ = [
    "HealthCheckPort",
    "HealthCheckResult",
    "HealthMonitorPort",
    "HealthStatePort",
    "HealthStatusLiteral",
]


@dataclass(frozen=True, slots=True)
class HealthCheckResult:
    """Detailed result of a health check operation.

    Contains health status with additional context for monitoring and alerting.

    Attributes:
        status: Current health status (HEALTHY, DEGRADED, UNHEALTHY).
        latency_ms: Time taken for the health check probe in milliseconds.
        last_error: Description of the last error encountered (if any).
        consecutive_failures: Number of consecutive health check failures.
        checked_at: Timestamp when the health check was performed.
        provider: Name of the provider being checked.
        endpoint: The endpoint used for the health check probe.

    Example:
        >>> result = HealthCheckResult(
        ...     status=HealthStatus.HEALTHY,
        ...     latency_ms=45.3,
        ...     provider="chembl",
        ...     endpoint="/chembl/api/data/status.json",
        ... )
        >>> result.is_healthy
        True

    """

    status: HealthStatus
    latency_ms: float
    provider: str
    endpoint: str = ""
    last_error: str | None = None
    consecutive_failures: int = 0
    checked_at: datetime | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.latency_ms) or self.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be finite and non-negative, got {self.latency_ms!r}"
            )
        if self.consecutive_failures < 0:
            raise ValueError(
                f"consecutive_failures must be non-negative, got {self.consecutive_failures!r}"
            )

    @property
    def is_healthy(self) -> bool:
        """Return True if status is HEALTHY."""
        is_healthy: bool = self.status == HealthStatus.HEALTHY
        return is_healthy

    @property
    def is_degraded(self) -> bool:
        """Return True if status is DEGRADED."""
        is_degraded: bool = self.status == HealthStatus.DEGRADED
        return is_degraded

    @property
    def is_unhealthy(self) -> bool:
        """Return True if status is UNHEALTHY."""
        is_unhealthy: bool = self.status == HealthStatus.UNHEALTHY
        return is_unhealthy

    def to_metric_labels(self) -> dict[str, str]:
        """Convert to metric labels for Prometheus export.

        Returns:
            Dictionary with provider and status labels.

        """
        return {
            "provider": self.provider,
            "status": self.status.value.lower(),
        }

    def to_dict(self) -> dict[str, str | float | int | None]:
        """Convert to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the health check result.

        """
        return {
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "checked_at": self.checked_at.isoformat() if self.checked_at else None,
        }


@runtime_checkable
class HealthCheckPort(Protocol):
    """Port for health check operations on external APIs.

    Provides a standardized interface for checking the health of
    data source adapters before pipeline execution.

    Health check probes should be:
    - Lightweight (minimal data transfer)
    - Fast (timeout of 5s recommended)
    - Non-mutating (read-only operations)

    Implementations MUST:
    - Return HealthCheckResult with accurate latency measurement
    - Handle timeouts gracefully (return UNHEALTHY, not raise)
    - Track consecutive failures for state machine transitions

    Example:
        >>> result = await adapter.check_health()
        >>> if result.is_unhealthy:
        ...     logger.error("Provider unavailable", **result.to_dict())

    """

    @property
    def provider_name(self) -> str:
        """The unique name of the data provider (e.g., 'chembl')."""
        ...

    async def check_health(self) -> HealthCheckResult:
        """Perform a health check on the external API.

        Returns:
            HealthCheckResult with current health status and metrics.

        Note:
            This method MUST NOT raise exceptions. All errors should be
            caught and returned as UNHEALTHY status with error details.

        """
        ...


HealthStatusLiteral = Literal["healthy", "degraded", "unhealthy"]
"""Type alias for health status literal values (for JSON serialization)."""


@runtime_checkable
class HealthStatePort(Protocol):
    """Protocol for provider health state.

    Provides a read-only view of health state for monitoring/debugging.
    """

    @property
    def status(self) -> HealthStatus:
        """Current health status."""
        ...

    @property
    def consecutive_errors(self) -> int:
        """Number of consecutive errors."""
        ...


@runtime_checkable
class HealthMonitorPort(Protocol):
    """Port for centralized health monitoring across providers.

    Implements RULES.md §3.5 state machine for provider health:
    - HEALTHY: Provider operational, no errors
    - DEGRADED: 1-2 consecutive errors, timeout ×2, batch_size ÷2
    - UNHEALTHY: ≥3 errors, pipeline paused, P2 alert

    This port abstracts the health monitoring implementation, allowing
    the application layer to track health without depending on
    infrastructure details.

    """

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: LoggerPort | None = None,
    ) -> HealthStatus:
        """Update health state from HealthCheckResult.

        Records latency metrics and triggers P2 alert on UNHEALTHY status.

        Args:
            result: HealthCheckResult from adapter health check.
            logger: Optional logger for P2 alert on UNHEALTHY.

        Returns:
            Current HealthStatus after applying transitions.

        """
        ...

    def record_success(self, provider: str) -> HealthStatus:
        """Record successful operation for a provider.

        Args:
            provider: Provider name.

        Returns:
            Current HealthStatus after recording success.

        """
        ...

    def record_error(self, provider: str) -> HealthStatus:
        """Record failed operation for a provider.

        Args:
            provider: Provider name.

        Returns:
            Current HealthStatus after recording error.

        """
        ...

    def get_all_states(self) -> Mapping[str, HealthStatePort]:
        """Get all provider health states for monitoring/debugging.

        Returns:
            Mapping of provider name to HealthStatePort.

        """
        ...
