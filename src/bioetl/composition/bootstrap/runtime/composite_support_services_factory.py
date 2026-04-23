"""Factory for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    CompositeCheckpointService,
    DependencyCoordinatorService,
    EnrichmentCoordinatorService,
    EnrichmentCrossValidator,
    FSMStateHelperService,
    JoinHow,
    KeyExtractorService,
    MergeCollaboratorGroup,
    MergeService,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.composite_control_plane_builder import (
    bind_manifest_logger,
    build_composite_control_plane_bundle,
)
from bioetl.composition.bootstrap.runtime.composite_support_service_builders import (
    build_execution_support_services,
    build_merge_dependencies,
    build_runtime_management_services,
)
from bioetl.domain.composite.strategy import MergeStrategy
from bioetl.infrastructure.storage.delta_reader import DeltaReader

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.composite.config import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import (
        ClockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
    )
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
    manifest_id: str | None = None
    run_ledger_service: RunLedgerService | None = None


class CompositeSupportServicesFactory:
    """Build support services used by composite runtime orchestration."""

    _JOIN_KEY_NORMALIZATION_POLICIES = JOIN_KEY_NORMALIZATION_POLICIES
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
        infra_context: CompositeInfrastructureContext,
        resolve_gold_schema: Callable[[str], type | None],
        load_field_group_registry: Callable[
            [str, LoggerPort], FieldGroupRegistry | None
        ],
        create_dq_report_service: Callable[
            [LoggerPort, Settings, MetricsPort],
            DQReportService,
        ],
        checkpoint_manager_cls: type[
            CompositeCheckpointService
        ] = CompositeCheckpointService,
    ) -> None:
        """Store composite runtime dependencies and validate normalization policies."""
        validate_join_key_normalization_policies(
            config,
            self._JOIN_KEY_NORMALIZATION_POLICIES,
        )
        self._config = config
        self._runtime = runtime
        self._infra = infra_context
        self._resolve_gold_schema = resolve_gold_schema
        self._load_field_group_registry = load_field_group_registry
        self._create_dq_report_service = create_dq_report_service
        self._checkpoint_manager_cls = checkpoint_manager_cls

    def build(self) -> CompositeSupportServices:
        """Build and return the support-service bundle."""
        control_plane_bundle = build_composite_control_plane_bundle(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
        )
        logger = bind_manifest_logger(
            self._infra.logger,
            control_plane_bundle.manifest_id,
        )
        delta_reader = self._create_delta_reader(logger=logger)
        execution_services = build_execution_support_services(
            config=self._config,
            logger=logger,
            delta_reader=delta_reader,
            clock=self._infra.clock,
        )
        field_group_registry = self._load_field_group_registry(
            self._config.name,
            logger,
        )
        cross_validator = self._create_cross_validator(logger=logger)
        merger = self._create_merge_service(
            delta_reader=delta_reader,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            logger=logger,
            clock=self._infra.clock,
        )
        runtime_management_services = build_runtime_management_services(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
            settings=self._infra.settings,
            logger=logger,
            run_id=self._infra.run_id,
            checkpoint_manager_cls=self._checkpoint_manager_cls,
            create_dq_report_service=self._create_dq_report_service,
            control_plane_bundle=control_plane_bundle,
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
            manifest_id=control_plane_bundle.manifest_id,
            run_ledger_service=control_plane_bundle.run_ledger_service,
        )

    def _create_delta_reader(self, *, logger: LoggerPort) -> DeltaReader:
        silver_base_path = str(Path(self._infra.settings.data_dir) / "output")
        return DeltaReader(
            base_path=silver_base_path,
            logger=logger,
        )

    def _create_cross_validator(
        self,
        *,
        logger: LoggerPort,
    ) -> EnrichmentCrossValidator | None:
        if not self._config.cross_validation.enabled:
            return None
        return EnrichmentCrossValidator(
            config=self._config.cross_validation,
            logger=logger,
        )

    def _create_merge_service(
        self,
        *,
        delta_reader: DeltaReader,
        field_group_registry: FieldGroupRegistry | None,
        cross_validator: EnrichmentCrossValidator | None,
        logger: LoggerPort,
        clock: ClockPort | None = None,
    ) -> MergeService:
        merge_dependencies = build_merge_dependencies(
            config=self._config,
            logger=logger,
            resolve_join_how=self._resolve_join_how,
            normalization_policies=self._JOIN_KEY_NORMALIZATION_POLICIES,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
        )
        return MergeService(
            merge_config=self._config.merge,
            storage=self._infra.storage,
            logger=logger,
            delta_reader=delta_reader,
            silver_reader=self._infra.storage,
            field_group_registry=field_group_registry,
            cross_validator=cross_validator,
            gold_schema=self._resolve_gold_schema(self._config.name),
            clock=clock,
            collaborators=MergeCollaboratorGroup(
                deduplicator=merge_dependencies.deduplicator,
                aggregator=merge_dependencies.aggregator,
                renamer=merge_dependencies.renamer,
                orderer=merge_dependencies.orderer,
                priority_orderer=merge_dependencies.priority_orderer,
                order_service=merge_dependencies.order_service,
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
