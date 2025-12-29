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
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.domain.ports.health_check import HealthCheckResult


@dataclass(frozen=True, slots=True)
class AdjustedClientConfig:
    """Configuration adjusted based on provider health status.

    Per RULES.md §3.5:
    - HEALTHY: Normal operation (multiplier=1.0, divisor=1)
    - DEGRADED: Timeout ×2, batch_size ÷2
    - UNHEALTHY: Timeout ×4, batch_size ÷4 (aggressive throttling)

    Attributes:
        timeout_multiplier: Factor to multiply base timeout by.
        batch_size_divisor: Factor to divide base batch_size by.
        status: Current health status.

    Example:
        >>> config = tracker.get_adjusted_config()
        >>> effective_timeout = base_timeout * config.timeout_multiplier
        >>> effective_batch_size = base_batch_size // config.batch_size_divisor

    """

    timeout_multiplier: float
    batch_size_divisor: int
    status: HealthStatus

    def apply_timeout(self, base_timeout: float) -> float:
        """Apply timeout multiplier to base timeout.

        Args:
            base_timeout: Base timeout in seconds.

        Returns:
            Adjusted timeout value.

        """
        return base_timeout * self.timeout_multiplier

    def apply_batch_size(self, base_batch_size: int, minimum: int = 1) -> int:
        """Apply batch size divisor to base batch size.

        Args:
            base_batch_size: Base batch size.
            minimum: Minimum allowed batch size (default: 1).

        Returns:
            Adjusted batch size, at least `minimum`.

        """
        return max(minimum, base_batch_size // self.batch_size_divisor)


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
            state.status == HealthStatus.DEGRADED and self._check_clear_window(state)
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
        self.metrics.set_gauge(
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
        # Record health check latency metric
        self.metrics.observe_histogram(
            "health_check_latency_ms",
            result.latency_ms,
            labels={"provider": result.provider},
        )

        # Record health check result metric
        self.metrics.set_gauge(
            "provider_health_status",
            float(result.status.to_metric_value()),
            labels={"provider": result.provider},
        )

        # Apply state transitions
        new_status = self.record_health_check_result(result.provider, result.status)

        # P2 Alert for UNHEALTHY status
        if new_status == HealthStatus.UNHEALTHY and logger:
            logger.error(
                "provider_unhealthy_alert",
                provider=result.provider,
                alert_priority="P2",
                status=new_status.value,
                consecutive_failures=result.consecutive_failures,
                last_error=result.last_error,
                endpoint=result.endpoint,
                latency_ms=result.latency_ms,
            )

        return new_status

    def get_adjusted_config(self, provider: str) -> AdjustedClientConfig:
        """Get adjusted client configuration based on health status.

        Per RULES.md §3.5:
        - HEALTHY: Normal operation (timeout ×1, batch_size ÷1)
        - DEGRADED: Timeout ×2, batch_size ÷2
        - UNHEALTHY: Timeout ×4, batch_size ÷4 (aggressive throttling)

        Args:
            provider: Provider name.

        Returns:
            AdjustedClientConfig with multipliers for timeout and batch_size.

        Example:
            >>> config = monitor.get_adjusted_config("chembl")
            >>> effective_timeout = 30.0 * config.timeout_multiplier  # 60.0 if DEGRADED
            >>> effective_batch_size = config.apply_batch_size(1000, minimum=100)

        """
        timeout_mult, batch_div = self.get_adaptive_params(provider)
        state = self.get_state(provider)
        return AdjustedClientConfig(
            timeout_multiplier=timeout_mult,
            batch_size_divisor=batch_div,
            status=state.status,
        )


@dataclass
class ProviderHealthTracker:
    """Per-provider health tracker with state machine management.

    Wraps ProviderHealthMonitor for single-provider usage, providing
    a simpler interface for adapters to track and respond to health changes.

    Implements RULES.md §3.5 state machine:
    - HEALTHY: Provider operational, no errors
    - DEGRADED: 1-2 consecutive errors, timeout ×2, batch_size ÷2
    - UNHEALTHY: ≥3 errors, pipeline paused, P2 alert

    Attributes:
        provider: Provider name (e.g., 'chembl', 'pubchem').
        monitor: Centralized ProviderHealthMonitor instance.
        logger: Optional logger for alerts.

    Example:
        >>> tracker = ProviderHealthTracker("chembl", monitor, logger)
        >>> tracker.update(health_result)
        >>> config = tracker.get_adjusted_config()
        >>> if config.status == HealthStatus.UNHEALTHY:
        ...     raise CriticalError("Provider unavailable")

    """

    provider: str
    monitor: ProviderHealthMonitor
    logger: LoggerPort | None = None

    # Base configuration defaults
    _base_timeout: float = 30.0
    _base_batch_size: int = 1000

    def update(self, result: HealthCheckResult) -> HealthStatus:
        """Update health state from HealthCheckResult.

        Args:
            result: HealthCheckResult from health check probe.

        Returns:
            Current HealthStatus after update.

        """
        return self.monitor.update_from_health_check_result(result, self.logger)

    def record_success(self) -> HealthStatus:
        """Record successful operation.

        Returns:
            Current HealthStatus after recording success.

        """
        return self.monitor.record_success(self.provider)

    def record_error(self) -> HealthStatus:
        """Record failed operation.

        Returns:
            Current HealthStatus after recording error.

        """
        return self.monitor.record_error(self.provider)

    def get_adjusted_config(self) -> AdjustedClientConfig:
        """Get adjusted client configuration.

        Returns:
            AdjustedClientConfig with timeout/batch_size adjustments.

        """
        return self.monitor.get_adjusted_config(self.provider)

    @property
    def status(self) -> HealthStatus:
        """Get current health status.

        Returns:
            Current HealthStatus for this provider.

        """
        return self.monitor.get_state(self.provider).status

    @property
    def consecutive_failures(self) -> int:
        """Get consecutive failure count.

        Returns:
            Number of consecutive errors.

        """
        return self.monitor.get_state(self.provider).consecutive_errors

    def is_healthy(self) -> bool:
        """Check if provider is healthy.

        Returns:
            True if status is HEALTHY.

        """
        return self.status == HealthStatus.HEALTHY

    def is_unhealthy(self) -> bool:
        """Check if provider is unhealthy.

        Returns:
            True if status is UNHEALTHY.

        """
        return self.status == HealthStatus.UNHEALTHY

    def should_pause_pipeline(self) -> bool:
        """Check if pipeline should be paused due to health.

        Per RULES.md §3.5: UNHEALTHY status pauses pipeline.

        Returns:
            True if pipeline should be paused.

        """
        return self.is_unhealthy()
