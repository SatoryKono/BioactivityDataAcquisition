"""Filter load result.

Provides the result container for loading filter IDs with deduplication metadata.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

__all__ = [
    "FilterLoadResult",
]


@dataclass(frozen=True)
class FilterLoadResult:
    """Filter ID load result with deduplication metadata.

    Supports both single-column and multi-column filtering modes:
    - Single-column: Use ids, total_count, unique_count, duplicate_count, duplicates
    - Multi-column: Use column_ids for per-field unique IDs, valid_combinations for
      exact row-wise combinations to filter

    Attributes:
        ids: Unique sorted IDs (single-column mode).
        total_count: Total records in the source (before deduplication).
        unique_count: Number of unique IDs (single-column mode).
        duplicate_count: Number of removed duplicates.
        duplicates: IDs that appeared more than once.
        column_ids: Per-field unique IDs for multi-column mode.
            Mapping from filter_field to tuple of unique IDs.
        valid_combinations: Exact row-wise combinations to match (multi-column mode).
            Each tuple contains values in the same order as columns were defined.
        filter_fields: Ordered tuple of filter field names for valid_combinations.
    """

    ids: tuple[str, ...] = ()
    total_count: int = 0
    unique_count: int = 0
    duplicate_count: int = 0
    duplicates: frozenset[str] = field(default_factory=frozenset)
    column_ids: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    valid_combinations: frozenset[tuple[str, ...]] = field(default_factory=frozenset)
    filter_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate result consistency."""
        # Skip validation for multi-column results
        if self.column_ids and not self.ids:
            return
        # Single-column validation
        if self.unique_count != len(self.ids):
            raise ValueError(
                f"unique_count ({self.unique_count}) must match len(ids) ({len(self.ids)})"
            )
        if self.duplicate_count != self.total_count - self.unique_count:
            raise ValueError(
                f"duplicate_count ({self.duplicate_count}) must equal "
                f"total_count - unique_count ({self.total_count - self.unique_count})"
            )

    @property
    def has_duplicates(self) -> bool:
        """Check whether any duplicates were found."""
        return self.duplicate_count > 0

    @property
    def is_multi_column(self) -> bool:
        """Check if this is a multi-column filter result."""
        return bool(self.column_ids) and len(self.column_ids) > 1
