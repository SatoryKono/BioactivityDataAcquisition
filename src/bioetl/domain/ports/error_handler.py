"""Backward-compatible re-export for quality error handler port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.error_handler import ErrorHandlerPort

__all__ = ["ErrorHandlerPort"]
