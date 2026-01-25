"""Column renamer service.

Unified column renaming for composite pipelines using {provider}.{entity}.{field} format.
"""

from typing import FrozenSet

import polars as pl


class ColumnRenamer:
    """Unified column renaming for composite pipelines.

    Applies {provider}.{entity}.{field} naming to ALL business columns.
    """

    # System columns prefix - strictly checks starts with
    SYSTEM_PREFIXES: FrozenSet[str] = frozenset({"_"})

    def rename_dataframe(
        self,
        df: pl.DataFrame,
        provider: str,
        entity: str,
        *,
        exclude_columns: set[str] | None = None,
    ) -> pl.DataFrame:
        """Rename ALL business columns to qualified format.

        Args:
            df: DataFrame to rename.
            provider: Provider name (e.g., 'chembl').
            entity: Entity name (e.g., 'publication').
            exclude_columns: Set of columns to NOT rename (e.g., join keys).

        Returns:
            DataFrame with renamed columns.
        """
        exclude = exclude_columns or set()
        rename_map = {}

        qualifier = f"{provider}.{entity}."

        for col in df.columns:
            # Skip system columns (start with _)
            if any(col.startswith(prefix) for prefix in self.SYSTEM_PREFIXES):
                continue

            # Skip explicitly excluded columns (join keys)
            if col in exclude:
                continue

            # Skip if already qualified
            if col.startswith(qualifier):
                continue

            rename_map[col] = f"{qualifier}{col}"

        if rename_map:
            return df.rename(rename_map)
        return df
