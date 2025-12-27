"""Memory management for batch processing.

Provides memory pressure detection and adaptive batch sizing
to prevent OOM errors when processing large datasets.
"""

from __future__ import annotations

import gc
import sys
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class MemoryPressure(Enum):
    """Memory pressure levels for adaptive batch sizing."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Configuration for memory management.

    Attributes:
        max_batch_memory_mb: Maximum memory for batch processing in MB.
        pressure_threshold_medium: Memory usage ratio to trigger medium pressure (0.0-1.0).
        pressure_threshold_high: Memory usage ratio to trigger high pressure (0.0-1.0).
        pressure_threshold_critical: Memory usage ratio to trigger critical pressure (0.0-1.0).
        min_batch_size: Minimum batch size to maintain under pressure.
        batch_reduction_factor: Factor to reduce batch size under high pressure (0.0-1.0).
        gc_on_high_pressure: Whether to run gc.collect() on high pressure.
        enabled: Whether memory management is enabled.
    """

    max_batch_memory_mb: int = 512
    pressure_threshold_medium: float = 0.6
    pressure_threshold_high: float = 0.75
    pressure_threshold_critical: float = 0.9
    min_batch_size: int = 10
    batch_reduction_factor: float = 0.5
    gc_on_high_pressure: bool = True
    enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration on creation."""
        if self.max_batch_memory_mb <= 0:
            raise ValueError(
                f"max_batch_memory_mb must be positive, got {self.max_batch_memory_mb}"
            )
        if not 0.0 < self.pressure_threshold_medium < 1.0:
            raise ValueError(
                f"pressure_threshold_medium must be in (0, 1), got {self.pressure_threshold_medium}"
            )
        if not 0.0 < self.pressure_threshold_high < 1.0:
            raise ValueError(
                f"pressure_threshold_high must be in (0, 1), got {self.pressure_threshold_high}"
            )
        if not 0.0 < self.pressure_threshold_critical < 1.0:
            raise ValueError(
                f"pressure_threshold_critical must be in (0, 1), got {self.pressure_threshold_critical}"
            )
        if not (
            self.pressure_threshold_medium
            < self.pressure_threshold_high
            < self.pressure_threshold_critical
        ):
            raise ValueError(
                "Thresholds must be ordered: medium < high < critical"
            )
        if self.min_batch_size <= 0:
            raise ValueError(
                f"min_batch_size must be positive, got {self.min_batch_size}"
            )
        if not 0.0 < self.batch_reduction_factor < 1.0:
            raise ValueError(
                f"batch_reduction_factor must be in (0, 1), got {self.batch_reduction_factor}"
            )


@dataclass(frozen=True, slots=True)
class MemoryStats:
    """Current memory statistics.

    Attributes:
        used_mb: Memory used in megabytes.
        limit_mb: Memory limit in megabytes (if available).
        usage_ratio: Memory usage ratio (0.0-1.0).
        pressure: Current memory pressure level.
    """

    used_mb: float
    limit_mb: float
    usage_ratio: float
    pressure: MemoryPressure


class MemoryManager:
    """Manages memory for batch processing with adaptive sizing.

    Uses Python's built-in resource module (Unix) or sys.getsizeof
    for memory estimation. Provides memory pressure detection and
    batch size recommendations.
    """

    def __init__(
        self,
        config: MemoryConfig | None = None,
        logger: LoggerPort | None = None,
    ) -> None:
        """Initialize memory manager.

        Args:
            config: Memory configuration. Uses defaults if None.
            logger: Optional logger for memory warnings.
        """
        self._config = config or MemoryConfig()
        self._logger = logger
        self._base_batch_size: int | None = None
        self._current_batch_size: int | None = None
        self._last_pressure = MemoryPressure.LOW
        self._consecutive_high_pressure = 0

    @property
    def config(self) -> MemoryConfig:
        """Get memory configuration."""
        return self._config

    @property
    def is_enabled(self) -> bool:
        """Check if memory management is enabled."""
        return self._config.enabled

    def set_base_batch_size(self, batch_size: int) -> None:
        """Set the base batch size for adaptive sizing.

        Args:
            batch_size: Original configured batch size.
        """
        self._base_batch_size = batch_size
        self._current_batch_size = batch_size

    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            MemoryStats with current memory usage and pressure level.
        """
        used_mb = self._get_process_memory_mb()
        limit_mb = float(self._config.max_batch_memory_mb)

        usage_ratio = min(used_mb / limit_mb, 1.0) if limit_mb > 0 else 0.0
        pressure = self._calculate_pressure(usage_ratio)

        return MemoryStats(
            used_mb=used_mb,
            limit_mb=limit_mb,
            usage_ratio=usage_ratio,
            pressure=pressure,
        )

    def _calculate_pressure(self, usage_ratio: float) -> MemoryPressure:
        """Calculate memory pressure level from usage ratio.

        Args:
            usage_ratio: Current memory usage ratio (0.0-1.0).

        Returns:
            Memory pressure level.
        """
        if usage_ratio >= self._config.pressure_threshold_critical:
            return MemoryPressure.CRITICAL
        if usage_ratio >= self._config.pressure_threshold_high:
            return MemoryPressure.HIGH
        if usage_ratio >= self._config.pressure_threshold_medium:
            return MemoryPressure.MEDIUM
        return MemoryPressure.LOW

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Get recommended batch size based on memory pressure.

        Args:
            current_batch_size: Current batch size.

        Returns:
            Recommended batch size (may be reduced under pressure).
        """
        if not self._config.enabled:
            return current_batch_size

        if self._base_batch_size is None:
            self._base_batch_size = current_batch_size
            self._current_batch_size = current_batch_size

        stats = self.get_current_stats()
        self._last_pressure = stats.pressure

        if stats.pressure == MemoryPressure.CRITICAL:
            self._consecutive_high_pressure += 1
            # Aggressive reduction under critical pressure
            new_size = max(
                self._config.min_batch_size,
                int(current_batch_size * self._config.batch_reduction_factor * 0.5),
            )
            self._trigger_gc_if_needed()
            self._log_pressure_adjustment(stats, current_batch_size, new_size)
            self._current_batch_size = new_size
            return new_size

        if stats.pressure == MemoryPressure.HIGH:
            self._consecutive_high_pressure += 1
            # Reduce batch size under high pressure
            new_size = max(
                self._config.min_batch_size,
                int(current_batch_size * self._config.batch_reduction_factor),
            )
            self._trigger_gc_if_needed()
            self._log_pressure_adjustment(stats, current_batch_size, new_size)
            self._current_batch_size = new_size
            return new_size

        if stats.pressure == MemoryPressure.MEDIUM:
            # Maintain current size under medium pressure
            self._consecutive_high_pressure = 0
            return current_batch_size

        # Low pressure - gradually recover batch size
        self._consecutive_high_pressure = 0
        if current_batch_size < self._base_batch_size:
            # Gradual increase (25% per check)
            new_size = min(
                self._base_batch_size,
                int(current_batch_size * 1.25),
            )
            if new_size != current_batch_size:
                self._log_pressure_adjustment(stats, current_batch_size, new_size)
            self._current_batch_size = new_size
            return new_size

        self._current_batch_size = current_batch_size
        return current_batch_size

    def should_process_in_chunks(self, batch_size: int) -> bool:
        """Check if batch should be processed in smaller chunks.

        Args:
            batch_size: Size of the batch to process.

        Returns:
            True if batch should be chunked due to memory pressure.
        """
        if not self._config.enabled:
            return False

        stats = self.get_current_stats()
        return stats.pressure in (MemoryPressure.HIGH, MemoryPressure.CRITICAL)

    def get_chunk_size(self, batch_size: int) -> int:
        """Get recommended chunk size for streaming processing.

        Args:
            batch_size: Total batch size.

        Returns:
            Recommended chunk size for memory-efficient processing.
        """
        if not self._config.enabled:
            return batch_size

        stats = self.get_current_stats()

        if stats.pressure == MemoryPressure.CRITICAL:
            return max(self._config.min_batch_size, batch_size // 8)
        if stats.pressure == MemoryPressure.HIGH:
            return max(self._config.min_batch_size, batch_size // 4)
        if stats.pressure == MemoryPressure.MEDIUM:
            return max(self._config.min_batch_size, batch_size // 2)

        return batch_size

    def _get_process_memory_mb(self) -> float:
        """Get current process memory usage in MB.

        Uses resource module on Unix, falls back to object size estimation.

        Returns:
            Memory usage in megabytes.
        """
        try:
            import resource

            # Get max resident set size (in kilobytes on Linux)
            rusage = resource.getrusage(resource.RUSAGE_SELF)
            return rusage.ru_maxrss / 1024.0
        except (ImportError, AttributeError):
            # Fallback: estimate using gc objects
            gc.collect()
            total_size = 0
            for obj in gc.get_objects():
                try:
                    total_size += sys.getsizeof(obj)
                except (TypeError, AttributeError):
                    pass
            return total_size / (1024 * 1024)

    def _trigger_gc_if_needed(self) -> None:
        """Trigger garbage collection if configured and under pressure."""
        if self._config.gc_on_high_pressure:
            collected = gc.collect()
            if self._logger and collected > 0:
                self._logger.debug(
                    "Memory pressure triggered GC",
                    objects_collected=collected,
                )

    def _log_pressure_adjustment(
        self,
        stats: MemoryStats,
        old_size: int,
        new_size: int,
    ) -> None:
        """Log batch size adjustment due to memory pressure.

        Args:
            stats: Current memory statistics.
            old_size: Previous batch size.
            new_size: New batch size.
        """
        if not self._logger:
            return

        if new_size < old_size:
            self._logger.warning(
                "Reducing batch size due to memory pressure",
                memory_pressure=stats.pressure.value,
                memory_used_mb=round(stats.used_mb, 2),
                memory_limit_mb=round(stats.limit_mb, 2),
                usage_ratio=round(stats.usage_ratio, 3),
                old_batch_size=old_size,
                new_batch_size=new_size,
                consecutive_high_pressure=self._consecutive_high_pressure,
            )
        else:
            self._logger.info(
                "Recovering batch size as memory pressure decreases",
                memory_pressure=stats.pressure.value,
                usage_ratio=round(stats.usage_ratio, 3),
                old_batch_size=old_size,
                new_batch_size=new_size,
            )

    def estimate_record_memory(self, records: list[dict[str, Any]]) -> float:
        """Estimate memory usage of records in MB.

        Args:
            records: List of records to estimate.

        Returns:
            Estimated memory usage in megabytes.
        """
        if not records:
            return 0.0

        # Sample-based estimation for large batches
        sample_size = min(len(records), 100)
        sample = records[:sample_size]

        total_size = 0
        for record in sample:
            try:
                total_size += sys.getsizeof(record)
                for key, value in record.items():
                    total_size += sys.getsizeof(key) + sys.getsizeof(value)
            except (TypeError, AttributeError):
                total_size += 1024  # Default estimate per record

        avg_size = total_size / sample_size if sample_size > 0 else 1024
        return (avg_size * len(records)) / (1024 * 1024)
