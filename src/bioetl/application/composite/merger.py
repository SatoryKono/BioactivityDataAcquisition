"""Merge Service for composite pipelines. See ADR-026."""

from __future__ import annotations

__all__ = ["MergeService"]

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.join_planner_helpers import table_path_to_name
from bioetl.application.composite.merger_compat_mixin import MergeCompatibilityMixin
from bioetl.application.composite.merger_io_mixin import MergeIOMixin
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.composite.merger_orchestration import (
    execute_merge_workflow,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)

if TYPE_CHECKING:

    from bioetl.application.composite.aggregator import EnricherAggregatorService
    from bioetl.application.composite.coalesce_policy import CoalescePolicyService
    from bioetl.application.composite.column_orderer import ColumnOrdererService
    from bioetl.application.composite.column_priority_orderer import (
        ColumnPriorityOrdererService,
    )
    from bioetl.application.composite.column_renamer import ColumnRenamerService
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidationService,
    )
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.join_planner import JoinPlannerService
    from bioetl.domain.composite.config import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import DeltaReaderPort, LoggerPort, StoragePort


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    return table_path_to_name(path)


class MergeService(MergeIOMixin, MergeCompatibilityMixin, MergeMetricsRecorderMixin):
    """Facade/orchestrator for seed+dependency+enricher merge workflow."""

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: StoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidationService | None = None,
        gold_schema: Any | None = None,  # Any: Pandera DataFrameModel class or instance
        *,
        deduplicator: EnricherDeduplicatorService,
        aggregator: EnricherAggregatorService,
        renamer: ColumnRenamerService,
        orderer: ColumnOrdererService,
        priority_orderer: ColumnPriorityOrdererService,
        coalesce_policy: CoalescePolicyService,
        conflict_resolver: ConflictResolverService,
        join_planner: JoinPlannerService,
    ) -> None:
        """Initialise the MergeService with all required and optional collaborators.

        The ``MergeService`` acts as the central facade for the seed + enricher +
        dependency merge workflow described in ADR-026. All data-access and processing
        concerns are delegated to the injected collaborator services; this class is
        responsible only for orchestration and sequencing.

        Args:
            merge_config: Domain merge configuration (strategy, enricher list, column
                conflict policy, cross-validation settings).
            storage: ``StoragePort`` adapter used to persist merged Silver/Gold output.
            logger: Structured logger for progress and diagnostic output.
            delta_reader: Optional ``DeltaReaderPort`` for reading seed and enricher
                Silver tables; when ``None`` the service falls back to
                storage-based reads.
            field_group_registry: Optional registry mapping publication field names to
                semantic groups; enables Gold-layer column filtering and ordering.
            cross_validator: Optional service that validates consistency across
                enricher data sources after joining; ``None`` disables cross-validation.
            gold_schema: Optional Pandera ``DataFrameModel`` class used to validate
                the Gold-layer output schema; type is ``Any`` because it is a class
                reference rather than an instance.
            deduplicator: Service that removes duplicate rows from enricher DataFrames
                keyed on join fields.
            aggregator: Service that aggregates many-to-one enricher DataFrames before
                joining.
            renamer: Service that qualifies column names to the
                ``{provider}.{entity}.{field}`` convention.
            orderer: Service that applies semantic group-based column ordering to the
                merged output.
            priority_orderer: Service that resolves provider priority ordering for
                coalesced columns.
            coalesce_policy: Service that selects the winning value for columns
                present in multiple enrichers.
            conflict_resolver: Service that detects and resolves column-name conflicts
                between the seed frame and enricher frames.
            join_planner: Pre-wired service that executes enricher and dependency
                joins against the seed DataFrame.
        """
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._gold_schema = gold_schema

        self._deduplicator = deduplicator
        self._aggregator = aggregator
        self._renamer = renamer
        self._orderer = orderer
        self._priority_orderer = priority_orderer
        self._coalesce_policy = coalesce_policy
        self._conflict_resolver = conflict_resolver
        self._join_planner = join_planner

    async def merge(
        self,
        seed_table: str,
        enrichers: Sequence[EnricherConfig],
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
        dependencies: Sequence[DependencyConfig] | None = None,
        dependency_results: dict[str, DependencyResult] | None = None,
    ) -> MergeResult:
        """Merge seed, dependency, and enricher data into unified output.

        Args:
            seed_table: Silver table name for the seed pipeline.
            enrichers: Enricher configurations to join into the merged output.
            enrichment_results: Mapping from pipeline name to EnrichmentResult.
            run_id: Current run identifier used for tracing.
            seed_pipeline: Optional seed pipeline name for qualified key resolution.
            dependencies: Optional dependency configurations to join before enrichers.
            dependency_results: Optional mapping from pipeline name to DependencyResult.

        Returns:
            MergeResult with merged record counts, source provenance, cross-validation
            stats, quarantine payloads, and duration metrics.
        """
        return await execute_merge_workflow(
            self,
            seed_table=seed_table,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            run_id=run_id,
            seed_pipeline=seed_pipeline,
            dependencies=dependencies,
            dependency_results=dependency_results,
        )
