"""ChEMBL Activity Gold Filter.

Logic for filtering records for the Gold layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext


class ActivityGoldFilter:
    """Filters ChEMBL activities for the Gold layer."""

    def __init__(self, preferred_types: list[str] | None = None):
        """Initialize with preferred activity types (e.g. IC50, Ki)."""
        self._preferred_types = set(preferred_types or []) or {
            "IC50",
            "Ki",
        }

    def should_include(self, _context: PipelineContext, record: dict[str, Any]) -> bool:
        """Filter records for Gold layer."""
        if record.get("standard_value") is None:
            return False
        if not record.get("standard_units"):
            return False
        if not record.get("target_chembl_id"):
            return False

        standard_type = record.get("standard_type")
        # Use pre-computed set for fast lookup
        if standard_type not in self._preferred_types:
            return False

        return not record.get("data_validity_comment")
