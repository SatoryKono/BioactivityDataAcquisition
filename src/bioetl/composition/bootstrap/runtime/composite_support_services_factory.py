"""Factory for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bioetl.application.composite.checkpoint import CompositeCheckpointService
from bioetl.application.composite.cross_validator import (
    EnrichmentCrossValidationService,
)
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.merger import MergeCollaborators, MergeService
from bioetl.application.composite.runner_pkg import CompositeRuntimeConfig
from bioetl.composition.bootstrap.runtime.composite_support_service_builders import (
    build_execution_support_services,
    build_merge_dependencies,
    build_runtime_management_services,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.fsm_helper import FSMStateHelperService
    from bioetl.application.composite.key_extractor import KeyExtractorService
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
        execution_services = build_execution_support_services(
            config=self._config,
            logger=self._logger,
            delta_reader=delta_reader,
        )
        field_group_registry = self._load_field_group_registry(
            self._config.name,
            self._logger,
        )
        cross_validator = self._create_cross_validator()
        merger = self._create_merge_service(
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
        )
        runtime_management_services = build_runtime_management_services(
            config=self._config,
            runtime=self._runtime,
            settings=self._settings,
            logger=self._logger,
            run_id=self._run_id,
            checkpoint_manager_cls=self._checkpoint_manager_cls,
            create_dq_report_service=self._create_dq_report_service,
        )

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

    def _create_cross_validator(self) -> EnrichmentCrossValidationService | None:
        if not self._config.cross_validation.enabled:
            return None
        return EnrichmentCrossValidationService(
            config=self._config.cross_validation,
            logger=self._logger,
        )

    def _create_merge_service(
        self,
        *,
        delta_reader: DeltaReader,
        field_group_registry: FieldGroupRegistry | None,
        cross_validator: EnrichmentCrossValidationService | None,
    ) -> MergeService:
        merge_dependencies = build_merge_dependencies(
            config=self._config,
            logger=self._logger,
            resolve_join_how=self._resolve_join_how,
            normalize_join_keys=self._NORMALIZE_JOIN_KEYS,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
        )
        return MergeService(
            merge_config=self._config.merge,
            storage=self._storage,
            logger=self._logger,
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            gold_schema=self._resolve_gold_schema(self._config.name),
            collaborators=MergeCollaborators(
                deduplicator=merge_dependencies.deduplicator,
                aggregator=merge_dependencies.aggregator,
                renamer=merge_dependencies.renamer,
                orderer=merge_dependencies.orderer,
                priority_orderer=merge_dependencies.priority_orderer,
                coalesce_policy=merge_dependencies.coalesce_policy,
                conflict_resolver=merge_dependencies.conflict_resolver,
                join_planner=merge_dependencies.join_planner,
            ),
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
