# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Provider-state helpers for HealthServer."""

from __future__ import annotations

from bioetl.domain.ports import HealthMonitorPort
from bioetl.domain.types import HealthStatus, JsonDict


class HealthServerStateMixin:
    """Mixin with provider state aggregation helpers."""

    _health_monitor: HealthMonitorPort | None

    def _get_overall_status(self) -> HealthStatus:
        """Get overall health status from all providers."""
        if not self._health_monitor:
            return HealthStatus.HEALTHY
        states = self._health_monitor.get_all_states()
        if not states:
            return HealthStatus.HEALTHY
        statuses = [state.status for state in states.values()]
        if any(status == HealthStatus.UNHEALTHY for status in statuses):
            return HealthStatus.UNHEALTHY
        if any(status == HealthStatus.DEGRADED for status in statuses):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def _get_provider_statuses(
        self,
    ) -> dict[str, JsonDict]:  # Any: response payload values are heterogeneous
        """Get detailed status for all providers."""
        if not self._health_monitor:
            return {}
        states = self._health_monitor.get_all_states()
        return {
            name: {
                "status": state.status.value.lower(),
                "consecutive_errors": state.consecutive_errors,
            }
            for name, state in states.items()
        }


__all__ = ["HealthServerStateMixin"]
