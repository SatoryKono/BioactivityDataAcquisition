"""Merge service implementation for composite pipelines. See ADR-026."""

from __future__ import annotations

__all__ = ["MergeService"]

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.composite.join_planner_helpers import (
    extract_base_column,
    infer_pipeline_from_table,
    infer_silver_table,
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
    table_path_to_name,
)
from bioetl.application.composite.merger_collaborators import (
    MergeCollaboratorGroup,
)
from bioetl.application.composite.merger_input_mixin import (
    _MergeInputLoaderMixin,
)
from bioetl.application.composite.merger_io_mixin import MergeIOMixin
from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.composite.merger_orchestration import (
    MergeExecutionRequest,
    MergeWorkflowContext,
    build_merge_execution_request,
    execute_merge_request,
)
from bioetl.application.runtime_clock import resolve_runtime_clock
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)

if TYPE_CHECKING:
    from bioetl.application.composite.column_service import (
        ColumnPriorityOrderingPolicy,
    )
    from bioetl.application.composite.cross_validator import (
        EnrichmentCrossValidator,
    )
    from bioetl.domain.composite import (
        DependencyConfig,
        EnricherConfig,
        MergeConfig,
    )
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import (
        ClockPort,
        DeltaReaderPort,
        LoggerPort,
        MergedStoragePort,
        SilverStoragePort,
    )


def _path_to_table_name(path: str) -> str:
    """Convert a full path to a table name by stripping layer prefix."""
    return table_path_to_name(path)


class MergeService(
    MergeIOMixin,
    MergeMetricsRecorderMixin,
    _MergeInputLoaderMixin,
):
    """Facade/orchestrator for seed+dependency+enricher merge workflow."""

    _infer_silver_table = staticmethod(infer_silver_table)
    _infer_pipeline_from_table = staticmethod(infer_pipeline_from_table)
    _parse_pipeline_name = staticmethod(parse_pipeline_name)
    _get_field_aliases = staticmethod(resolve_field_aliases_from_registry)
    _extract_base_column = staticmethod(extract_base_column)
    _priority_orderer: ColumnPriorityOrderingPolicy | None

    def __init__(
        self,
        merge_config: MergeConfig,
        storage: MergedStoragePort,
        logger: LoggerPort,
        delta_reader: DeltaReaderPort | None = None,
        silver_reader: SilverStoragePort | None = None,
        field_group_registry: FieldGroupRegistry | None = None,
        cross_validator: EnrichmentCrossValidator | None = None,
        gold_schema: Any | None = None,  # Any: Pandera DataFrameModel class or instance
        clock: ClockPort | None = None,
        *,
        collaborators: MergeCollaboratorGroup,
    ) -> None:
        """Initialise the MergeService with all required and optional collaborators.

        The ``MergeService`` acts as the central facade for the seed + enricher +
        dependency merge workflow described in ADR-026. All data-access and processing
        concerns are delegated to the injected collaborator services; this class is
        responsible only for orchestration and sequencing.

        Args:
            merge_config: Domain merge configuration (strategy, enricher list, column
                conflict policy, cross-validation settings).
            storage: ``MergedStoragePort`` adapter used to persist merged Silver/Gold output.
            logger: Structured logger for progress and diagnostic output.
            delta_reader: Optional ``DeltaReaderPort`` for reading seed and enricher
                Silver tables.
            silver_reader: Optional ``SilverStoragePort`` used only as a
                compatibility fallback when ``delta_reader`` is not available.
            field_group_registry: Optional registry mapping publication field names to
                semantic groups; enables Gold-layer column filtering and ordering.
            cross_validator: Optional service that validates consistency across
                enricher data sources after joining; ``None`` disables cross-validation.
            gold_schema: Optional Pandera ``DataFrameModel`` class used to validate
                the Gold-layer output schema; type is ``Any`` because it is a class
                reference rather than an instance.
            collaborators: Dependency bundle containing the merge-time collaborator
                services.
        """
        self._config = merge_config
        self._storage = storage
        self._logger = logger
        self._delta_reader = delta_reader
        self._silver_reader = silver_reader
        self._field_group_registry = field_group_registry
        self._cross_validator = cross_validator
        self._gold_schema = gold_schema
        self._clock = resolve_runtime_clock(clock)

        self._deduplicator = collaborators.deduplicator
        self._aggregator = collaborators.aggregator
        self._renamer = collaborators.renamer
        self._order_service = collaborators.order_service
        self._priority_orderer = getattr(
            self._order_service,
            "_priority_orderer",
            None,
        )
        self._coalesce_policy = collaborators.coalesce_policy
        self._conflict_resolver = collaborators.conflict_resolver
        self._join_planner = collaborators.join_planner

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
        request = build_merge_execution_request(
            seed_table=seed_table,
            enrichers=enrichers,
            enrichment_results=enrichment_results,
            run_id=run_id,
            seed_pipeline=seed_pipeline,
            dependencies=dependencies,
            dependency_results=dependency_results,
        )
        return await self.execute_request(request)

    async def execute_request(
        self,
        request: MergeExecutionRequest,
    ) -> MergeResult:
        """Execute a canonical merge request envelope."""
        return await execute_merge_request(cast(MergeWorkflowContext, self), request)
