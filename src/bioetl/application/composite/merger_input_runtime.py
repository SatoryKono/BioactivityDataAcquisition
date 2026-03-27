"""Pure/runtime helpers for merge input loading."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass

import polars as pl

from bioetl.application.composite.join_planner_helpers import (
    infer_silver_table,
    table_path_to_name,
)
from bioetl.domain.composite.config import DependencyConfig, EnricherConfig
from bioetl.domain.composite.result import DependencyResult, EnrichmentResult
from bioetl.domain.types import BronzeRecord


@dataclass(frozen=True, slots=True)
class MergeInputLoadSpec:
    """Describes one optional merge input that should be loaded."""

    pipeline: str
    table: str
    role: str


@dataclass(frozen=True, slots=True)
class LoadedMergeInputsResult:
    """Loaded optional merge inputs plus the source pipelines that succeeded."""

    dataframes: dict[str, pl.DataFrame]
    sources: list[str]


@dataclass(frozen=True, slots=True)
class _PreparedSeedDataframe:
    """Prepared seed dataframe plus derived merge context."""

    seed_df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None


@dataclass(frozen=True, slots=True)
class _BoundLegacySilverReader:
    """Adapter for legacy storage objects that only expose ``read_silver``."""

    read_silver_fn: Callable[[str], Awaitable[list[BronzeRecord]]]

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]:
        """Delegate legacy Silver reads through the captured callable."""
        return await self.read_silver_fn(table_name)


def build_enricher_load_specs(
    *,
    enrichers: Sequence[EnricherConfig],
    enrichment_results: dict[str, EnrichmentResult],
) -> list[MergeInputLoadSpec]:
    """Build load specs for successful enrichers only."""
    specs: list[MergeInputLoadSpec] = []
    for enricher in enrichers:
        result = enrichment_results.get(enricher.pipeline)
        if result is None or not result.is_success:
            continue
        specs.append(
            MergeInputLoadSpec(
                pipeline=enricher.pipeline,
                table=enricher.silver_table or infer_silver_table(enricher.pipeline),
                role="enricher",
            )
        )
    return specs


def build_dependency_load_specs(
    *,
    dependencies: Sequence[DependencyConfig] | None,
    dependency_results: dict[str, DependencyResult] | None,
) -> list[MergeInputLoadSpec]:
    """Build load specs for successful dependency reads only."""
    if not dependencies or not dependency_results:
        return []
    specs: list[MergeInputLoadSpec] = []
    for dependency in dependencies:
        dep_result = dependency_results.get(dependency.pipeline)
        if dep_result is None or not dep_result.is_success or not dependency.silver_table:
            continue
        specs.append(
            MergeInputLoadSpec(
                pipeline=dependency.pipeline,
                table=dependency.silver_table,
                role="dependency",
            )
        )
    return specs


def build_prepared_seed_dataframe(
    *,
    seed_df: pl.DataFrame,
    effective_seed_pipeline: str | None,
) -> PreparedSeedDataframe:
    """Build the prepared seed dataframe result object."""
    return PreparedSeedDataframe(
        seed_df=seed_df,
        records_from_seed=len(seed_df),
        effective_seed_pipeline=effective_seed_pipeline,
    )


PreparedSeedDataframe = _PreparedSeedDataframe
BoundLegacySilverReader = _BoundLegacySilverReader


def coerce_polars_dataframe(result: pl.DataFrame | pl.Series) -> pl.DataFrame:
    """Normalize Polars read results to a DataFrame."""
    if isinstance(result, pl.Series):
        return result.to_frame()
    return result


def to_silver_table_name(path: str) -> str:
    """Map storage path to legacy logical table name."""
    return table_path_to_name(path)


__all__ = [
    "BoundLegacySilverReader",
    "LoadedMergeInputsResult",
    "MergeInputLoadSpec",
    "PreparedSeedDataframe",
    "build_dependency_load_specs",
    "build_enricher_load_specs",
    "build_prepared_seed_dataframe",
    "coerce_polars_dataframe",
    "to_silver_table_name",
]
