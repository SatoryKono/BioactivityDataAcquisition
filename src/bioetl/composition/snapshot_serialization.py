"""Composition facade. Implementation lives in `bioetl.domain.serialization.snapshot_serialization` (#11241)."""

from __future__ import annotations

from bioetl.domain.serialization.snapshot_serialization import (
    normalize_snapshot,
    to_serializable_mapping,
)

__all__ = ['normalize_snapshot', 'to_serializable_mapping']
