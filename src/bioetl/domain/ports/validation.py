"""Backward-compatible re-export for quality validation ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.validation import (
    GoldValidatorPort,
    SilverValidatorPort,
)

__all__ = ["GoldValidatorPort", "SilverValidatorPort"]
