"""SilverWriteResult value object for Silver layer write operation results.

Implements RULES.md §2.1.2 - Silver Layer specifications.

This value object encapsulates the result of a Silver write operation,
providing all necessary information for downstream lineage tracking
in Gold layer.

Requirements:
- REQ-LINEAGE-002: Track Silver table versions for Gold lineage
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "SilverWriteResult",
]


@dataclass(frozen=True, slots=True)
class SilverWriteResult:
    """Result of a Silver layer write operation.

    This frozen dataclass captures all metadata from a Silver write operation
    needed for lineage tracking in downstream Gold layer.

    Attributes:
        table_name: Silver table name (e.g., "chembl.activity").
        table_path: Full path to Silver Delta table.
        delta_version: Delta table version after write.
        record_count: Number of records written.

    Example:
        >>> result = SilverWriteResult(
        ...     table_name="chembl.activity",
        ...     table_path="/data/silver/chembl/activity",
        ...     delta_version=42,
        ...     record_count=1000,
        ... )
        >>> result.table_name
        'chembl.activity'
    """

    table_name: str
    table_path: str
    delta_version: int
    record_count: int

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        self._validate_non_negative_fields()
        self._validate_required_strings()

    def _validate_non_negative_fields(self) -> None:
        """Validate that numeric fields are non-negative."""
        if self.delta_version < 0:
            raise ValueError(
                f"delta_version must be non-negative, got {self.delta_version}"
            )
        if self.record_count < 0:
            raise ValueError(
                f"record_count must be non-negative, got {self.record_count}"
            )

    def _validate_required_strings(self) -> None:
        """Validate that required string fields are not empty."""
        if not self.table_name:
            raise ValueError("table_name cannot be empty")
        if not self.table_path:
            raise ValueError("table_path cannot be empty")
