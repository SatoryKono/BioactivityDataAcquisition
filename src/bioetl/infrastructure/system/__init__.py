"""System-level infrastructure components.

This package contains infrastructure adapters for system-level operations:
- Memory monitoring (psutil, /proc/meminfo, resource module)
- System metrics collection
"""

from __future__ import annotations

# Package-level re-export shim — sunset date: 2026-12-31. Canonical home is
# bioetl.infrastructure.system.memory_monitor; first-party code MUST import
# from that module. Codemod: replace
# `from bioetl.infrastructure.system import MemoryMonitor` ->
# `from bioetl.infrastructure.system.memory_monitor import MemoryMonitor`.
from bioetl.infrastructure.system.memory_monitor import MemoryMonitor

__all__ = ["MemoryMonitor"]
