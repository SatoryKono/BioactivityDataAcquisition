"""Backward-compatible re-export for quality DQ config ports."""

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
