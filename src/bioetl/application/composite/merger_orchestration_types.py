"""Typed request/context models for composite merge orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.application.composite.merger_post_join import MergePostJoinWorkflowContext

if TYPE_CHECKING:
    from collections.abc import Sequence

    import polars as pl

    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.application.composite.merger_input_mixin import _PreparedSeedDataframe
    from bioetl.domain.composite import DependencyConfig, EnricherConfig
    from bioetl.domain.composite.result import DependencyResult, EnrichmentResult
    from bioetl.domain.ports import ClockPort

__all__ = [
    "MergeExecutionContext",
    "MergeExecutionRequest",
    "MergeExecutionRequestSpec",
    "MergeInputContext",
    "MergeWorkflowContext",
]


@dataclass(frozen=True, slots=True)
class MergeInputContext:
    """Resolved seed, dependency, and enricher inputs for one merge run."""

    seed_df: pl.DataFrame
    records_from_seed: int
    effective_seed_pipeline: str | None
    sources_used: list[str]
    enricher_dfs: dict[str, pl.DataFrame]
    dependency_dfs: dict[str, pl.DataFrame]


@dataclass(frozen=True, slots=True)
class MergeExecutionRequestSpec:
    """Canonical request envelope for one composite merge execution."""

    seed_table: str
    enrichers: Sequence[EnricherConfig]
    enrichment_results: dict[str, EnrichmentResult]
    run_id: str
    metadata_timestamp: datetime | None = None
    seed_pipeline: str | None = None
    dependencies: Sequence[DependencyConfig] | None = None
    dependency_results: dict[str, DependencyResult] | None = None


@dataclass(frozen=True, slots=True)
class MergeExecutionContext:
    """Prepared execution state for one canonical merge/join run."""

    request: MergeExecutionRequestSpec
    started_at: datetime
    started_monotonic: float
    loaded_inputs: MergeInputContext


class MergeWorkflowContext(MergePostJoinWorkflowContext, Protocol):
    """Subset of MergeService API required by orchestration helpers."""

    @property
    def _clock(self) -> ClockPort | None: ...

    @property
    def _join_planner(self) -> JoinPlannerService: ...

    async def _prepare_seed_dataframe(
        self,
        seed_table: str,
        seed_pipeline: str | None,
    ) -> _PreparedSeedDataframe: ...

    async def _load_enricher_dataframes(
        self,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
    ) -> tuple[dict[str, pl.DataFrame], list[str]]: ...

    async def _load_dependency_dataframes(
        self,
        dependencies: Sequence[DependencyConfig] | None,
        dependency_results: dict[str, DependencyResult] | None,
    ) -> tuple[dict[str, pl.DataFrame], list[str]]: ...

    async def _apply_dependency_joins_if_needed(
        self,
        merged_df: pl.DataFrame,
        dependency_dfs: dict[str, pl.DataFrame],
        dependencies: Sequence[DependencyConfig] | None,
        seed_pipeline: str | None,
    ) -> pl.DataFrame: ...


MergeExecutionRequest = MergeExecutionRequestSpec
