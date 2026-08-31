"""Memory monitoring configuration object.

Defines the MemoryConfig value object for memory-aware batch processing.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "MemoryConfig",
]


class MemoryConfig(BaseModel):
    """Configuration for memory-aware batch processing.

    Used by MemoryMonitor (infrastructure layer) to configure adaptive
    batch sizing based on memory pressure detection.

    Attributes:
        max_batch_memory_mb: Positive maximum memory budget per batch in MB.
            Memory-derived maximum batch calculations may still return
            min_batch_size as a forward-progress floor when records are large.
        memory_pressure_threshold: Configured pressure threshold in the range
            (0.0, 1.0]. Infrastructure treats usage equal to the threshold as
            pressure.
        min_batch_size: Positive minimum batch size even under memory pressure.
        check_interval_records: Positive interval for memory checks.
        enable_adaptive_sizing: Enable/disable adaptive batch sizing (default: True).

    Example:
        >>> config = MemoryConfig()
        >>> config.memory_pressure_threshold
        0.8
        >>> config.max_batch_memory_mb
        512
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    max_batch_memory_mb: int = Field(default=512, gt=0)
    memory_pressure_threshold: float = Field(
        default=0.8,
        gt=0.0,
        le=1.0,
        allow_inf_nan=False,
    )
    min_batch_size: int = Field(default=10, gt=0)
    check_interval_records: int = Field(default=100, gt=0)
    enable_adaptive_sizing: bool = True
