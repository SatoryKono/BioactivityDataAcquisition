"""Backward-compatible re-export for quality error classifier port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.error_classifier import ErrorClassifierPort

__all__ = ["ErrorClassifierPort"]
