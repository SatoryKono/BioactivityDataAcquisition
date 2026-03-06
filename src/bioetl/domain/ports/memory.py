"""Backward-compatible re-export for runtime memory ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.memory import MemoryMonitorPort, MemoryStats

__all__ = ["MemoryMonitorPort", "MemoryStats"]
