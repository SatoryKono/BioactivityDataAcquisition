"""Backward-compatible re-export for runtime shutdown port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.shutdown import ShutdownPort

__all__ = ["ShutdownPort"]
