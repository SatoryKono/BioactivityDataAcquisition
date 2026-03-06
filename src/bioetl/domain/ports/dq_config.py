"""Backward-compatible re-export for quality DQ config ports.

Compatibility shim: canonical Port Protocol definitions remain @runtime_checkable
in subpackages and are re-exported here for stable import paths."""

from bioetl.domain.ports.quality.dq_config import (
    BronzeDQConfigPort,
    GoldDQConfigPort,
    SilverDQConfigPort,
)

__all__ = [
    "BronzeDQConfigPort",
    "GoldDQConfigPort",
    "SilverDQConfigPort",
]
