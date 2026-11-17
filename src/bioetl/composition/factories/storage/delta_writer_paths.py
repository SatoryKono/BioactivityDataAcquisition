"""Public Delta writer path helpers for cross-owner composition callers."""

from __future__ import annotations

from bioetl.composition.factories.storage._helpers import (
    resolve_delta_writer_base_path,
    resolve_delta_writer_flat_structure,
)

__all__ = [
    "resolve_delta_writer_base_path",
    "resolve_delta_writer_flat_structure",
]
