"""Backward-compatible re-export for quality quarantine port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.quarantine import QuarantinePort

__all__ = ["QuarantinePort"]
