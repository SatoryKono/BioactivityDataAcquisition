"""Memory management for adaptive batch sizing.

Extracted from BatchExecutor to reduce class size. Handles memory pressure
detection, batch size adjustment, and recovery after processing.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.ports import LoggerPort, MemoryMonitorPort


class BatchMemoryManagerService:
    """Manages adaptive batch sizing based on memory pressure."""

    def __init__(
        self,
        initial_batch_size: int,
        *,
        memory_monitor: MemoryMonitorPort | None = None,
        memory_config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        self._memory_monitor = memory_monitor
        self._memory_config = memory_config
        self._initial_batch_size = initial_batch_size
        self._logger = logger
        self.enabled = memory_monitor is not None or (
            memory_config is not None and memory_config.enable_adaptive_sizing
        )
        self.batch_size_reductions = 0
        self.min_batch_size_used = initial_batch_size

    def get_check_interval(self) -> int:
        """Get interval for memory pressure checks.

        Returns:
            Number of records between memory monitor checks (defaults to 100).
        """
        if self._memory_config:
            return self._memory_config.check_interval_records
        return 100

    def check_pressure(
        self, current_size: int, check_interval: int, records_fetched: int
    ) -> int:
        """Check memory pressure and adjust batch size if needed.

        Args:
            current_size: Current batch size.
            check_interval: Number of records between memory checks.
            records_fetched: Total records fetched so far.

        Returns:
            Recommended batch size (may be smaller than current_size).
        """
        if not self.enabled:
            return current_size
        if records_fetched % check_interval != 0:
            return current_size
        return self._adjust(current_size)

    def maybe_recover(self, current_size: int) -> int:
        """Try to recover batch size after processing.

        Args:
            current_size: Current batch size.

        Returns:
            Recommended batch size (may be larger than current_size).
        """
        if not self.enabled:
            return current_size
        return self._try_recover(current_size)

    def _adjust(self, current_size: int) -> int:
        """Adjust batch size based on memory pressure."""
        if self._memory_monitor:
            new_size = self._memory_monitor.get_recommended_batch_size(current_size)
        elif self._memory_config:
            new_size = self._estimate_from_config(current_size)
        else:
            return current_size

        if new_size < current_size:
            self.batch_size_reductions += 1
            self.min_batch_size_used = min(self.min_batch_size_used, new_size)
            if self._logger:
                self._logger.info(
                    "Reduced batch size due to memory pressure",
                    old_size=current_size,
                    new_size=new_size,
                    total_reductions=self.batch_size_reductions,
                )

        return new_size

    def _estimate_from_config(self, current_size: int) -> int:
        """Estimate batch size without memory monitoring."""
        if not self._memory_config:
            return current_size

        records_per_mb = 1000
        max_records = self._memory_config.max_batch_memory_mb * records_per_mb

        if current_size > max_records:
            return max(max_records, self._memory_config.min_batch_size)

        return current_size

    def _try_recover(self, current_size: int) -> int:
        """Try to recover batch size after pressure is relieved."""
        if self._memory_monitor:
            return self._memory_monitor.get_recommended_batch_size(current_size)

        if current_size < self._initial_batch_size:
            recovery_size = min(
                int(current_size * 1.1),
                self._initial_batch_size,
            )
            return recovery_size

        return current_size



__all__ = ["BatchMemoryManagerService"]
