"""Backward-compatible re-export for quality fallback policy port.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.fallback_policy import FallbackPolicyPort

__all__ = ["FallbackPolicyPort"]
