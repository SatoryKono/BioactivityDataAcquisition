# pyright: reportOptionalMemberAccess=false
# basedpyright residual burn-down (shrink-only product surface).
"""Memory monitoring for adaptive batch processing.

Provides memory pressure detection and adaptive batch size recommendations.
Uses psutil if available, falls back to resource module on Unix or estimates on Windows.

Implements MemoryMonitorPort from domain/ports/memory.py.

Performance optimizations:
- Module-level psutil availability cache (avoid repeated import checks)
- Cached Process instance (avoid repeated process lookup)
- Lazy psutil import (deferred until first get_memory_stats() call)

Note:
    This module is part of the infrastructure layer (Ports & Adapters architecture).
    It provides the concrete implementation of MemoryMonitorPort defined in domain/ports/memory.py.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

# Import domain value objects
from bioetl.domain.config import MemoryConfig

# Re-export MemoryStats from domain for backward compatibility
from bioetl.domain.ports import MemoryStats

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

# Module-level cache for psutil availability (checked once per process)
_psutil_available: bool | None = None
_psutil_module: Any = None  # Any: lazy-loaded psutil module reference


def _check_psutil_available() -> bool:
    """Check psutil availability once and cache the result.

    Returns:
        True if psutil is available and importable, False otherwise.
    """
    global _psutil_available, _psutil_module
    if _psutil_available is None:
        try:
            import psutil

            _psutil_module = psutil
            _psutil_available = True
        except ImportError:
            _psutil_available = False
    return _psutil_available


@dataclass
class MemoryMonitor:
    """Monitor memory usage and provide adaptive batch-size recommendations."""

    config: MemoryConfig
    logger: LoggerPort | None = None
    _psutil_available: bool = field(default=False, init=False)
    _last_batch_size: int = field(default=100, init=False)
    _recovery_target_batch_size: int | None = field(default=None, init=False)
    _consecutive_pressure_count: int = field(default=0, init=False)
    _last_monitor_mode: str = field(default="unknown", init=False)
    _last_pressure_state: bool | None = field(default=None, init=False)
    # Any: optional psutil.Proces...
    _cached_process: Any = field(  # Any: type varies at runtime
        default=None, init=False
    )  # Any: psutil.Process cached; optional dependency

    def __post_init__(self) -> None:
        """Initialize memory monitor with cached psutil detection."""
        self._psutil_available = _check_psutil_available()
        if self._psutil_available and self.logger:
            self.logger.debug("psutil available for memory monitoring")
        elif not self._psutil_available and self.logger:
            self.logger.debug("psutil not available, using fallback memory monitoring")

    def get_monitor_mode(self) -> str:
        """Return the bounded monitor mode observed by the last stats call."""
        return self._last_monitor_mode

    def get_last_pressure_state(self) -> bool | None:
        """Return the pressure decision observed by the last adaptive check."""
        return self._last_pressure_state

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        if self._psutil_available:
            return self._get_stats_psutil()
        return self._get_stats_fallback()

    def _get_stats_psutil(self) -> MemoryStats:
        """Get memory stats using psutil with cached module and process handles."""
        psutil = _psutil_module
        self._last_monitor_mode = "psutil"
        vm = psutil.virtual_memory()
        if self._cached_process is None:
            object.__setattr__(self, "_cached_process", psutil.Process())
        process_memory = self._cached_process.memory_info()

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
        """Get memory stats using the Unix `resource` module and `/proc/meminfo`."""
        import resource

        resource_module: Any = resource  # Any: resource module unavailable on Windows
        rusage = resource_module.getrusage(resource_module.RUSAGE_SELF)
        process_mb = rusage.ru_maxrss / 1024  # Convert KB to MB on Linux
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
                self._last_monitor_mode = "resource"

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
        """Provide conservative estimates when actual stats are unavailable."""
        self._last_monitor_mode = "estimate"
        return MemoryStats(
            used_mb=4096.0,  # Assume 4GB used
            available_mb=4096.0,  # Assume 4GB available
            total_mb=8192.0,  # Assume 8GB total
            percent_used=0.5,
            process_mb=256.0,  # Assume 256MB process
        )

    def is_under_pressure(self) -> bool:
        """Check if system is under memory pressure."""
        if not self.config.enable_adaptive_sizing:
            self._last_pressure_state = None
            return False

        stats = self.get_memory_stats()
        is_pressure = stats.percent_used >= self.config.memory_pressure_threshold
        self._last_pressure_state = is_pressure
        return is_pressure

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Return adaptive batch size recommendation based on current memory pressure.

        Returns:
            Adjusted batch size integer, reduced under pressure or gradually recovered.
        """
        if not self.config.enable_adaptive_sizing:
            self._last_pressure_state = None
            return current_batch_size

        stats = self.get_memory_stats()
        is_pressure = stats.percent_used >= self.config.memory_pressure_threshold
        self._last_pressure_state = is_pressure

        if is_pressure:
            return self._reduce_batch_size_under_pressure(
                current_batch_size=current_batch_size,
                stats=stats,
            )

        self._consecutive_pressure_count = 0
        recovery_target = self._recovery_target_batch_size or self._last_batch_size
        if current_batch_size < recovery_target:
            return self._recover_batch_size(
                current_batch_size=current_batch_size,
                recovery_target=recovery_target,
                stats=stats,
            )

        self._recovery_target_batch_size = None
        self._last_batch_size = current_batch_size
        return current_batch_size

    def _reduce_batch_size_under_pressure(
        self,
        *,
        current_batch_size: int,
        stats: MemoryStats,
    ) -> int:
        self._consecutive_pressure_count += 1
        reduction_factor = self._get_reduction_factor()
        new_size = max(
            int(current_batch_size * reduction_factor),
            self.config.min_batch_size,
        )
        if new_size < current_batch_size:
            self._update_recovery_tracking(current_batch_size)
            self._log_batch_size_reduction(
                current_batch_size=current_batch_size,
                new_size=new_size,
                stats=stats,
            )
        return new_size

    def _recover_batch_size(
        self,
        *,
        current_batch_size: int,
        recovery_target: int,
        stats: MemoryStats,
    ) -> int:
        recovery_size = min(
            max(current_batch_size + 1, int(current_batch_size * 1.25)),
            recovery_target,
        )
        if self.logger:
            self.logger.debug(
                "Memory pressure relieved, increasing batch size",
                current_batch_size=current_batch_size,
                new_batch_size=recovery_size,
                memory_percent_used=round(stats.percent_used * 100, 1),
            )
        if recovery_size >= recovery_target:
            self._recovery_target_batch_size = None
            self._last_batch_size = recovery_target
        return recovery_size

    def _update_recovery_tracking(self, current_batch_size: int) -> None:
        if (
            self._recovery_target_batch_size is None
            or current_batch_size > self._recovery_target_batch_size
        ):
            self._recovery_target_batch_size = current_batch_size
        self._last_batch_size = self._recovery_target_batch_size

    def _log_batch_size_reduction(
        self,
        *,
        current_batch_size: int,
        new_size: int,
        stats: MemoryStats,
    ) -> None:
        if self.logger is None:
            return
        self.logger.warning(
            "Memory pressure detected, reducing batch size",
            current_batch_size=current_batch_size,
            new_batch_size=new_size,
            memory_percent_used=round(stats.percent_used * 100, 1),
            consecutive_pressure_count=self._consecutive_pressure_count,
        )

    def _get_reduction_factor(self) -> float:
        """Get batch-size reduction factor based on pressure duration."""
        if self._consecutive_pressure_count >= 5:
            return 0.25  # Aggressive: reduce to 25%
        if self._consecutive_pressure_count >= 3:
            return 0.35  # Moderate-aggressive: reduce to 35%
        return 0.5  # Standard: reduce by half

    def estimate_batch_memory_mb(
        self, record_count: int, avg_record_size_bytes: int = 1024
    ) -> float:
        """Estimate memory usage for a batch."""
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, avg_record_size_bytes: int = 1024) -> int:
        """Calculate maximum batch size based on available memory."""
        max_memory_bytes = self.config.max_batch_memory_mb * 1024 * 1024
        overhead_factor = 2.5
        max_records = int(max_memory_bytes / (avg_record_size_bytes * overhead_factor))
        return max(max_records, self.config.min_batch_size)


__all__ = ["MemoryConfig", "MemoryMonitor", "MemoryStats"]
