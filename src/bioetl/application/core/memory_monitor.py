"""Backward compatibility shim for memory monitoring types.

The MemoryMonitor implementation has been moved to infrastructure layer:
bioetl.infrastructure.system.memory_monitor

This module re-exports domain types (MemoryConfig, MemoryStats) for backward compatibility.

For MemoryMonitor implementation, import from:
- bioetl.infrastructure.system.memory_monitor (in composition layer)
- Or use MemoryMonitorPort (domain/ports/memory.py) for type hints in application layer

Note:
    Memory monitoring involves system-level operations (reading /proc/meminfo,
    using psutil) which belong in the infrastructure layer per Hexagonal Architecture.
    Application layer should depend on MemoryMonitorPort (abstract interface), not
    on the concrete MemoryMonitor class.
"""

from __future__ import annotations

# Re-export domain types for backward compatibility
from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import MemoryStats

__all__ = ["MemoryConfig", "MemoryStats"]
