"""Input filter configuration.

Provides configuration for input-based filtering of pipeline records.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FilterColumn:
    """Single column filter configuration.

    Attributes:
        column_name: Name of the column in CSV file.
        filter_field: API field to filter by (e.g., molecule_chembl_id).
    """

    column_name: str
    filter_field: str


@dataclass(frozen=True, slots=True)
class InputFilterConfig:
    """Configuration for input-based filtering.

    When enabled, the pipeline will only fetch records matching
    the IDs provided in the source file.

    Supports both single-column and multi-column filtering modes:
    - Single-column: Use column_name and filter_field directly
    - Multi-column: Use columns list for AND-logic filtering

    Attributes:
        enabled: Whether filtering is active.
        source_path: Path to the filter source (e.g., CSV file).
        column_name: Name of the column containing filter IDs (single-column mode).
        filter_field: API field to filter by (single-column mode).
        columns: Tuple of FilterColumn for multi-column filtering.
        batch_size: Number of IDs per API request (ChEMBL limit ~100).
        fallback_column: Optional column for fallback search (e.g., 'title' for DOI→title).
    """

    enabled: bool = False
    source_path: str | None = None
    column_name: str | None = None
    filter_field: str | None = None
    columns: tuple[FilterColumn, ...] = ()
    batch_size: int = 100
    fallback_column: str | None = None

    def __post_init__(self) -> None:
        """Validate configuration consistency."""
        self._validate_enabled_fields()
        self._validate_batch_size()

    def _validate_enabled_fields(self) -> None:
        """Validate fields required when filtering is enabled."""
        if not self.enabled:
            return
        if not self.source_path:
            raise ValueError("source_path is required when filter is enabled")
        # Either columns list or single column_name/filter_field must be provided
        if self.columns:
            self._validate_columns()
        elif not self._has_single_column_config():
            raise ValueError(
                "Either columns list or column_name/filter_field is required "
                "when filter is enabled"
            )

    def _has_single_column_config(self) -> bool:
        """Check if single-column configuration is complete."""
        return bool(self.column_name and self.filter_field)

    def _validate_columns(self) -> None:
        """Validate multi-column configuration."""
        for col in self.columns:
            if not col.column_name or not col.filter_field:
                raise ValueError("Each column must have column_name and filter_field")

    def _validate_batch_size(self) -> None:
        """Validate the batch_size is within a reasonable range."""
        if not (1 <= self.batch_size <= 1000):
            raise ValueError("batch_size must be between 1 and 1000")

    @property
    def is_multi_column(self) -> bool:
        """Check if multi-column filtering mode is active."""
        return len(self.columns) > 1

    def get_columns(self) -> tuple[FilterColumn, ...]:
        """Get filter columns (resolves single-column to columns format).

        Returns:
            Tuple of FilterColumn objects. For single-column mode, creates
            a tuple with one FilterColumn from column_name/filter_field.
        """
        if self.columns:
            return self.columns
        if self.column_name and self.filter_field:
            return (FilterColumn(self.column_name, self.filter_field),)
        return ()
