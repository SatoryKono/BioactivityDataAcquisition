"""Shared health-monitor contracts used by HTTP adapter health helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort


@dataclass(frozen=True, slots=True)
class HealthAdjustedConfig:
    """Configuration adjusted based on provider health status."""

    timeout_multiplier: float
    batch_size_divisor: int
    status: HealthStatus

    def apply_timeout(self, base_timeout: float) -> float:
        """Apply timeout multiplier to one base timeout."""
        return base_timeout * self.timeout_multiplier

    def apply_batch_size(self, base_batch_size: int, minimum: int = 1) -> int:
        """Apply batch size divisor to one base batch size."""
        return max(minimum, base_batch_size // self.batch_size_divisor)


class ProviderHealthStateView(Protocol):
    """Read-only health-state shape required by tracker wrappers."""

    status: HealthStatus
    consecutive_errors: int


class ProviderHealthMonitorProtocol(Protocol):
    """Structural protocol for per-provider health monitors."""

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: LoggerPort | None = None,
    ) -> HealthStatus: ...

    def record_success(self, provider: str) -> HealthStatus: ...

    def record_error(self, provider: str) -> HealthStatus: ...

    def get_adjusted_config(self, provider: str) -> HealthAdjustedConfig: ...

    def get_state(self, provider: str) -> ProviderHealthStateView: ...


__all__ = [
    "HealthAdjustedConfig",
    "ProviderHealthMonitorProtocol",
    "ProviderHealthStateView",
]
