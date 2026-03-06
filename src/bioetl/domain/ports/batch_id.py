"""Backward-compatible re-export for runtime batch-id port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.runtime.batch_id import BatchIdGeneratorPort

__all__ = ["BatchIdGeneratorPort"]
