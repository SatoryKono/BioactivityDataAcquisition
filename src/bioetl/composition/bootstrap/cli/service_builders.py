"""Sanctioned service-graph builders for CLI/admin bootstrap flows."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from bioetl.application.core.lifecycle import (
    CheckpointCompatibilityService,
    CheckpointRuntimeService,
)
from bioetl.application.services.admin_runtime_api import QuarantineRuntimeService
from bioetl.application.services.audit_inspection_service import AuditInspectionService
from bioetl.application.services.checkpoint_service import CheckpointService
from bioetl.application.services.config_dq_service import (
    ConfigDQService,
    DQConfigLoaderProtocol,
    PipelineYamlConfigGetterProtocol,
)
from bioetl.application.services.config_service import ConfigService
from bioetl.application.services.observability_workflow_service import (
    ObservabilityWorkflowService,
)
from bioetl.application.services.quarantine_service import QuarantineService
from bioetl.domain.ports import DomainConfigMapperPort, SettingsLoaderPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter
from bioetl.infrastructure.time import SystemClock

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.effective_config_service import (
        EffectiveConfigService,
    )
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.domain.ports import (
        AuditPort,
        CheckpointPort,
        DomainConfigMapperPort,
        LoggerPort,
        MetricsPort,
        PipelineConfigLoaderPort,
        PipelineRegistryPort,
        QuarantinePort,
        RegistryAccessorPort,
        SettingsLoaderPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings

__all__ = [
    "build_cli_audit_inspection_service",
    "build_cli_checkpoint_runtime_service",
    "build_cli_checkpoint_service",
    "build_cli_config_service",
    "build_cli_observability_workflow_service",
    "build_cli_quarantine_runtime_service",
    "build_cli_quarantine_service",
]


def build_cli_config_service(
    *,
    registry: PipelineRegistryPort | None,
    logger_factory: Callable[[], LoggerPort],
    register_pipelines: Callable[[], object],
    default_registry_accessor: RegistryAccessorPort,
    settings_loader: SettingsLoaderPort,
    pipeline_config_loader: PipelineConfigLoaderPort,
    domain_config_mapper: DomainConfigMapperPort,
    pipeline_yaml_getter: PipelineYamlConfigGetterProtocol,
    dq_config_loader: DQConfigLoaderProtocol,
    effective_config_service_factory: Callable[[], EffectiveConfigService],
) -> ConfigService:
    """Build the CLI-facing ``ConfigService`` graph."""
    logger = logger_factory()
    effective_registry = registry
    if effective_registry is None:
        register_pipelines()
        effective_registry = default_registry_accessor()

    def _registry_accessor() -> PipelineRegistryPort:
        return effective_registry

    dq_service = ConfigDQService(
        logger=logger,
        _pipeline_yaml_getter=pipeline_yaml_getter,
        _dq_config_loader=dq_config_loader,
        _effective_config_service=effective_config_service_factory(),
    )
    return ConfigService(
        logger=logger,
        _settings_loader=settings_loader,
        _pipeline_config_loader=pipeline_config_loader,
        _domain_config_mapper=domain_config_mapper,
        _registry_accessor=_registry_accessor,
        _dq_service=dq_service,
    )


def build_cli_quarantine_runtime_service(
    *,
    pipeline_name: str,
    quarantine_port_factory: Callable[[], QuarantinePort],
) -> QuarantineRuntimeService:
    """Build the CLI quarantine runtime-service graph."""
    return QuarantineRuntimeService(
        quarantine_port=quarantine_port_factory(),
        pipeline_name=pipeline_name,
    )


def build_cli_quarantine_manager(
    *,
    pipeline_name: str,
    quarantine_port_factory: Callable[[], QuarantinePort],
) -> QuarantineRuntimeService:
    """Compatibility wrapper for the retired manager-style builder name."""
    return build_cli_quarantine_runtime_service(
        pipeline_name=pipeline_name,
        quarantine_port_factory=quarantine_port_factory,
    )


def build_cli_checkpoint_runtime_service(
    *,
    pipeline_name: str,
    run_id: RunID,
    checkpoint_port_factory: Callable[[str], CheckpointPort],
    logger_factory: Callable[[], LoggerPort],
    compatibility_service_factory: Callable[
        [LoggerPort], CheckpointCompatibilityService
    ],
) -> CheckpointRuntimeService:
    """Build the CLI checkpoint runtime-service graph."""
    logger = logger_factory()
    return CheckpointRuntimeService(
        checkpoint_port=checkpoint_port_factory(pipeline_name),
        logger=logger,
        pipeline_name=pipeline_name,
        run_id=run_id,
        resume=False,
        checkpoint_compatibility_service=compatibility_service_factory(logger),
    )


def build_cli_checkpoint_manager(
    *,
    pipeline_name: str,
    run_id: RunID,
    checkpoint_port_factory: Callable[[str], CheckpointPort],
    logger_factory: Callable[[], LoggerPort],
    compatibility_service_factory: Callable[
        [LoggerPort], CheckpointCompatibilityService
    ],
) -> CheckpointRuntimeService:
    """Compatibility wrapper for the retired manager-style builder name."""
    return build_cli_checkpoint_runtime_service(
        pipeline_name=pipeline_name,
        run_id=run_id,
        checkpoint_port_factory=checkpoint_port_factory,
        logger_factory=logger_factory,
        compatibility_service_factory=compatibility_service_factory,
    )


def build_cli_checkpoint_service(
    *,
    settings: Settings,
    logger_factory: Callable[[], LoggerPort],
    metrics_resolver: Callable[..., MetricsPort],
    tracing_resolver: Callable[..., TracingPort],
) -> CheckpointService:
    """Build the global CLI checkpoint administration service graph."""
    return CheckpointService(
        checkpoint_port=LocalCheckpointAdapter(
            base_path=settings.checkpoint_path,
            pipeline_name="",
        ),
        logger=logger_factory(),
        metrics=metrics_resolver(metrics=None, settings=settings),
        tracer=tracing_resolver(
            tracer=None,
            settings=settings,
            service_name="bioetl.checkpoint_admin",
        ),
    )


def build_cli_audit_inspection_service(
    *,
    settings: Settings,
    logger_factory: Callable[[], LoggerPort],
    metrics_resolver: Callable[..., MetricsPort],
    tracing_resolver: Callable[..., TracingPort],
    audit_port_factory: Callable[..., AuditPort],
) -> AuditInspectionService:
    """Build the CLI audit inspection service graph."""
    logger = logger_factory()
    audit_port = audit_port_factory(
        settings=settings,
        logger=logger,
        metrics=metrics_resolver(metrics=None, settings=settings),
        tracing=tracing_resolver(
            tracer=None,
            settings=settings,
            service_name="bioetl.audit_admin",
        ),
    )
    return AuditInspectionService(audit_port=audit_port)


def build_cli_observability_workflow_service(
    *,
    settings: Settings,
    checkpoint_service_factory: Callable[[], CheckpointService],
    audit_service_factory: Callable[[], AuditInspectionService],
    run_manifest_service_factory: Callable[[], RunManifestInspectionService],
    lineage_service_factory: Callable[[], LineageInspectionService],
    quarantine_service_factory: Callable[[], QuarantineService],
    tracing_resolver: Callable[..., TracingPort],
) -> ObservabilityWorkflowService:
    """Build the CLI diagnostics workflow service graph."""
    return ObservabilityWorkflowService(
        audit_service=audit_service_factory(),
        checkpoint_service=checkpoint_service_factory(),
        run_manifest_service=run_manifest_service_factory(),
        lineage_service=lineage_service_factory(),
        quarantine_service=quarantine_service_factory(),
        tracer=tracing_resolver(
            tracer=None,
            settings=settings,
            service_name="bioetl.diagnostics",
        ),
    )


def build_cli_quarantine_service(
    *,
    settings: Settings,
    quarantine_port_factory: Callable[[], QuarantinePort],
    logger_factory: Callable[[], LoggerPort],
    metrics_resolver: Callable[..., MetricsPort],
    tracing_resolver: Callable[..., TracingPort],
    clock_factory: Callable[[], SystemClock] = SystemClock,
) -> QuarantineService:
    """Build the CLI quarantine administration service graph."""
    return QuarantineService(
        quarantine_port=quarantine_port_factory(),
        logger=logger_factory(),
        clock=clock_factory(),
        metrics=metrics_resolver(metrics=None, settings=settings),
        tracer=tracing_resolver(
            tracer=None,
            settings=settings,
            service_name="bioetl.quarantine_admin",
        ),
    )
