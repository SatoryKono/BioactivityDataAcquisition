"""Conflict resolution utilities for composite merge pipeline."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.domain.composite.strategy import ConflictResolution

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.composite.config import EnricherConfig, MergeConfig
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

        match self._config.conflict_resolution:
            case ConflictResolution.SEED_PRIORITY:
                return self._coalesce_policy.coalesce_prefer_seed(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.ENRICHER_PRIORITY:
                return self._coalesce_policy.coalesce_prefer_enricher(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.COALESCE:
                return self._coalesce_policy.coalesce_first_non_null(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case ConflictResolution.EXPLICIT_RULES:
                return self._coalesce_policy.apply_explicit_rules(
                    df,
                    enrichers,
                    self._config.field_priorities,
                    seed_pipeline,
                )
            case ConflictResolution.LATEST_TIMESTAMP:
                return self._coalesce_policy.coalesce_prefer_seed(
                    df,
                    enrichers,
                    seed_pipeline,
                )
            case _:
                return df
