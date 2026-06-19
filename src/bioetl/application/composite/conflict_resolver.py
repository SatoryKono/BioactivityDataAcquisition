"""Conflict resolution utilities for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import polars as pl

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.domain.composite.config import EnricherConfig, MergeConfig
from bioetl.domain.composite.strategy import ConflictResolution
from bioetl.domain.ports import LoggerPort

__all__ = ["ConflictResolverService"]


class ConflictResolverService:
    """Handles column conflict detection and policy-based coalescing."""

    def __init__(
        self,
        merge_config: MergeConfig,
        logger: LoggerPort,
        coalesce_policy: CoalescePolicyService,
    ) -> None:
        self._config = merge_config
        self._logger = logger
        self._coalesce_policy = coalesce_policy

    def find_next_suffix(self, base_col: str, existing_cols: set[str]) -> str:
        """Find next available A/B/C/... suffix for conflicting columns.

        Args:
            base_col: Base column name to find a suffix for.
            existing_cols: Set of column names already in use.

        Returns:
            Single or double letter suffix string (e.g. ``"A"``, ``"B"``, ``"AA"``).
        """
        suffix_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

        for char in suffix_chars:
            candidate = f"{base_col}.{char}"
            if candidate not in existing_cols:
                return char

        for first in suffix_chars:
            for second in suffix_chars:
                suffix = f"{first}{second}"
                candidate = f"{base_col}.{suffix}"
                if candidate not in existing_cols:
                    return suffix

        raise ValueError(f"Exhausted all suffixes for column '{base_col}'")

    def detect_and_resolve_conflicts(
        self,
        seed_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        join_keys: set[str],
    ) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Rename conflicting enricher columns while preserving seed columns.

        Args:
            seed_df: Seed DataFrame whose column names take priority.
            enricher_df: Enricher DataFrame with columns to rename on conflict.
            join_keys: Set of join key column names to exclude from conflict detection.

        Returns:
            Tuple of (seed_df, enricher_df) where conflicting enricher columns have been
            renamed with letter suffixes to avoid overwriting seed values.
        """
        seed_cols = set(seed_df.columns)
        enricher_cols = set(enricher_df.columns)
        conflicts = (seed_cols & enricher_cols) - join_keys

        if not conflicts:
            return seed_df, enricher_df

        enricher_rename: dict[str, str] = {}
        for col in conflicts:
            suffix = self.find_next_suffix(col, seed_cols)
            enricher_rename[col] = f"{col}.{suffix}"

        self._logger.warning(
            "Column name conflicts detected after prefixing",
            conflicts=list(conflicts),
            resolution=f"Renaming enricher columns: {enricher_rename}",
        )

        return seed_df, enricher_df.rename(enricher_rename)

    def resolve_conflicts(
        self,
        df: pl.DataFrame,
        _enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Apply configured conflict-resolution policy to merged DataFrame.

        Args:
            df: Merged DataFrame potentially containing duplicate qualified columns.
            _enricher_dfs: Enricher DataFrames by name (unused, kept for API symmetry).
            enrichers: Enricher configurations used by the coalesce policy.
            seed_pipeline: Pipeline name used to identify seed columns; defaults to None.

        Returns:
            DataFrame after applying the configured ConflictResolution policy (coalescing,
            seed-priority, enricher-priority, or explicit rules).
        """
        if self._config.preserve_all_sources:
            qualified_cols = [
                col for col in df.columns if "." in col and not col.startswith("_")
            ]
            self._logger.info(
                "Skipping conflict resolution - preserve_all_sources=True",
                qualified_columns=len(qualified_cols),
            )
            return df

        return self._resolve_by_policy(df, enrichers, seed_pipeline)

    def _resolve_by_policy(
        self,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        handler = self._resolve_policy_handler(
            df=df,
            enrichers=enrichers,
            seed_pipeline=seed_pipeline,
        )
        return handler() if handler is not None else df

    def _resolve_policy_handler(
        self,
        *,
        df: pl.DataFrame,
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None,
    ) -> Callable[[], pl.DataFrame] | None:
        """Map configured conflict policy to coalesce-policy execution callable."""
        policy = self._config.conflict_resolution
        match policy:
            case ConflictResolution.SEED_PRIORITY:
                return lambda: self._coalesce_policy.coalesce_prefer_seed(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.ENRICHER_PRIORITY:
                return lambda: self._coalesce_policy.coalesce_prefer_enricher(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.COALESCE:
                return lambda: self._coalesce_policy.coalesce_first_non_null(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.EXPLICIT_RULES:
                return lambda: self._coalesce_policy.apply_explicit_rules(
                    df,
                    enrichers,
                    self._config.field_priorities,
                    seed_pipeline,
                )
            case ConflictResolution.LATEST_TIMESTAMP:
                return lambda: self._coalesce_policy.coalesce_prefer_latest_timestamp(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case _:
                return None
