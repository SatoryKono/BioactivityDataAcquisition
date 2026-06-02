"""Public control-plane composition API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.composition._lazy_exports import install_lazy_exports

if TYPE_CHECKING:

    class ControlPlaneArtifactLifecycleStoreProtocol(Protocol):
        def plan(
            self,
            policy: ControlPlaneArtifactLifecyclePolicy,
            *,
            dry_run: bool,
        ) -> ControlPlaneArtifactLifecyclePlan: ...

        def apply(
            self,
            plan: ControlPlaneArtifactLifecyclePlan,
        ) -> ControlPlaneArtifactLifecycleApplyResult: ...

    def get_adr_service() -> AuditInspectionService: ...

    def bootstrap_control_plane_lifecycle_store() -> (
        ControlPlaneArtifactLifecycleStoreProtocol
    ): ...

    def get_checkpoint_runtime_service(pipeline: str) -> CheckpointRuntimeService: ...

    def get_config_service() -> ConfigService: ...

    def get_export_service() -> ExportService: ...

    def get_forensic_run_diff_service() -> ForensicRunDiffService: ...

    def get_historical_replay_closure_service() -> HistoricalReplayClosureService: ...

    def get_historical_replay_corpus_service() -> HistoricalReplayCorpusService: ...

    def get_historical_replay_universe_service() -> HistoricalReplayUniverseService: ...

    def persist_historical_replay_closure_report(
        report: HistoricalReplayClosureReport,
    ) -> object: ...

    def persist_historical_replay_universe_report(
        report: HistoricalReplayUniverseClosureReport,
    ) -> object: ...

    def get_lineage_service() -> LineageInspectionService: ...

    def get_lock_service() -> LockService: ...

    def get_run_manifest_service() -> RunManifestInspectionService: ...

    def get_workflow_execution_service(
        registry: PipelineRegistry | None = None,
    ) -> WorkflowExecutionService: ...

    def get_workflow_runner_service(
        registry: PipelineRegistry | None = None,
    ) -> WorkflowRunnerService: ...

    def get_workflow_inspection_service() -> WorkflowInspectionService: ...

    def load_workflow_config(name: str) -> WorkflowConfig: ...


__all__ = [
    "bootstrap_control_plane_lifecycle_store",
    "get_adr_service",
    "get_checkpoint_runtime_service",
    "get_config_service",
    "get_export_service",
    "get_forensic_run_diff_service",
    "get_historical_replay_closure_service",
    "get_historical_replay_corpus_service",
    "get_historical_replay_universe_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "get_workflow_runner_service",
    "load_workflow_config",
    "persist_historical_replay_closure_report",
    "persist_historical_replay_universe_report",
]

_SERVICES_MODULE = "bioetl.composition._services"
_WORKFLOW_SERVICES_MODULE = "bioetl.composition._workflow_services"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_CLI_CONTROL_PLANE_LIFECYCLE_MODULE = (
    "bioetl.composition.bootstrap.cli.control_plane_lifecycle"
)
_RUN_MANIFEST_BOOTSTRAP_MODULE = "bioetl.composition.bootstrap.cli.run_manifest"
_PUBLIC_EXPORTS = {
    "bootstrap_control_plane_lifecycle_store": _CLI_CONTROL_PLANE_LIFECYCLE_MODULE,
    "get_adr_service": _SERVICES_MODULE,
    "get_checkpoint_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_config_service": _SERVICES_MODULE,
    "get_export_service": _SERVICES_MODULE,
    "get_forensic_run_diff_service": _SERVICES_MODULE,
    "get_historical_replay_closure_service": _SERVICES_MODULE,
    "get_historical_replay_corpus_service": _SERVICES_MODULE,
    "get_historical_replay_universe_service": _SERVICES_MODULE,
    "get_lineage_service": _SERVICES_MODULE,
    "get_lock_service": _SERVICES_MODULE,
    "persist_historical_replay_closure_report": _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "persist_historical_replay_universe_report": _RUN_MANIFEST_BOOTSTRAP_MODULE,
    "get_run_manifest_service": _SERVICES_MODULE,
    "get_workflow_execution_service": _WORKFLOW_SERVICES_MODULE,
    "get_workflow_runner_service": _WORKFLOW_SERVICES_MODULE,
    "get_workflow_inspection_service": _WORKFLOW_SERVICES_MODULE,
    "load_workflow_config": _WORKFLOW_SERVICES_MODULE,
}
install_lazy_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
    cache=True,
)
