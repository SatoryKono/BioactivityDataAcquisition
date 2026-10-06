"""Factory for composite runtime support services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
    CompositeCheckpointService,
    DependencyCoordinatorService,
    EnrichmentCoordinatorService,
    FSMStateHelperService,
    KeyExtractorService,
    MergeService,
    validate_join_key_normalization_policies,
)
from bioetl.composition.bootstrap.composite_infrastructure_context import (
    CompositeInfrastructureContext,
)
from bioetl.composition.bootstrap.runtime.composite_execution_support_builder import (
    build_execution_support_services,
)
from bioetl.composition.bootstrap.runtime.composite_merge_service_builder import (
    SYSTEM_COLUMNS_TO_DROP,
    build_composite_merge_service,
)
from bioetl.composition.bootstrap.runtime.composite_runtime_management_builder import (
    build_runtime_management_services,
)
from bioetl.composition.bootstrap.runtime.composite_support_runtime_context import (
    resolve_composite_support_runtime_context,
)
from bioetl.composition.bootstrap.runtime.assay_replay_capture import (
    prepare_assay_replay,
)
from bioetl.composition.factories.storage import StorageBundle
from bioetl.infrastructure.storage.composite_replay_bundle import SUPPORTED_COMPOSITES

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.application.services.quality.dq_report_service import DQReportService
    from bioetl.domain.composite import CompositeConfig
    from bioetl.domain.composite.field_groups import FieldGroupRegistry
    from bioetl.domain.ports import (
        DeltaReaderPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
    )
    from bioetl.infrastructure.config.settings_api import Settings


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
    _SYSTEM_COLUMNS_TO_DROP = SYSTEM_COLUMNS_TO_DROP

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
        runtime_context = resolve_composite_support_runtime_context(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
            load_field_group_registry=self._load_field_group_registry,
        )
        execution_services = build_execution_support_services(
            config=self._config,
            logger=runtime_context.logger,
            delta_reader=runtime_context.delta_reader,
            clock=self._infra.clock,
        )
        storage = (
            self._infra.storage_for_manifest(runtime_context.control_plane_bundle)
            if self._infra.storage_for_manifest is not None
            else self._infra.storage
        )
        merge_reader: DeltaReaderPort = runtime_context.delta_reader
        execution_hook = None
        if self._config.name in SUPPORTED_COMPOSITES:
            candidate_storage: object = storage
            if not isinstance(candidate_storage, StorageBundle):
                raise TypeError("assay_replay_requires_storage_bundle")
            merge_reader, execution_hook = prepare_assay_replay(
                config=self._config,
                reader=merge_reader,
                storage=candidate_storage,
                settings=self._infra.settings,
                logger=runtime_context.logger,
                field_group_registry=runtime_context.field_group_registry,
            )
        merger = build_composite_merge_service(
            config=self._config,
            storage=storage,
            resolve_gold_schema=self._resolve_gold_schema,
            delta_reader=merge_reader,
            field_group_registry=runtime_context.field_group_registry,
            cross_validator=runtime_context.cross_validator,
            logger=runtime_context.logger,
            system_columns_to_drop=self._SYSTEM_COLUMNS_TO_DROP,
            normalization_policies=self._JOIN_KEY_NORMALIZATION_POLICIES,
            clock=self._infra.clock,
            execution_hook=execution_hook,
        )
        runtime_management_services = build_runtime_management_services(
            config=self._config,
            runtime=self._runtime,
            infra_context=self._infra,
            settings=self._infra.settings,
            logger=runtime_context.logger,
            run_id=self._infra.run_id,
            checkpoint_manager_cls=self._checkpoint_manager_cls,
            create_dq_report_service=self._create_dq_report_service,
            control_plane_bundle=runtime_context.control_plane_bundle,
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
            manifest_id=runtime_context.control_plane_bundle.manifest_id,
            run_ledger_service=runtime_context.control_plane_bundle.run_ledger_service,
        )


def build_support_services(
    *,
    config: CompositeConfig,
    runtime: CompositeRuntimeConfig,
    infra_context: CompositeInfrastructureContext,
    support_services_factory_cls: type[CompositeSupportServicesFactory],
    resolve_gold_schema_fn: Callable[[str], type | None],
    load_field_group_registry_fn: Callable[
        [str, LoggerPort], FieldGroupRegistry | None
    ],
    create_dq_report_service_fn: Callable[
        [LoggerPort, Settings, MetricsPort],
        DQReportService,
    ],
) -> CompositeSupportServices:
    """Build composite support service bundle consumed by runner facade.

    Args:
        config: CompositeConfig for this composite run.
        runtime: Runtime options (resume, concurrency, etc.).
        infra_context: Bundle of infrastructure primitives.
        support_services_factory_cls: Factory class that assembles the bundle.
        resolve_gold_schema_fn: Callable returning the Gold Pandera schema for
            a composite pipeline name, or None if not registered.
        load_field_group_registry_fn: Callable returning the FieldGroupRegistry
            for a composite pipeline name, or None.
        create_dq_report_service_fn: Callable returning a DQReportService
            given a logger and settings.

    Returns:
        CompositeSupportServices bundle with all services required by the runner.
    """
    return support_services_factory_cls(
        config=config,
        runtime=runtime,
        infra_context=infra_context,
        resolve_gold_schema=resolve_gold_schema_fn,
        load_field_group_registry=load_field_group_registry_fn,
        create_dq_report_service=create_dq_report_service_fn,
        checkpoint_manager_cls=CompositeCheckpointService,
    ).build()


__all__ = [
    "CompositeSupportServices",
    "CompositeSupportServicesFactory",
    "build_support_services",
]
