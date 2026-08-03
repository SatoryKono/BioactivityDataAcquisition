"""Column renamer service for composite pipelines.

Provides unified column renaming to {provider}.{entity}.{field} format.
See ADR-026 for rationale.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

from bioetl.domain.value_objects.column_qualifier import ColumnQualifier

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort

__all__ = ["ColumnRenamer"]


class ColumnRenamer:
    """Service for renaming columns to qualified format.

    Renames all business columns to {provider}.{entity}.{field} format.
    Excludes join keys and system columns from renaming.

    Example:
        >>> renamer = ColumnRenamer(logger)
        >>> result = renamer.rename_dataframe(df, "chembl_publication")
        >>> # 'title' -> 'chembl.publication.title'
        >>> # 'doi' -> 'doi' (join key, unchanged)
        >>> # '_run_id' -> '_run_id' (system, unchanged)
    """

    # System column prefixes (not renamed)
    SYSTEM_PREFIXES: Final[frozenset[str]] = frozenset({"_"})

    # Identity columns that are never provider-qualified.
    # These are universal identifiers shared across all providers.
    IDENTITY_COLUMNS: Final[frozenset[str]] = frozenset(
        {
            "entity_id",
            "content_hash",
        }
    )

    # Join key columns (not renamed, case-insensitive)
    JOIN_KEY_COLUMNS: Final[frozenset[str]] = frozenset(
        {
            "publication_id",
            "publication_doi",
            "publication_pmid",
            "publication_pmc_id",
            # Backward-compatible publication keys used in tests/pipelines
            "doi",
            "pmid",
            "pmc_id",
        }
    )

    def __init__(self, logger: LoggerPort) -> None:
        """Initialize renamer.

        Args:
            logger: Logger port for diagnostics.
        """
        self._logger = logger

    def rename_dataframe(
        self,
        df: pl.DataFrame,
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
        field_aliases: dict[str, str] | None = None,
    ) -> pl.DataFrame:
        """Rename all business columns to qualified format.

        Transforms column names from 'field' to '{provider}.{entity}.{field}'.
        When ``field_aliases`` is provided, provider-specific field names are
        first normalized to canonical names before qualification.

        Args:
            df: DataFrame to rename.
            pipeline: Pipeline name in format 'provider_entity'.
            exclude_join_keys: If True, join keys (doi, pmid, pmc_id)
                are NOT renamed. Default: True.
            field_aliases: Optional mapping of provider-specific field names
                to canonical names (e.g., ``{"h_bond_acceptor_count": "hba_count"}``).
                Used to normalize field names across providers.

        Returns:
            DataFrame with renamed columns.

        Example:
            >>> df = pl.DataFrame({"doi": ["10.1/a"], "title": ["T1"], "_run_id": ["x"]})
            >>> result = renamer.rename_dataframe(df, "chembl_publication")
            >>> result.columns
            ['doi', 'chembl.publication.title', '_run_id']
        """
        rename_map = self.build_rename_map(
            columns=df.columns,
            pipeline=pipeline,
            exclude_join_keys=exclude_join_keys,
            field_aliases=field_aliases,
        )

        if not rename_map:
            return df

        self._logger.debug(
            "Renaming columns to qualified format",
            pipeline=pipeline,
            rename_count=len(rename_map),
            sample_renames=dict(list(rename_map.items())[:3]),
        )

        return df.rename(rename_map)

    def build_rename_map(
        self,
        columns: Sequence[str],
        pipeline: str,
        *,
        exclude_join_keys: bool = True,
        field_aliases: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Build rename mapping {old_name: new_name}.

        When ``field_aliases`` is provided, provider-specific field names
        are normalized to canonical names in the qualified output. For example,
        with alias ``{"h_bond_acceptor_count": "hba_count"}``, the column
        ``h_bond_acceptor_count`` becomes ``pubchem.compound.hba_count``.

        Args:
            columns: List of column names.
            pipeline: Pipeline name in format 'provider_entity'.
            exclude_join_keys: If True, exclude join keys from mapping.
            field_aliases: Optional mapping of provider-specific field names
                to canonical names.

        Returns:
            Dictionary mapping old column names to new qualified names.

        Raises:
            ValueError: If pipeline format is invalid.
        """
        provider, entity = self._parse_pipeline(pipeline)
        rename_map: dict[str, str] = {}

        for col in columns:
            # Skip system columns
            if self._is_system_column(col):
                self._logger.debug("Skipping system column", column=col)
                continue

            # Skip already qualified columns
            if self._is_already_qualified(col):
                self._logger.debug("Skipping already qualified column", column=col)
                continue

            # Skip join keys if requested
            if exclude_join_keys and self._is_join_key(col):
                self._logger.debug("Skipping join key column", column=col)
                continue

            # Normalize field name via alias if available
            canonical_field = col
            if field_aliases and col in field_aliases:
                canonical_field = field_aliases[col]
                self._logger.debug(
                    "Applying field alias",
                    original=col,
                    canonical=canonical_field,
                    provider=provider,
                )

            # Build qualified name using (possibly normalized) field name
            qualifier = ColumnQualifier(provider, entity, canonical_field)
            rename_map[col] = str(qualifier)

        return rename_map

    def _parse_pipeline(self, pipeline: str) -> tuple[str, str]:
        """Parse pipeline name into (provider, entity).

        Args:
            pipeline: Pipeline name in format 'provider_entity'.

        Returns:
            Tuple of (provider, entity).

        Raises:
            ValueError: If format is invalid.
        """
        if "_" not in pipeline:
            raise ValueError(
                f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
            )
        parts = pipeline.split("_", 1)
        return (parts[0].lower(), parts[1].lower())

    def _is_system_column(self, col: str) -> bool:
        """Check if column is a system or identity column."""
        if col in self.IDENTITY_COLUMNS:
            return True
        return any(col.startswith(prefix) for prefix in self.SYSTEM_PREFIXES)

    def _is_already_qualified(self, col: str) -> bool:
        """Check if column is already in qualified format (x.y.z)."""
        return ColumnQualifier.is_qualified(col)

    def _is_join_key(self, col: str) -> bool:
        """Check if column is a join key (case-insensitive)."""
        return col.lower() in self.JOIN_KEY_COLUMNS
