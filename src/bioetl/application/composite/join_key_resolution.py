"""Join-key resolution and normalization helpers."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from bioetl.application.composite.helpers.resolver_helper import ResolverHelper
from bioetl.application.composite.join_key_resolution_helpers import (
    find_join_key_column,
    resolve_composite_join_keys,
    resolve_join_key_names,
    resolve_join_key_names_asymmetric,
)

__all__ = ["JoinKeyResolverService"]


class JoinKeyResolverService:
    """Resolve and normalize join keys across qualified/unqualified schemas."""

    def __init__(
        self,
        *,
        resolver_helper: ResolverHelper,
        parse_pipeline_name: Callable[[str], tuple[str, str]],
    ) -> None:
        self._resolver_helper = resolver_helper
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
        return find_join_key_column(
            key=key,
            columns=columns,
            pipeline=pipeline,
            parse_pipeline_name=self._parse_pipeline_name,
        )

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
            DataFrame with canonical trim/casing policy applied to supported
            string join keys.
        """
        return self._resolver_helper.normalize_join_keys(
            df=df,
            join_keys=join_keys,
            pipeline=pipeline,
            parse_pipeline_name=self._parse_pipeline_name,
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
        return resolve_join_key_names(
            primary_key=primary_key,
            seed_pipeline=seed_pipeline,
            enricher_pipeline=enricher_pipeline,
            merged_columns=merged_columns,
            parse_pipeline_name=self._parse_pipeline_name,
        )

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
        return resolve_join_key_names_asymmetric(
            left_key=left_key,
            right_key=right_key,
            left_pipeline=left_pipeline,
            right_pipeline=right_pipeline,
            merged_columns=merged_columns,
            parse_pipeline_name=self._parse_pipeline_name,
        )

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
        return resolve_composite_join_keys(
            join_keys_list=join_keys_list,
            left_pipeline=left_pipeline,
            right_pipeline=right_pipeline,
            merged_columns=merged_columns,
            parse_pipeline_name=self._parse_pipeline_name,
        )
