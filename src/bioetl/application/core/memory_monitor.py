"""Memory monitoring for adaptive batch processing.

Provides memory pressure detection and adaptive batch size recommendations.
Uses psutil if available, falls back to resource module on Unix or estimates on Windows.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    """Configuration for memory-aware batch processing.

    Attributes:
        max_batch_memory_mb: Maximum memory per batch in MB (default: 512MB).
        memory_pressure_threshold: Threshold (0.0-1.0) for reducing batch size (default: 0.8).
        min_batch_size: Minimum batch size even under memory pressure (default: 10).
        check_interval_records: Check memory every N records (default: 100).
        enable_adaptive_sizing: Enable/disable adaptive batch sizing (default: True).

    """

    max_batch_memory_mb: int = 512
    memory_pressure_threshold: float = 0.8
    min_batch_size: int = 10
    check_interval_records: int = 100
    enable_adaptive_sizing: bool = True


@dataclass(slots=True)
class MemoryStats:
    """Current memory statistics.

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
        """Check if system is under memory pressure (>80% used)."""
        return self.percent_used > 0.8


@dataclass
class MemoryMonitor:
    """Monitor memory usage and provide adaptive batch size recommendations.

    This class tracks memory consumption during batch processing and
    automatically recommends batch size reductions when memory pressure
    is detected, preventing OOM errors during large dataset processing.

    Example:
        >>> monitor = MemoryMonitor(config=MemoryConfig(), logger=logger)
        >>> batch_size = 1000
        >>> for chunk in data_source:
        ...     batch_size = monitor.get_recommended_batch_size(batch_size)
        ...     # Process with adjusted batch size

    """

    config: MemoryConfig
    logger: LoggerPort | None = None
    _psutil_available: bool = field(default=False, init=False)
    _last_batch_size: int = field(default=100, init=False)
    _consecutive_pressure_count: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        """Initialize and detect available memory monitoring backend."""
        self._psutil_available = self._check_psutil()

    def _check_psutil(self) -> bool:
        """Check if psutil is available for memory monitoring."""
        try:
            import psutil  # noqa: F401  # type: ignore[import-untyped]

            return True
        except ImportError:
            if self.logger:
                self.logger.debug(
                    "psutil not available, using fallback memory monitoring"
                )
            return False

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics.

        Returns:
            MemoryStats with current memory usage information.

        """
        if self._psutil_available:
            return self._get_stats_psutil()
        return self._get_stats_fallback()

    def _get_stats_psutil(self) -> MemoryStats:
        """Get memory stats using psutil."""
        import psutil

        vm = psutil.virtual_memory()
        process = psutil.Process()
        process_memory = process.memory_info()

        return MemoryStats(
            used_mb=vm.used / (1024 * 1024),
            available_mb=vm.available / (1024 * 1024),
            total_mb=vm.total / (1024 * 1024),
            percent_used=vm.percent / 100.0,
            process_mb=process_memory.rss / (1024 * 1024),
        )

    def _get_stats_fallback(self) -> MemoryStats:
        """Get memory stats using fallback methods."""
        if sys.platform != "win32":
            return self._get_stats_resource()
        return self._get_stats_estimate()

    def _get_stats_resource(self) -> MemoryStats:
        """Get memory stats using resource module (Unix only)."""
        import resource

        # Get process memory usage (Unix-only attributes)
        rusage = resource.getrusage(resource.RUSAGE_SELF)  # type: ignore[attr-defined]
        process_mb = rusage.ru_maxrss / 1024  # Convert KB to MB on Linux

        # Try to read system memory from /proc/meminfo
        try:
            with Path("/proc/meminfo").open() as f:
                meminfo = {}
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].rstrip(":")
                        value = int(parts[1])  # in KB
                        meminfo[key] = value

                total_mb = meminfo.get("MemTotal", 0) / 1024
                available_mb = meminfo.get("MemAvailable", 0) / 1024
                used_mb = total_mb - available_mb
                percent_used = used_mb / total_mb if total_mb > 0 else 0.5

                return MemoryStats(
                    used_mb=used_mb,
                    available_mb=available_mb,
                    total_mb=total_mb,
                    percent_used=percent_used,
                    process_mb=process_mb,
                )
        except (OSError, KeyError):
            return self._get_stats_estimate()

    def _get_stats_estimate(self) -> MemoryStats:
        """Provide conservative estimates when actual stats unavailable."""
        # Conservative estimate: assume 50% memory used
        # This is safer than assuming low usage
        return MemoryStats(
            used_mb=4096.0,  # Assume 4GB used
            available_mb=4096.0,  # Assume 4GB available
            total_mb=8192.0,  # Assume 8GB total
            percent_used=0.5,
            process_mb=256.0,  # Assume 256MB process
        )

    def is_under_pressure(self) -> bool:
        """Check if system is under memory pressure.

        Returns:
            True if memory usage exceeds the configured threshold.

        """
        if not self.config.enable_adaptive_sizing:
            return False

        stats = self.get_memory_stats()
        return stats.percent_used >= self.config.memory_pressure_threshold

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Get recommended batch size based on memory pressure.

        Implements adaptive batch sizing:
        - If under memory pressure, reduces batch size by 50%
        - If pressure persists for 3+ checks, reduces more aggressively
        - Never goes below min_batch_size
        - Gradually increases batch size when pressure is relieved

        Args:
            current_batch_size: Current batch size.

        Returns:
            Recommended batch size (may be smaller if under pressure).

        """
        if not self.config.enable_adaptive_sizing:
            return current_batch_size

        stats = self.get_memory_stats()
        is_pressure = stats.percent_used >= self.config.memory_pressure_threshold

        if is_pressure:
            self._consecutive_pressure_count += 1
            reduction_factor = self._get_reduction_factor()
            new_size = max(
                int(current_batch_size * reduction_factor),
                self.config.min_batch_size,
            )

            if self.logger and new_size < current_batch_size:
                self.logger.warning(
                    "Memory pressure detected, reducing batch size",
                    current_batch_size=current_batch_size,
                    new_batch_size=new_size,
                    memory_percent_used=round(stats.percent_used * 100, 1),
                    consecutive_pressure_count=self._consecutive_pressure_count,
                )

            self._last_batch_size = new_size
            return new_size

        # Pressure relieved - consider gradual recovery
        self._consecutive_pressure_count = 0

        # If we previously reduced, try to recover gradually
        if current_batch_size < self._last_batch_size:
            recovery_size = min(
                int(current_batch_size * 1.25),  # Increase by 25%
                self._last_batch_size,
            )
            if self.logger:
                self.logger.debug(
                    "Memory pressure relieved, increasing batch size",
                    current_batch_size=current_batch_size,
                    new_batch_size=recovery_size,
                    memory_percent_used=round(stats.percent_used * 100, 1),
                )
            return recovery_size

        self._last_batch_size = current_batch_size
        return current_batch_size

    def _get_reduction_factor(self) -> float:
        """Get batch size reduction factor based on pressure duration.

        Returns:
            Reduction factor (0.25 to 0.5).

        """
        if self._consecutive_pressure_count >= 5:
            return 0.25  # Aggressive: reduce to 25%
        if self._consecutive_pressure_count >= 3:
            return 0.35  # Moderate-aggressive: reduce to 35%
        return 0.5  # Standard: reduce by half

    def estimate_batch_memory_mb(
        self, record_count: int, avg_record_size_bytes: int = 1024
    ) -> float:
        """Estimate memory usage for a batch.

        Args:
            record_count: Number of records in batch.
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Estimated memory usage in MB.

        """
        # Factor in transformation overhead (2x for in-memory copies)
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, avg_record_size_bytes: int = 1024) -> int:
        """Calculate maximum batch size based on available memory.

        Args:
            avg_record_size_bytes: Average size per record in bytes.

        Returns:
            Maximum recommended batch size.

        """
        max_memory_bytes = self.config.max_batch_memory_mb * 1024 * 1024
        overhead_factor = 2.5

        max_records = int(max_memory_bytes / (avg_record_size_bytes * overhead_factor))
        return max(max_records, self.config.min_batch_size)


__all__ = ["MemoryConfig", "MemoryMonitor", "MemoryStats"]
