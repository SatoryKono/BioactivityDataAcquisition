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

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


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
        state.consecutive_errors = 0

        # Check if 5 min window passed BEFORE updating last_success
        # This allows DEGRADED → HEALTHY transition if enough time has passed
        should_recover_to_healthy = (
            state.status == HealthStatus.DEGRADED
            and self._check_clear_window(state)
        )

        state.last_success = time.monotonic()

        # Recovery: Unhealthy → Degraded after 1 success
        if state.status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.DEGRADED
        elif should_recover_to_healthy:
            state.status = HealthStatus.HEALTHY

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
        state.consecutive_errors += 1

        if state.consecutive_errors >= ProviderHealthState.UNHEALTHY_THRESHOLD:
            state.status = HealthStatus.UNHEALTHY
        elif state.consecutive_errors >= ProviderHealthState.DEGRADED_THRESHOLD:
            state.status = HealthStatus.DEGRADED

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
        state.last_check = time.monotonic()

        if status == HealthStatus.UNHEALTHY:
            state.status = HealthStatus.UNHEALTHY
            state.consecutive_errors = ProviderHealthState.UNHEALTHY_THRESHOLD
        elif status == HealthStatus.HEALTHY:
            # Recovery path
            if state.status == HealthStatus.UNHEALTHY:
                state.status = HealthStatus.DEGRADED
            elif state.status == HealthStatus.DEGRADED:
                state.status = HealthStatus.HEALTHY
            state.consecutive_errors = 0
            state.last_success = time.monotonic()
        # DEGRADED status from probe: maintain current state

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

        if state.status == HealthStatus.UNHEALTHY:
            return (4.0, 4)  # Aggressive throttling
        if state.status == HealthStatus.DEGRADED:
            return (2.0, 2)  # Timeout ×2, batch_size ÷2
        return (1.0, 1)  # Normal operation

    def _check_clear_window(self, state: ProviderHealthState) -> bool:
        """Check if 5 min window has passed with no errors.

        Args:
            state: Provider health state.

        Returns:
            True if window passed and can transition to Healthy.
        """
        if state.last_success is None:
            return False
        elapsed = time.monotonic() - state.last_success
        return elapsed >= ProviderHealthState.CLEAR_WINDOW_SECONDS

    def _emit_metric(self, state: ProviderHealthState) -> None:
        """Emit provider_health_status metric.

        Args:
            state: Provider health state.
        """
        value = state.status.to_metric_value()  # 0, 1, or 2
        self.metrics.gauge(
            "provider_health_status",
            value,
            labels={"provider": state.provider},
        )

    def get_all_states(self) -> dict[str, ProviderHealthState]:
        """Get all provider states for monitoring/debugging.

        Returns:
            Dictionary of provider name to ProviderHealthState.
        """
        return dict(self._states)
