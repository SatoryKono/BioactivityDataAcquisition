"""Memory monitoring configuration object.

Defines the MemoryConfig value object for memory-aware batch processing.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "MemoryConfig",
]


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Configuration for memory-aware batch processing.

    Used by MemoryMonitor (infrastructure layer) to configure adaptive
    batch sizing based on memory pressure detection.

    Attributes:
        max_batch_memory_mb: Maximum memory per batch in MB (default: 512MB).
        memory_pressure_threshold: Threshold (0.0-1.0) for reducing batch size (default: 0.8).
        min_batch_size: Minimum batch size even under memory pressure (default: 10).
        check_interval_records: Check memory every N records (default: 100).
        enable_adaptive_sizing: Enable/disable adaptive batch sizing (default: True).

    Example:
        >>> config = MemoryConfig()
        >>> config.memory_pressure_threshold
        0.8
        >>> config.max_batch_memory_mb
        512
    """

    max_batch_memory_mb: int = 512
    memory_pressure_threshold: float = 0.8
    min_batch_size: int = 10
    check_interval_records: int = 100
    enable_adaptive_sizing: bool = True

    def __post_init__(self) -> None:
        """Validate memory-adaptive sizing limits."""
        if self.max_batch_memory_mb <= 0:
            raise ValueError("max_batch_memory_mb must be greater than 0")
        if not 0.0 < self.memory_pressure_threshold <= 1.0:
            raise ValueError(
                "memory_pressure_threshold must be in the range (0.0, 1.0]"
            )
        if self.min_batch_size <= 0:
            raise ValueError("min_batch_size must be greater than 0")
        if self.check_interval_records <= 0:
            raise ValueError("check_interval_records must be greater than 0")
