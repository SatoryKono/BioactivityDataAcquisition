"""Join-key resolution and normalization helpers."""

from __future__ import annotations

__all__ = ["JoinKeyResolverService"]


from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl


class JoinKeyResolverService:
    """Resolve and normalize join keys across qualified/unqualified schemas."""

    def __init__(
        self,
        *,
        normalize_join_keys: frozenset[str],
        parse_pipeline_name: Callable[[str], tuple[str, str]],
    ) -> None:
        self._normalize_join_keys = normalize_join_keys
        self._parse_pipeline_name = parse_pipeline_name

    def find_join_key_column(
        self,
        key: str,
        columns: list[str],
        pipeline: str | None = None,
    ) -> str | None:
        """Find key column name (qualified preferred, fallback unqualified).

        Args:
            key: Unqualified join key name (e.g. ``"chembl_id"``).
            columns: List of column names present in the current DataFrame.
            pipeline: Optional pipeline name used to build qualified column candidate.

        Returns:
            Qualified column name if found, unqualified name as fallback,
            or None if no matching column exists.
        """
        if pipeline:
            try:
                provider, entity = self._parse_pipeline_name(pipeline)
                qualified = f"{provider}.{entity}.{key}"
                if qualified in columns:
                    return qualified
            except ValueError:
                pass

        if key in columns:
            return key

        return next((col for col in columns if col.endswith(f".{key}")), None)

    def normalize_join_key_columns(
        self,
        df: pl.DataFrame,
        join_keys: list[str],
        pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Normalize selected identifier join key columns to lowercase.

        Args:
            df: DataFrame containing the columns to normalize.
            join_keys: List of unqualified key names to check for normalization.
            pipeline: Optional pipeline name used to locate qualified column variants.

        Returns:
            DataFrame with qualifying identifier columns (doi, pmid, pmc_id) lowercased.
        """
        import polars as pl

        columns = df.columns
        normalize = [
            column
            for key in join_keys
            if key in self._normalize_join_keys
            if (column := self.find_join_key_column(key, columns, pipeline))
        ]
        if not normalize:
            return df
        return df.with_columns(
            [pl.col(column).str.to_lowercase().alias(column) for column in normalize]
        )

    def resolve_join_key_names(
        self,
        primary_key: str,
        seed_pipeline: str | None,
        enricher_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names for seed/enricher join.

        Args:
            primary_key: Unqualified join key name shared by both sides.
            seed_pipeline: Optional seed pipeline name for qualified column lookup.
            enricher_pipeline: Enricher pipeline name for building qualified right key.
            merged_columns: Columns available in the current merged DataFrame.

        Returns:
            Tuple of (seed_join_key, enricher_join_key, seed_join_key_qualified) where
            seed_join_key_qualified is the fully-qualified seed key or None if unavailable.
        """
        seed_join_key_qualified: str | None = None
        seed_join_key = primary_key

        if seed_pipeline is not None:
            try:
                seed_provider, seed_entity = self._parse_pipeline_name(seed_pipeline)
                seed_join_key_qualified = f"{seed_provider}.{seed_entity}.{primary_key}"
                if seed_join_key_qualified in merged_columns:
                    seed_join_key = seed_join_key_qualified
            except ValueError:
                pass

        try:
            enricher_provider, enricher_entity = self._parse_pipeline_name(
                enricher_pipeline
            )
            enricher_join_key = f"{enricher_provider}.{enricher_entity}.{primary_key}"
        except ValueError:
            enricher_join_key = primary_key

        return seed_join_key, enricher_join_key, seed_join_key_qualified

    def resolve_join_key_names_asymmetric(
        self,
        left_key: str,
        right_key: str,
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[str, str, str | None]:
        """Resolve qualified join key names when left/right key names differ.

        Args:
            left_key: Unqualified key name on the left (merged) side.
            right_key: Unqualified key name on the right (dependency) side.
            left_pipeline: Optional left-side pipeline name for qualified column lookup.
            right_pipeline: Right-side pipeline name for building the qualified right key.
            merged_columns: Columns available in the current merged DataFrame.

        Returns:
            Tuple of (left_join_key, right_join_key, left_join_key_qualified) where
            left_join_key_qualified is the fully-qualified left key or None if unavailable.
        """
        left_join_key_qualified: str | None = None
        left_join_key = left_key

        if left_pipeline is not None:
            try:
                left_provider, left_entity = self._parse_pipeline_name(left_pipeline)
                left_join_key_qualified = f"{left_provider}.{left_entity}.{left_key}"
                if left_join_key_qualified in merged_columns:
                    left_join_key = left_join_key_qualified
            except ValueError:
                pass

        try:
            right_provider, right_entity = self._parse_pipeline_name(right_pipeline)
            right_join_key = f"{right_provider}.{right_entity}.{right_key}"
        except ValueError:
            right_join_key = right_key

        return left_join_key, right_join_key, left_join_key_qualified

    def resolve_composite_join_keys(
        self,
        join_keys_list: list[str],
        left_pipeline: str | None,
        right_pipeline: str,
        merged_columns: list[str],
    ) -> tuple[list[str], list[str], set[str]]:
        """Resolve all join keys for composite-key dependency join.

        Args:
            join_keys_list: Ordered list of unqualified key names to resolve.
            left_pipeline: Optional left-side pipeline name for qualified column lookup.
            right_pipeline: Right-side pipeline name for building qualified right keys.
            merged_columns: Columns available in the current merged DataFrame.

        Returns:
            Tuple of (left_keys, right_keys, all_join_key_set) with resolved qualified
            key names for each side and the complete set of all key column names.
        """
        left_keys: list[str] = []
        right_keys: list[str] = []
        all_join_key_set: set[str] = set()

        for key in join_keys_list:
            left_key, right_key, left_key_qualified = (
                self.resolve_join_key_names_asymmetric(
                    left_key=key,
                    right_key=key,
                    left_pipeline=left_pipeline,
                    right_pipeline=right_pipeline,
                    merged_columns=merged_columns,
                )
            )
            left_keys.append(left_key)
            right_keys.append(right_key)
            all_join_key_set.add(left_key)
            all_join_key_set.add(right_key)
            if left_key_qualified and left_key_qualified != left_key:
                all_join_key_set.add(left_key_qualified)

        return left_keys, right_keys, all_join_key_set
