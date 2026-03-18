"""Internal builder bundles for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.aggregator import EnricherAggregator
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrderer,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.dependency_joiner import DependencyJoinerService
from bioetl.application.composite.dependency_key_resolvers import (
    create_chained_key_resolver,
    create_seed_key_resolver,
)
from bioetl.application.composite.dependency_progress_tracker import (
    DependencyProgressService,
)
from bioetl.application.composite.dependency_result_mapper import (
    DependencyResultService,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner import (
    JoinPlannerService,
    JoinPreparationCollaborators,
)
from bioetl.application.composite.join_planner_helpers import (
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.composition.bootstrap.assembly.checkpoint import (
    bootstrap_composite_checkpoint_port,
    bootstrap_quarantine_port,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.dataframe.polars_join_adapter import PolarsJoinAdapter

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.checkpoint import CompositeCheckpointService
    from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.ports import (
        CompositeCheckpointPort,
        LoggerPort,
        QuarantinePort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.storage.delta_reader import DeltaReader


@dataclass(slots=True)
class ExecutionSupportServicesBundle:
    """Execution-facing services shared across composite runtime phases."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService


@dataclass(slots=True)
class RuntimeManagementServicesBundle:
    """Checkpoint, FSM, DQ, and quarantine services for runtime orchestration."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


@dataclass(slots=True)
class MergeDependenciesBundle:
    """Merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregator
    renamer: ColumnRenamer
    orderer: ColumnOrderer
    priority_orderer: ColumnPriorityOrderer
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


def build_execution_support_services(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    delta_reader: DeltaReader,
) -> ExecutionSupportServicesBundle:
    """Build execution-facing support services shared across runtime stages."""
    return ExecutionSupportServicesBundle(
        key_extractor=KeyExtractorService(
            delta_reader=delta_reader,
            logger=logger,
        ),
        dependency_coordinator=DependencyCoordinatorService(
            logger=logger,
            seed_key_resolver=create_seed_key_resolver(logger),
            chained_key_resolver=create_chained_key_resolver(logger),
            progress_service=DependencyProgressService(logger),
            result_service=DependencyResultService(logger),
            delta_reader=delta_reader,
        ),
        coordinator=EnrichmentCoordinatorService(
            logger=logger,
            dq_config=config.dq,
            max_concurrency=config.execution.max_concurrency,
        ),
    )


def build_runtime_management_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    settings: Settings,
    logger: LoggerPort,
    run_id: str,
    checkpoint_manager_cls: type[CompositeCheckpointService],
    create_dq_report_service: Callable[[LoggerPort, Settings], DQReportService],
) -> RuntimeManagementServicesBundle:
    """Build checkpoint, FSM, DQ, and quarantine runtime services."""
    checkpoint_storage: CompositeCheckpointPort = bootstrap_composite_checkpoint_port()
    quarantine_port = (
        bootstrap_quarantine_port() if config.cross_validation.enabled else None
    )
    return RuntimeManagementServicesBundle(
        checkpoint_manager=checkpoint_manager_cls(
            composite_name=config.name,
            run_id=run_id,
            storage=checkpoint_storage,
            logger=logger,
            resume=runtime.resume,
        ),
        dq_report_service=create_dq_report_service(logger, settings),
        fsm_state_helper=FSMStateHelperService(
            config=config,
            logger=logger,
            run_id=run_id,
        ),
        quarantine_port=quarantine_port,
    )


def build_merge_dependencies(
    *,
    config: CompositeConfig,
    logger: LoggerPort,
    resolve_join_how: Callable[[MergeStrategy], JoinHow],
    normalize_join_keys: frozenset[str],
    system_columns_to_drop: frozenset[str],
) -> MergeDependenciesBundle:
    """Assemble merge-specific collaborators used by MergeService."""
    merge_column_groups = getattr(config.merge, "column_groups", None)
    deduplicator = EnricherDeduplicatorService(logger)
    aggregator = EnricherAggregator(logger)
    renamer = ColumnRenamer(logger)
    orderer = ColumnOrderer(
        logger,
        column_groups=merge_column_groups if merge_column_groups else None,
    )
    priority_orderer = ColumnPriorityOrderer(logger)
    coalesce_policy = CoalescePolicyService(logger, priority_orderer)
    conflict_resolver = ConflictResolverService(
        config.merge,
        logger,
        coalesce_policy,
    )
    join_key_resolver = JoinKeyResolverService(
        normalize_join_keys=normalize_join_keys,
        parse_pipeline_name=parse_pipeline_name,
    )
    join_executor = PolarsJoinAdapter(
        logger=logger,
        join_type_resolver=lambda: resolve_join_how(config.merge.strategy),
    )
    dependency_joiner = DependencyJoinerService(
        logger=logger,
        deduplicator=deduplicator,
        renamer=renamer,
        conflict_resolver=conflict_resolver,
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        system_columns_to_drop=system_columns_to_drop,
    )
    join_planner = JoinPlannerService(
        merge_config=config.merge,
        logger=logger,
        preparation=JoinPreparationCollaborators(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
        ),
        field_alias_resolver=resolve_field_aliases_from_registry,
        join_key_resolver=join_key_resolver,
        join_executor=join_executor,
        dependency_joiner=dependency_joiner,
    )
    return MergeDependenciesBundle(
        deduplicator=deduplicator,
        aggregator=aggregator,
        renamer=renamer,
        orderer=orderer,
        priority_orderer=priority_orderer,
        coalesce_policy=coalesce_policy,
        conflict_resolver=conflict_resolver,
        join_planner=join_planner,
    )
