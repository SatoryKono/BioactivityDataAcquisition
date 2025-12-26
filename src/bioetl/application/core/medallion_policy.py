"""Medallion layer write mode policies.

Validates that write operations comply with medallion architecture rules.
Per RULES.md §3 (Medallion Architecture):
- Bronze: Append-only (immutable raw data)
- Silver: Merge/Upsert or Append (idempotent transforms)
- Gold: Merge or Overwrite (aggregated/derived data)

Note: This module re-exports from bioetl.domain.medallion for backward compatibility.
The canonical location is bioetl.domain.medallion.
"""

from __future__ import annotations

# Re-export from domain layer for backward compatibility
from bioetl.domain.medallion import Layer, WriteMode, WriteModePolicy

__all__ = ["Layer", "WriteMode", "WriteModePolicy"]
