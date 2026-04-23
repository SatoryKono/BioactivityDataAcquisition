"""Memory monitoring port for adaptive batch processing.

Provides interface for memory pressure detection and adaptive batch sizing.
Implementations may use psutil, resource module, or provide estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from bioetl.domain.types import JsonDict


@dataclass(frozen=True, slots=True)
class MemoryDecisionTraceEntry:
    """Replay-visible adaptive memory sizing decision."""

    decision_index: int
    record_index: int | None
    stage: str
    old_batch_size: int
    new_batch_size: int
    adaptive_sizing_enabled: bool
    monitor_available: bool
    config_available: bool
    pressure_state: bool | None
    monitor_mode: str
    reason: str

    def to_dict(self) -> JsonDict:
        """Return a JSON-serializable trace entry."""
        return {
            "decision_index": self.decision_index,
            "record_index": self.record_index,
            "stage": self.stage,
            "old_batch_size": self.old_batch_size,
            "new_batch_size": self.new_batch_size,
            "adaptive_sizing_enabled": self.adaptive_sizing_enabled,
            "monitor_available": self.monitor_available,
            "config_available": self.config_available,
            "pressure_state": self.pressure_state,
            "monitor_mode": self.monitor_mode,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Current memory statistics (immutable value object).

    Attributes:
        used_mb: Currently used memory in MB.
        available_mb: Available memory in MB.
        total_mb: Total system memory in MB.
        percent_used: Percentage of memory used (0.0-1.0).
        process_mb: Current process memory usage in MB.

    """

    used_mb: float
    available_mb: float
    total_mb: float
    percent_used: float
    process_mb: float

    @property
    def is_under_pressure(self) -> bool:
        """Check pressure with the coarse 80% convenience threshold.

        Runtime policy should use ``is_under_pressure_at`` with
        ``MemoryConfig.memory_pressure_threshold`` instead of this helper.
        """
        return self.is_under_pressure_at(0.8)

    def is_under_pressure_at(self, threshold: float) -> bool:
        """Check if system usage is at or above a configured threshold."""
        return self.percent_used >= threshold


@runtime_checkable
class MemoryMonitorPort(Protocol):
    """Port for memory monitoring and adaptive batch sizing.

    Abstracts memory monitoring implementation to allow:
    - Real monitoring via psutil
    - Fallback monitoring via resource module
    - Conservative estimates when monitoring unavailable
    - Mock implementations for testing

    This port enables testability by allowing injection of mock
    implementations that simulate various memory pressure scenarios.
    """

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            MemoryStats with current memory usage information.

        """
        ...

    def is_under_pressure(self) -> bool:
        """Check if system is under memory pressure.

        Returns:
            True if memory usage exceeds the configured threshold.

        """
        ...

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Get recommended batch size based on memory pressure.

        Implements adaptive batch sizing:
        - If under memory pressure, reduces batch size
        - If pressure persists, reduces more aggressively
        - Never goes below configured min_batch_size
        - Gradually increases batch size when pressure is relieved

        Args:
            current_batch_size: Current batch size.

        Returns:
            Recommended batch size (may be smaller if under pressure).

        """
        ...

    def estimate_batch_memory_mb(
        self,
        record_count: int,
        avg_record_size_bytes: int = 1024,
    ) -> float:
        """Estimate memory usage for a batch.

        Args:
            record_count: Number of records in batch.
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Estimated memory usage in MB.

        """
        ...

    def calculate_max_batch_size(self, avg_record_size_bytes: int = 1024) -> int:
        """Calculate maximum batch size based on available memory.

        Args:
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Maximum recommended batch size.

        """
        ...


__all__ = ["MemoryDecisionTraceEntry", "MemoryMonitorPort", "MemoryStats"]
