"""Provider Health Monitor.

Implements RULES.md §3.5 - Centralized health state management.

Requirements:
- REQ-OBS-010: provider_health_status metric
- REQ-ERR-015: Automatic state transitions

State transitions per RULES.md §3.5:
- Healthy → Degraded: 1-2 consecutive errors
- Degraded → Unhealthy: ≥3 errors OR health_check fail
- Unhealthy → Degraded: 1 successful health_check (Recovery)
- Degraded → Healthy: 0 errors for 5 min window
"""

from __future__ import annotations

__all__ = [
    "HealthAdjustedConfig",
    "ProviderHealthMonitor",
    "ProviderHealthState",
    "ProviderHealthTracker",
]


import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http._health_monitor_models import (
    HealthAdjustedConfig,
)
from bioetl.infrastructure.adapters.http._health_monitor_support import (
    emit_health_check_observability,
    emit_provider_health_metric,
    emit_unhealthy_alert,
    get_adaptive_params_for_status,
    record_error_transition,
    record_health_check_transition,
    record_success_transition,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import HealthCheckResult, LoggerPort, MetricsPort


@dataclass
class ProviderHealthState:
    """Tracks health state for a single provider.

    Thresholds from RULES.md §3.5:
    - Degraded: 1-2 consecutive errors
    - Unhealthy: ≥3 errors
    """

    provider: str
    status: HealthStatus = HealthStatus.HEALTHY
    consecutive_errors: int = 0
    last_success: float | None = None  # monotonic time
    last_check: float | None = None  # monotonic time

    # Thresholds from RULES.md §3.5
    DEGRADED_THRESHOLD: int = 1  # 1-2 consecutive errors
    UNHEALTHY_THRESHOLD: int = 3  # ≥3 errors
    CLEAR_WINDOW_SECONDS: float = 300.0  # 5 minutes


@dataclass
class ProviderHealthMonitor:
    """Centralized health monitoring for all providers.

    Implements automatic state transitions per RULES.md §3.5:
    - Healthy → Degraded: 1-2 consecutive errors
    - Degraded → Unhealthy: ≥3 errors OR health_check fail
    - Unhealthy → Degraded: 1 successful health_check (Recovery)
    - Degraded → Healthy: 0 errors for 5 min window

    Emits metric: provider_health_status{provider} (0=Unhealthy, 1=Degraded, 2=Healthy)
    """

    metrics: MetricsPort
    _states: dict[str, ProviderHealthState] = field(default_factory=dict)

    def get_state(self, provider: str) -> ProviderHealthState:
        """Get or create health state for provider.

        Args:
            provider: Provider name (e.g., "chembl", "uniprot").

        Returns:
            ProviderHealthState for the provider.
        """
        if provider not in self._states:
            self._states[provider] = ProviderHealthState(provider=provider)
        return self._states[provider]

    def record_success(self, provider: str) -> HealthStatus:
        """Record successful operation, potentially recover from Unhealthy.

        Args:
            provider: Provider name.

        Returns:
            Current HealthStatus after recording success.
        """
        state = self.get_state(provider)
        record_success_transition(state, now=time.monotonic())
        self._emit_metric(state)
        return state.status

    def record_error(self, provider: str) -> HealthStatus:
        """Record error, potentially transition to Degraded/Unhealthy.

        Args:
            provider: Provider name.

        Returns:
            Current HealthStatus after recording error.
        """
        state = self.get_state(provider)
        record_error_transition(state)
        self._emit_metric(state)
        return state.status

    def record_health_check_result(
        self,
        provider: str,
        status: HealthStatus,
    ) -> HealthStatus:
        """Record health check result, apply transitions.

        Args:
            provider: Provider name.
            status: HealthStatus from health check probe.

        Returns:
            Current HealthStatus after applying transitions.
        """
        state = self.get_state(provider)
        record_health_check_transition(
            state,
            status=status,
            now=time.monotonic(),
        )
        self._emit_metric(state)
        return state.status

    def get_adaptive_params(self, provider: str) -> tuple[float, int]:
        """Get adaptive timeout and batch_size based on health.

        Per RULES.md §3.5:
        - Degraded: Timeout ×2, batch_size ÷2
        - Unhealthy: More aggressive throttling

        Args:
            provider: Provider name.

        Returns:
            Tuple of (timeout_multiplier, batch_size_divisor).
        """
        state = self.get_state(provider)
        return get_adaptive_params_for_status(state.status)

    def _emit_metric(self, state: ProviderHealthState) -> None:
        """Emit provider_health_status metric.

        Args:
            state: Provider health state.
        """
        emit_provider_health_metric(
            metrics=self.metrics,
            state=state,
        )

    def get_all_states(self) -> Mapping[str, ProviderHealthState]:
        """Get all provider states for monitoring/debugging.

        Returns:
            Mapping of provider name to ProviderHealthState.
        """
        return dict(self._states)

    def update_from_health_check_result(
        self,
        result: HealthCheckResult,
        logger: LoggerPort | None = None,
    ) -> HealthStatus:
        """Update state from HealthCheckResult and emit metrics.

        This method provides enhanced integration with HealthCheckResult,
        recording latency metrics and logging P2 alerts for UNHEALTHY status.

        Args:
            result: HealthCheckResult from adapter health check.
            logger: Optional logger for P2 alert on UNHEALTHY.

        Returns:
            Current HealthStatus after applying transitions.

        """
        emit_health_check_observability(
            metrics=self.metrics,
            result=result,
        )
        new_status = self.record_health_check_result(result.provider, result.status)
        emit_unhealthy_alert(
            logger=logger,
            result=result,
            new_status=new_status,
        )
        return new_status

    def get_adjusted_config(self, provider: str) -> HealthAdjustedConfig:
        """Get adjusted client configuration based on health status.

        Per RULES.md §3.5:
        - HEALTHY: Normal operation (timeout ×1, batch_size ÷1)
        - DEGRADED: Timeout ×2, batch_size ÷2
        - UNHEALTHY: Timeout ×4, batch_size ÷4 (aggressive throttling)

        Args:
            provider: Provider name.

        Returns:
            HealthAdjustedConfig with multipliers for timeout and batch_size.

        Example:
            >>> config = monitor.get_adjusted_config("chembl")
            >>> effective_timeout = 30.0 * config.timeout_multiplier  # 60.0 if DEGRADED
            >>> effective_batch_size = config.apply_batch_size(1000, minimum=100)

        """
        timeout_mult, batch_div = self.get_adaptive_params(provider)
        state = self.get_state(provider)
        return HealthAdjustedConfig(
            timeout_multiplier=timeout_mult,
            batch_size_divisor=batch_div,
            status=state.status,
        )


def __getattr__(name: str) -> object:
    """Resolve compatibility re-exports without eager tracker imports."""
    if name != "ProviderHealthTracker":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from bioetl.infrastructure.adapters.http.health_tracker import ProviderHealthTracker

    globals()[name] = ProviderHealthTracker
    return ProviderHealthTracker
