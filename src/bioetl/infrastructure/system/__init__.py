"""System-level infrastructure components.

This package contains infrastructure adapters for system-level operations:
- Memory monitoring (psutil, /proc/meminfo, resource module)
- System metrics collection
"""

from __future__ import annotations

from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

__all__ = ["MemoryMonitor"]
