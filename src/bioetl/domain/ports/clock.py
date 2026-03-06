"""Backward-compatible re-export for runtime clock port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.clock import ClockPort

__all__ = ["ClockPort"]
