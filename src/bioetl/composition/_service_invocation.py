"""Typed lazy invocation seam for composition service bootstrap owners."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, overload

if TYPE_CHECKING:
    from bioetl.composition._service_types import (
        AdrServicePort,
        AuditInspectionService,
        BronzeCleanupService,
        CheckpointService,
        ConfigService,
        ContractMigrationService,
        ExportService,
        ForensicRunDiffService,
        HealthService,
        HistoricalReplayClosureService,
        HistoricalReplayCorpusService,
        HistoricalReplayUniverseService,
        LineageInspectionService,
        LockService,
        MetricsService,
        ObservabilityWorkflowService,
        PipelineRunnerService,
        QuarantinePort,
        QuarantineService,
        RunManifestInspectionService,
        VacuumService,
    )
    from bioetl.composition.bootstrap.assembly.health_server import (
        HealthServerDependencies,
    )


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_adr_service"], *args: object, **kwargs: object
) -> AdrServicePort: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_audit_inspection_service"], *args: object, **kwargs: object
) -> AuditInspectionService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_bronze_cleanup_service"], *args: object, **kwargs: object
) -> BronzeCleanupService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_checkpoint_service"], *args: object, **kwargs: object
) -> CheckpointService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_config_service"], *args: object, **kwargs: object
) -> ConfigService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_contract_migration_service"],
    *args: object,
    **kwargs: object,
) -> ContractMigrationService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_export_service"], *args: object, **kwargs: object
) -> ExportService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_forensic_run_diff_service"],
    *args: object,
    **kwargs: object,
) -> ForensicRunDiffService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_historical_replay_closure_service"],
    *args: object,
    **kwargs: object,
) -> HistoricalReplayClosureService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_historical_replay_corpus_service"],
    *args: object,
    **kwargs: object,
) -> HistoricalReplayCorpusService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_historical_replay_universe_service"],
    *args: object,
    **kwargs: object,
) -> HistoricalReplayUniverseService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_health_server_dependencies"],
    *args: object,
    **kwargs: object,
) -> HealthServerDependencies: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_health_service"], *args: object, **kwargs: object
) -> HealthService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_lineage_service"], *args: object, **kwargs: object
) -> LineageInspectionService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_lock_service"], *args: object, **kwargs: object
) -> LockService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_metrics_service"], *args: object, **kwargs: object
) -> MetricsService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_observability_workflow_service"],
    *args: object,
    **kwargs: object,
) -> ObservabilityWorkflowService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_pipeline_runner_service"], *args: object, **kwargs: object
) -> PipelineRunnerService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_quarantine_adapter"], *args: object, **kwargs: object
) -> QuarantinePort: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_quarantine_service"], *args: object, **kwargs: object
) -> QuarantineService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_run_manifest_service"], *args: object, **kwargs: object
) -> RunManifestInspectionService: ...


@overload
def invoke_bootstrap(
    name: Literal["bootstrap_vacuum_service"], *args: object, **kwargs: object
) -> VacuumService: ...


def invoke_bootstrap(name: str, *args: object, **kwargs: object) -> object:
    """Resolve one bootstrap owner lazily and invoke it as a callable."""
    from bioetl.composition import _services

    bootstrap_fn = _services.resolve_bootstrap_attr(name)
    if not callable(bootstrap_fn):
        raise TypeError(f"Bootstrap export {name!r} is not callable")
    return bootstrap_fn(*args, **kwargs)
