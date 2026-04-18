"""Join planning and execution for composite merge pipeline."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.enricher_join_execution import (
    build_prepared_enricher_join_context,
    execute_prepared_enricher_join,
)
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_planner_delegation_mixin import (
    JoinPlannerDelegationMixin,
)
from bioetl.application.composite.join_planner_helpers import (
    parse_pipeline_name,
)
from bioetl.application.composite.protocols import (
    DependencyJoinerProtocol,
    JoinExecutorProtocol,
    JoinKeyResolverProtocol,
)

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.domain.composite.config import (
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.ports import LoggerPort

__all__ = ["JoinHow", "JoinPlannerService", "JoinPreparationCollaborators"]


@dataclass(frozen=True, slots=True)
class JoinPreparationCollaborators:
    """Grouped preparation collaborators for JoinPlannerService."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    conflict_resolver: ConflictResolverService


class JoinPlannerService(JoinPlannerDelegationMixin):
    """Prepares and executes enricher/dependency joins with key normalization."""

    _SYSTEM_COLUMNS_TO_DROP: frozenset[str] = frozenset(
        {
            "_run_id",
            "_run_type",
            "_source_batch_id",
            "_ingestion_ts",
            "_dq_warn",
            "_dq_error",
            "_index",
            "_lookup_method",
            "_original_id",
            "_source",
        }
    )

    _parse_pipeline_name = staticmethod(parse_pipeline_name)

    def __init__(
        self,
        merge_config: MergeConfig,
        logger: LoggerPort,
        preparation: JoinPreparationCollaborators,
        join_key_resolver: JoinKeyResolverProtocol,
        join_executor: JoinExecutorProtocol,
        dependency_joiner: DependencyJoinerProtocol,
        field_alias_resolver: Callable[[str], dict[str, str] | None],
    ) -> None:
        """Initialise the join planner with explicit collaborator services.

        Required collaborators (``preparation``,
        ``join_key_resolver``, ``join_executor``,
        ``dependency_joiner``) must be provided explicitly. See ADR-026 for the
        composite join workflow design.

        Args:
            merge_config: Domain merge configuration containing join strategy,
                enricher list, and column-conflict policy.
            logger: Structured logger forwarded to all collaborator services.
            preparation: Grouped preparation services (deduplicator, aggregator,
                renamer, conflict_resolver) for normalising data frames.
            field_alias_resolver: Callable returning a field-alias mapping
                for a given pipeline name.
            join_key_resolver: ``JoinKeyResolverProtocol`` implementation for
                qualified/unqualified join-key resolution.
            join_executor: ``JoinExecutorProtocol`` implementation for Polars joins.
            dependency_joiner: ``DependencyJoinerProtocol`` implementation for
                dependency-specific join preparation and execution.
        """
        self._config = merge_config
        self._logger = logger
        self._deduplicator = preparation.deduplicator
        self._aggregator = preparation.aggregator
        self._renamer = preparation.renamer
        self._conflict_resolver = preparation.conflict_resolver
        self._field_alias_resolver = field_alias_resolver
        self._join_key_resolver = join_key_resolver
        self._join_executor = join_executor
        self._dependency_joiner = dependency_joiner

    async def apply_joins(
        self,
        seed_df: pl.DataFrame,
        enricher_dfs: dict[str, pl.DataFrame],
        enrichers: Sequence[EnricherConfig],
        seed_pipeline: str | None = None,
    ) -> pl.DataFrame:
        """Join successful enrichers to seed DataFrame.

        Args:
            seed_df: Base seed DataFrame to join enrichers into.
            enricher_dfs: Mapping from pipeline name to loaded enricher DataFrame.
            enrichers: Ordered enricher configurations defining join logic.
            seed_pipeline: Optional seed pipeline name for qualified key resolution.

        Returns:
            Merged DataFrame with all available enricher data joined to the seed frame.
        """
        await asyncio.sleep(0)
        merged = seed_df
        for enricher in enrichers:
            enricher_df = enricher_dfs.get(enricher.pipeline)
            if enricher_df is None:
                continue

            merged = self._merge_single_enricher(
                merged_df=merged,
                enricher_df=enricher_df,
                enricher=enricher,
                seed_pipeline=seed_pipeline,
            )
        return merged

    def _merge_single_enricher(
        self,
        *,
        merged_df: pl.DataFrame,
        enricher_df: pl.DataFrame,
        enricher: EnricherConfig,
        seed_pipeline: str | None,
    ) -> pl.DataFrame:
        return execute_prepared_enricher_join(
            prepared_context=build_prepared_enricher_join_context(
                merged_df=merged_df,
                enricher_df=enricher_df,
                enricher=enricher,
                seed_pipeline=seed_pipeline,
                deduplicator=self._deduplicator,
                aggregator=self._aggregator,
                renamer=self._renamer,
                logger=self._logger,
                field_alias_resolver=self._field_alias_resolver,
                join_key_resolver=self._join_key_resolver,
                resolve_join_key_names=self.resolve_join_key_names,
                drop_system_columns=self.drop_system_columns,
            ),
            conflict_resolver=self._conflict_resolver,
            join_executor=self.execute_polars_join,
        )
