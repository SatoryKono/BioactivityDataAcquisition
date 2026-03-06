"""Backward-compatible re-export for runtime locking port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.locking import LockPort

__all__ = ["LockPort"]
