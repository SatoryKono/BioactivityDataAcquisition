"""Input loading mixin for MergeService."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import polars as pl

from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.exceptions import StorageError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MergedStoragePort
    from bioetl.domain.ports.delta_reader import DeltaReaderPort


@dataclass(frozen=True)
class _PreparedSeedDataframe:
    """Seed DataFrame with provenance metadata."""
    
    df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None


class _MergeInputLoaderMixin:
    """Mixin providing input loading methods for MergeService."""
    
    # Host-class attributes (set by MergeService.__init__)
    _logger: LoggerPort
    _storage: MergedStoragePort
    _delta_reader: DeltaReaderPort | None
    _renamer: Any  # ColumnRenamerService
    _config: Any  # MergeConfig

    async def _read_optional_merge_input(
        self,
        pipeline: str,
        table: str,
        role: str,
    ) -> pl.DataFrame | None:
        """Read optional input table, returning None on error."""
        try:
            return await self._read_silver_table(table)
        except (StorageError, ValueError) as exc:
            self._logger.warning(
                f"Skipping {role} input due to read error",
                pipeline=pipeline,
                table=table,
                role=role,
                error=str(exc),
            )
            return None

    async def _prepare_seed_dataframe(
        self,
        seed_table: str,
        seed_pipeline: str | None,
    ) -> _PreparedSeedDataframe:
        """Read and prepare seed DataFrame with pipeline qualification."""
        seed_df = await self._read_silver_table(seed_table)
        
        # Apply column renaming if seed_pipeline is provided
        effective_seed_pipeline = seed_pipeline
        if seed_pipeline and hasattr(self._renamer, 'rename_dataframe'):
            seed_df = self._renamer.rename_dataframe(seed_df)
        else:
            # Try to infer pipeline from table name if not provided
            effective_seed_pipeline = None
        
        return _PreparedSeedDataframe(
            df=seed_df,
            records_from_seed=len(seed_df),
            effective_seed_pipeline=effective_seed_pipeline,
        )

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load DataFrames for successful enrichers only."""
        enricher_dfs: dict[str, pl.DataFrame] = {}
        sources_used: list[str] = []
        
        for enricher in enrichers:
            result = enrichment_results.get(enricher.pipeline)
            if result and result.status == EnrichmentStatus.SUCCESS:
                df = await self._read_optional_merge_input(
                    pipeline=enricher.pipeline,
                    table=enricher.silver_table or f"silver/{enricher.pipeline}",
                    role="enricher",
                )
                if df is not None:
                    enricher_dfs[enricher.pipeline] = df
                    sources_used.append(enricher.pipeline)
        
        return enricher_dfs, sources_used

    async def _load_dependency_dataframes(
        self,
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[dict[str, pl.DataFrame], list[str]]:
        """Load DataFrames for successful dependencies."""
        if not dependencies or not dependency_results:
            return {}, []
        
        dependency_dfs: dict[str, pl.DataFrame] = {}
        sources_used: list[str] = []
        
        for dep in dependencies:
            result = dependency_results.get(dep.pipeline)
            if result and result.status == DependencyStatus.SUCCESS:
                df = await self._read_optional_merge_input(
                    pipeline=dep.pipeline,
                    table=dep.silver_table or f"silver/{dep.pipeline}",
                    role="dependency",
                )
                if df is not None:
                    dependency_dfs[dep.pipeline] = df
                    sources_used.append(dep.pipeline)
        
        return dependency_dfs, sources_used

    async def _read_silver_table(self, table: str) -> pl.DataFrame:
        """Read Silver table using delta_reader or fall back to storage."""
        if self._delta_reader is not None:
            # Read using Delta Lake
            arrow_table = await self._delta_reader.read_table(table)
            return pl.from_arrow(arrow_table)
        
        # Check if storage fallback is disabled (for test compatibility)
        if not hasattr(self, '_storage') or self._storage is None:
            raise RuntimeError(
                f"Reading Silver table {table} requires delta_reader or silver_reader"
            )
        
        # Fall back to storage adapter
        records = await self._storage.read_silver(table)
        if not records:
            return pl.DataFrame()
        return pl.from_dicts(records)


__all__ = ["_MergeInputLoaderMixin", "_PreparedSeedDataframe"]