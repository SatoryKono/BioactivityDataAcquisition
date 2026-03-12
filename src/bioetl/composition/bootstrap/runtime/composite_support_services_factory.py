"""Factory for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.aggregator import EnricherAggregatorService
from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.application.composite.column_priority_orderer import (
    ColumnPriorityOrdererService,
)
from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.cross_validator import (
    EnrichmentCrossValidationService,
)
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
from bioetl.application.composite.join_execution import JoinExecutorService, JoinHow
from bioetl.application.composite.join_key_resolution import JoinKeyResolverService
from bioetl.application.composite.join_planner import JoinPlannerService
from bioetl.application.composite.join_planner_helpers import (
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
)
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import LoggerPort, QuarantinePort
    from bioetl.infrastructure.config import Settings


@dataclass(slots=True)
class CompositeSupportServices:
    """Bundle of support services required by CompositePipelineRunner."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService
    merger: MergeService
    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


@dataclass(slots=True)
class _CompositeExecutionSupportServices:
    """Execution-facing services shared across composite runtime phases."""

    key_extractor: KeyExtractorService
    dependency_coordinator: DependencyCoordinatorService
    coordinator: EnrichmentCoordinatorService


@dataclass(slots=True)
class _CompositeRuntimeManagementServices:
    """Runtime management services that do not participate in merge wiring."""

    checkpoint_manager: CompositeCheckpointService
    dq_report_service: DQReportService
    fsm_state_helper: FSMStateHelperService
    quarantine_port: QuarantinePort | None


@dataclass(slots=True)
class _CompositeMergeDependencies:
    """Typed bundle for merge-specific collaborators assembled in composition."""

    deduplicator: EnricherDeduplicatorService
    aggregator: EnricherAggregatorService
    renamer: ColumnRenamerService
    orderer: ColumnOrdererService
    priority_orderer: ColumnPriorityOrdererService
    coalesce_policy: CoalescePolicyService
    conflict_resolver: ConflictResolverService
    join_planner: JoinPlannerService


class CompositeSupportServicesFactory:
    """Build support services used by composite runtime orchestration."""

    _NORMALIZE_JOIN_KEYS: frozenset[str] = frozenset({"doi", "pmid", "pmc_id"})
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

    def __init__(
        self,
        *,
        config: CompositeConfig,
        runtime: CompositeRuntimeConfig,
        settings: Settings,
        logger: LoggerPort,
        storage: Any,  # Any: storage adapter is concrete infra object implementing StoragePort
        run_id: str,
        resolve_gold_schema: Callable[[str], type | None],
        load_field_group_registry: Callable[
            [str, LoggerPort], FieldGroupRegistry | None
        ],
        create_dq_report_service: Callable[[LoggerPort, Settings], DQReportService],
        checkpoint_manager_cls: type[
            CompositeCheckpointService
        ] = CompositeCheckpointService,
    ) -> None:
        """Initialise the factory with composite run context and injectable callables.

        Stores all dependencies as private attributes so that ``build()`` can
        construct the full ``CompositeSupportServices`` bundle without requiring
        additional arguments. Injectable callables (``resolve_gold_schema``,
        ``load_field_group_registry``, ``create_dq_report_service``) allow the
        factory to remain testable without importing concrete infrastructure types
        at class level. Part of the composition layer for ADR-026.

        Args:
            config: Parsed domain ``CompositeConfig`` containing merge, enricher,
                dependency, DQ, and cross-validation settings.
            runtime: Immutable composite runtime options (resume flag,
                concurrency settings).
            settings: Global infrastructure settings supplying paths and feature
                flags (e.g. ``data_dir``).
            logger: Structured logger forwarded to all constructed services.
            storage: Storage adapter implementing ``StoragePort``; typed as ``Any``
                because it is a concrete infrastructure object injected from the
                composition root.
            run_id: Unique string identifier for this composite pipeline run;
                embedded in checkpoint paths and FSM state.
            resolve_gold_schema: Callable that accepts a composite pipeline name and
                returns the corresponding Pandera ``DataFrameModel`` class or ``None``.
            load_field_group_registry: Callable that accepts a composite pipeline name
                and a ``LoggerPort`` and returns a configured ``FieldGroupRegistry``
                or ``None``.
            create_dq_report_service: Callable that accepts a ``LoggerPort`` and
                ``Settings`` and returns a ``DQReportService`` instance.
            checkpoint_manager_cls: ``CompositeCheckpointService`` class (or
                compatible subclass) used to create the checkpoint manager; allows
                injection of a test double.
        """
        self._config = config
        self._runtime = runtime
        self._settings = settings
        self._logger = logger
        self._storage = storage
        self._run_id = run_id
        self._resolve_gold_schema = resolve_gold_schema
        self._load_field_group_registry = load_field_group_registry
        self._create_dq_report_service = create_dq_report_service
        self._checkpoint_manager_cls = checkpoint_manager_cls

    def build(self) -> CompositeSupportServices:
        """Build and return support service bundle.

        Returns:
            CompositeSupportServices bundle with all services required by CompositePipelineRunner.
        """
        delta_reader = self._create_delta_reader()
        execution_services = self._build_execution_support_services(delta_reader)
        field_group_registry = self._load_field_group_registry_for_composite()
        cross_validator = self._create_cross_validator()
        merger = self._create_merge_service(
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
        )
        runtime_management_services = self._build_runtime_management_services()

        return CompositeSupportServices(
            key_extractor=execution_services.key_extractor,
            dependency_coordinator=execution_services.dependency_coordinator,
            coordinator=execution_services.coordinator,
            merger=merger,
            checkpoint_manager=runtime_management_services.checkpoint_manager,
            dq_report_service=runtime_management_services.dq_report_service,
            fsm_state_helper=runtime_management_services.fsm_state_helper,
            quarantine_port=runtime_management_services.quarantine_port,
        )

    def _create_delta_reader(self) -> DeltaReader:
        silver_base_path = str(Path(self._settings.data_dir) / "output")
        return DeltaReader(
            base_path=silver_base_path,
            logger=self._logger,
        )

    def _build_execution_support_services(
        self,
        delta_reader: DeltaReader,
    ) -> _CompositeExecutionSupportServices:
        """Build execution-facing support services shared across runtime stages."""
        return _CompositeExecutionSupportServices(
            key_extractor=KeyExtractorService(
                delta_reader=delta_reader,
                logger=self._logger,
            ),
            dependency_coordinator=DependencyCoordinatorService(
                logger=self._logger,
                seed_key_resolver=create_seed_key_resolver(self._logger),
                chained_key_resolver=create_chained_key_resolver(self._logger),
                progress_service=DependencyProgressService(self._logger),
                result_service=DependencyResultService(self._logger),
                delta_reader=delta_reader,
            ),
            coordinator=EnrichmentCoordinatorService(
                logger=self._logger,
                dq_config=self._config.dq,
                max_concurrency=self._config.execution.max_concurrency,
            ),
        )

    def _build_runtime_management_services(
        self,
    ) -> _CompositeRuntimeManagementServices:
        """Build checkpoint, FSM, DQ, and quarantine runtime services."""
        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_composite_checkpoint_port,
        )

        checkpoint_storage = bootstrap_composite_checkpoint_port()
        return _CompositeRuntimeManagementServices(
            checkpoint_manager=self._checkpoint_manager_cls(
                composite_name=self._config.name,
                run_id=self._run_id,
                storage=checkpoint_storage,
                logger=self._logger,
                resume=self._runtime.resume,
            ),
            dq_report_service=self._create_dq_report_service(
                self._logger,
                self._settings,
            ),
            fsm_state_helper=FSMStateHelperService(
                config=self._config,
                logger=self._logger,
                run_id=self._run_id,
            ),
            quarantine_port=self._create_quarantine_port_if_enabled(),
        )

    def _load_field_group_registry_for_composite(
        self,
    ) -> FieldGroupRegistry | None:
        """Resolve optional field-group registry for the active composite."""
        return self._load_field_group_registry(self._config.name, self._logger)

    def _create_cross_validator(self) -> EnrichmentCrossValidationService | None:
        if not self._config.cross_validation.enabled:
            return None
        return EnrichmentCrossValidationService(
            config=self._config.cross_validation,
            logger=self._logger,
        )

    def _create_quarantine_port_if_enabled(self) -> QuarantinePort | None:
        if not self._config.cross_validation.enabled:
            return None

        from bioetl.composition.bootstrap.assembly.checkpoint import (
            bootstrap_quarantine_port,
        )

        return bootstrap_quarantine_port()

    def _create_merge_service(
        self,
        *,
        delta_reader: DeltaReader,
        field_group_registry: FieldGroupRegistry | None,
        cross_validator: EnrichmentCrossValidationService | None,
    ) -> MergeService:
        merge_dependencies = self._build_merge_dependencies()
        return MergeService(
            merge_config=self._config.merge,
            storage=self._storage,
            logger=self._logger,
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            gold_schema=self._resolve_gold_schema(self._config.name),
            deduplicator=merge_dependencies.deduplicator,
            aggregator=merge_dependencies.aggregator,
            renamer=merge_dependencies.renamer,
            orderer=merge_dependencies.orderer,
            priority_orderer=merge_dependencies.priority_orderer,
            coalesce_policy=merge_dependencies.coalesce_policy,
            conflict_resolver=merge_dependencies.conflict_resolver,
            join_planner=merge_dependencies.join_planner,
        )

    def _build_merge_dependencies(self) -> _CompositeMergeDependencies:
        """Assemble merge-specific collaborators used by MergeService."""
        merge_column_groups = getattr(self._config.merge, "column_groups", None)
        deduplicator = EnricherDeduplicatorService(self._logger)
        aggregator = EnricherAggregatorService(self._logger)
        renamer = ColumnRenamerService(self._logger)
        orderer = ColumnOrdererService(
            self._logger,
            column_groups=merge_column_groups if merge_column_groups else None,
        )
        priority_orderer = ColumnPriorityOrdererService(self._logger)
        coalesce_policy = CoalescePolicyService(self._logger, priority_orderer)
        conflict_resolver = ConflictResolverService(
            self._config.merge,
            self._logger,
            coalesce_policy,
        )
        join_key_resolver = JoinKeyResolverService(
            normalize_join_keys=self._NORMALIZE_JOIN_KEYS,
            parse_pipeline_name=parse_pipeline_name,
        )
        join_executor = JoinExecutorService(
            logger=self._logger,
            join_type_resolver=lambda: self._resolve_join_how(
                self._config.merge.strategy
            ),
        )
        dependency_joiner = DependencyJoinerService(
            logger=self._logger,
            deduplicator=deduplicator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
            field_alias_resolver=resolve_field_aliases_from_registry,
            join_key_resolver=join_key_resolver,
            join_executor=join_executor,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
        )
        join_planner = JoinPlannerService(
            merge_config=self._config.merge,
            logger=self._logger,
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            conflict_resolver=conflict_resolver,
            field_alias_resolver=resolve_field_aliases_from_registry,
            join_key_resolver=join_key_resolver,
            join_executor=join_executor,
            dependency_joiner=dependency_joiner,
        )
        return _CompositeMergeDependencies(
            deduplicator=deduplicator,
            aggregator=aggregator,
            renamer=renamer,
            orderer=orderer,
            priority_orderer=priority_orderer,
            coalesce_policy=coalesce_policy,
            conflict_resolver=conflict_resolver,
            join_planner=join_planner,
        )

    @staticmethod
    def _resolve_join_how(strategy: MergeStrategy) -> JoinHow:
        match strategy:
            case MergeStrategy.LEFT_OUTER:
                return "left"
            case MergeStrategy.INNER:
                return "inner"
            case MergeStrategy.UNION:
                return "full"
            case _:
                return "left"


__all__ = ["CompositeSupportServices", "CompositeSupportServicesFactory"]
