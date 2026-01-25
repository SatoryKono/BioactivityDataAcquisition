"""Column Renamer Service.

Unified service for renaming columns in composite pipelines to the
{provider}.{entity}.{field} format. See ADR-026.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl
    from bioetl.domain.ports import LoggerPort


class ColumnRenamer:
    """Service for renaming columns to qualified format."""

    SYSTEM_PREFIXES: frozenset[str] = frozenset({"_"})
    JOIN_KEY_COLUMNS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize renamer service.

        Args:
            logger: Logger instance.
        """
        self._logger = logger

    def rename_dataframe(
        self,
        df: pl.DataFrame,
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
    ) -> pl.DataFrame:
        """Rename ALL business columns to format {provider}.{entity}.{field}.

        Args:
            df: DataFrame to rename.
            pipeline: Pipeline name (e.g., 'chembl_publication').
            exclude_join_keys: If True, join keys (doi, pmid, pmc_id) are NOT renamed.

        Returns:
            DataFrame with renamed columns.
        """
        rename_map = self.build_rename_map(
            df.columns, pipeline, exclude_join_keys=exclude_join_keys
        )

        if not rename_map:
            return df

        self._logger.debug(
            "Renaming columns",
            pipeline=pipeline,
            rename_count=len(rename_map),
        )

        return df.rename(rename_map)

    def build_rename_map(
        self,
        columns: Sequence[str],
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
    ) -> dict[str, str]:
        """Build dictionary of {old_name: new_name} for renaming.

        Args:
            columns: List of column names.
            pipeline: Pipeline name.
            exclude_join_keys: Whether to exclude join keys from renaming.

        Returns:
            Dictionary mapping old names to qualified names.
        """
        rename_map = {}
        for col in columns:
            if self._is_system_column(col):
                self._logger.debug("Skipping system column", column=col)
                continue

            if self._is_already_qualified(col):
                self._logger.debug("Skipping already qualified column", column=col)
                continue

            if exclude_join_keys and self._is_join_key(col):
                continue

            try:
                qualifier = ColumnQualifier.from_pipeline(pipeline, col)
                rename_map[col] = str(qualifier)
            except ValueError as e:
                self._logger.warning(
                    "Could not qualify column",
                    column=col,
                    pipeline=pipeline,
                    error=str(e),
                )
                continue

        return rename_map

    def _is_system_column(self, col: str) -> bool:
        """Check if column is a system column (starts with underscore)."""
        return any(col.startswith(prefix) for prefix in self.SYSTEM_PREFIXES)

    def _is_already_qualified(self, col: str) -> bool:
        """Check if column is already in qualified format (contains dots)."""
        # Simple heuristic: if it has 2 dots, it's likely qualified
        # Proper check would be trying to parse it, but that might be overkill
        # here as we assume incoming data is either raw or qualified.
        return col.count(".") >= 2

    def _is_join_key(self, col: str) -> bool:
        """Check if column is a join key (case-insensitive)."""
        return col.lower() in self.JOIN_KEY_COLUMNS
