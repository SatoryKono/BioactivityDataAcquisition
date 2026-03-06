"""Backward-compatible re-export for runtime checkpoint port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.checkpoint import CheckpointPort

__all__ = ["CheckpointPort"]
