"""Pure adaptive batch memory decision helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.ports import MemoryMonitorPort

def config_budget_exceeded(
    memory_config: MemoryConfig | None,
    current_size: int,
) -> bool:
    """Return whether current size exceeds the configured memory budget."""
    if not memory_config:
        return False
    records_per_mb = 1000
    max_records = memory_config.max_batch_memory_mb * records_per_mb
    return current_size > max_records

def estimate_from_config(
    memory_config: MemoryConfig | None,
    current_size: int,
) -> int:
    """Estimate batch size without memory monitoring."""
    if not memory_config:
        return current_size

    records_per_mb = 1000
    max_records = memory_config.max_batch_memory_mb * records_per_mb

    if config_budget_exceeded(memory_config, current_size):
        estimated_size: int = max(max_records, memory_config.min_batch_size)
        return estimated_size

    return current_size

def decision_reason(*, old_size: int, new_size: int) -> str:
    """Return a bounded reason for a monitor-sourced decision."""
    if new_size < old_size:
        return "monitor_recommended_reduction"
    if new_size > old_size:
        return "monitor_recommended_recovery"
    return "monitor_recommended_no_change"

def decision_status(
    *,
    old_size: int,
    new_size: int,
    pressure_state: bool | None,
) -> str:
    """Return a bounded status for one adaptive-memory decision."""
    if new_size < old_size:
        return "reduced"
    if new_size > old_size:
        return "recovered"
    if pressure_state is True:
        return "pressure"
    if pressure_state is False:
        return "stable"
    return "disabled"

def monitor_mode(monitor: MemoryMonitorPort) -> str:
    """Return the monitor mode when exposed by the monitor implementation."""
    getter = getattr(monitor, "get_monitor_mode", None)
    if callable(getter):
        value = getter()
        if isinstance(value, str):
            return value
    return "unknown"

def monitor_pressure_state(monitor: MemoryMonitorPort) -> bool | None:
    """Return the latest monitor pressure state when exposed."""
    getter = getattr(monitor, "get_last_pressure_state", None)
    if callable(getter):
        value = getter()
        if isinstance(value, bool):
            return value
    return None

__all__ = [
    "config_budget_exceeded",
    "decision_reason",
    "decision_status",
    "estimate_from_config",
    "monitor_mode",
    "monitor_pressure_state",
]
