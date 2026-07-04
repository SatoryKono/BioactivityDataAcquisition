"""Provider-level health tracking facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http._health_monitor_models import (
    HealthAdjustedConfig,
    ProviderHealthMonitorProtocol,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort


@dataclass
class ProviderHealthTracker:
    """Per-provider health tracker wrapper around `ProviderHealthMonitor`."""

    provider: str
    monitor: ProviderHealthMonitorProtocol
    logger: LoggerPort | None = None

    _base_timeout: float = 30.0
    _base_batch_size: int = 1000

    def update(self, result: HealthCheckResult) -> HealthStatus:
        """Update health state from HealthCheckResult.

        Args:
            result: Result object from the most recent health check,
                containing status and optional diagnostic details.

        Returns:
            Updated HealthStatus after applying the result.

        """
        return self.monitor.update_from_health_check_result(result, self.logger)

    def record_success(self) -> HealthStatus:
        """Record successful operation."""
        return self.monitor.record_success(self.provider)

    def record_error(self) -> HealthStatus:
        """Record failed operation."""
        return self.monitor.record_error(self.provider)

    def get_adjusted_config(self) -> HealthAdjustedConfig:
        """Get adjusted client configuration."""
        return self.monitor.get_adjusted_config(self.provider)

    @property
    def status(self) -> HealthStatus:
        """Get current health status."""
        return self.monitor.get_state(self.provider).status

    @property
    def consecutive_failures(self) -> int:
        """Get consecutive failure count."""
        return int(self.monitor.get_state(self.provider).consecutive_errors)

    def is_healthy(self) -> bool:
        """Check whether provider is healthy."""
        return bool(self.status == HealthStatus.HEALTHY)

    def is_unhealthy(self) -> bool:
        """Check whether provider is unhealthy."""
        return bool(self.status == HealthStatus.UNHEALTHY)

    def should_pause_pipeline(self) -> bool:
        """Check whether pipeline should be paused due to provider health."""
        return self.is_unhealthy()


__all__ = ["ProviderHealthTracker"]
