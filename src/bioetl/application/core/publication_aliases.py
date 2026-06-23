"""Publication legacy→canonical field alias registry.

Centralizes compatibility aliases used by composite publication pipelines.
Maps ChEMBL API field names to unified canonical names for cross-provider
column ordering and matching.
"""

from __future__ import annotations

from datetime import date
from typing import Final

LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE: Final[date] = date(2026, 3, 29)
"""Date when legacy publication alias migration was considered complete."""

__all__ = ["LEGACY_PUBLICATION_ALIASES_CUTOFF_DATE"]
