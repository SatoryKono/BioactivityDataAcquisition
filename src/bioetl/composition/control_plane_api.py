"""Public control-plane composition API."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.core.lifecycle.checkpoint_manager import (
        CheckpointRuntimeService,
    )
    from bioetl.application.services.audit_inspection_service import (
        AuditInspectionService,
    )
    from bioetl.application.services.config_service import ConfigService
    from bioetl.application.services.control_plane.forensic_diff_service import (
        ForensicRunDiffService,
    )
    from bioetl.application.services.control_plane.run_manifest_inspection_service import (
        RunManifestInspectionService,
    )
    from bioetl.application.services.control_plane.workflow_execution_service import (
        WorkflowExecutionService,
    )
    from bioetl.application.services.control_plane.workflow_inspection_service import (
        WorkflowInspectionService,
    )
    from bioetl.application.services.export_service import ExportService
    from bioetl.application.services.lineage.lineage_inspection_service import (
        LineageInspectionService,
    )
    from bioetl.application.services.lock_service import LockService
    from bioetl.composition.registry_api import PipelineRegistry
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecycleApplyResult,
        ControlPlaneArtifactLifecyclePlan,
        ControlPlaneArtifactLifecyclePolicy,
    )
    from bioetl.domain.workflow import WorkflowConfig

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

    def get_lineage_service() -> LineageInspectionService: ...

    def get_lock_service() -> LockService: ...

    def get_run_manifest_service() -> RunManifestInspectionService: ...

    def get_workflow_execution_service(
        registry: PipelineRegistry | None = None,
    ) -> WorkflowExecutionService: ...

    def get_workflow_inspection_service() -> WorkflowInspectionService: ...

    def load_workflow_config(name: str) -> WorkflowConfig: ...


__all__ = [
    "bootstrap_control_plane_lifecycle_store",
    "get_adr_service",
    "get_checkpoint_runtime_service",
    "get_config_service",
    "get_export_service",
    "get_forensic_run_diff_service",
    "get_lineage_service",
    "get_lock_service",
    "get_run_manifest_service",
    "get_workflow_execution_service",
    "get_workflow_inspection_service",
    "load_workflow_config",
]

_SERVICES_MODULE = "bioetl.composition._services"
_WORKFLOW_SERVICES_MODULE = "bioetl.composition._workflow_services"
_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_CLI_CONTROL_PLANE_LIFECYCLE_MODULE = (
    "bioetl.composition.bootstrap.cli.control_plane_lifecycle"
)
_PUBLIC_EXPORTS = {
    "bootstrap_control_plane_lifecycle_store": _CLI_CONTROL_PLANE_LIFECYCLE_MODULE,
    "get_adr_service": _SERVICES_MODULE,
    "get_checkpoint_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_config_service": _SERVICES_MODULE,
    "get_export_service": _SERVICES_MODULE,
    "get_forensic_run_diff_service": _SERVICES_MODULE,
    "get_lineage_service": _SERVICES_MODULE,
    "get_lock_service": _SERVICES_MODULE,
    "get_run_manifest_service": _SERVICES_MODULE,
    "get_workflow_execution_service": _WORKFLOW_SERVICES_MODULE,
    "get_workflow_inspection_service": _WORKFLOW_SERVICES_MODULE,
    "load_workflow_config": _WORKFLOW_SERVICES_MODULE,
}


def __getattr__(name: str) -> object:
    """Resolve control-plane exports lazily to avoid CLI import fan-out."""
    module_name = _PUBLIC_EXPORTS.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Expose lazy exports to introspection and wildcard imports."""
    return sorted(set(globals()) | set(__all__))
