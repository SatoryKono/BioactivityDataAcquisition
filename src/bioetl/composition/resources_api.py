"""Public resource-management composition API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._lazy_exports import install_lazy_exports

if TYPE_CHECKING:
    from bioetl.composition._json_types import JsonDict
    from bioetl.composition._pipeline_execution import ArchiveOptions, VacuumOptions
    from bioetl.composition._resource_management import (
        CheckpointRuntimeServiceProtocol,
        CleanupPreviewProtocol,
        MedallionLifecycleServiceProtocol,
        QuarantineRuntimeServiceProtocol,
    )

__all__ = [
    "ArchiveOptions",
    "VacuumOptions",
    "archive_table",
    "get_checkpoint_runtime_service",
    "get_lifecycle_service",
    "get_quarantine_runtime_service",
    "inspect_quarantine",
    "list_checkpoints",
    "preview_cleanup",
    "vacuum_table",
]

_RESOURCE_MANAGEMENT_MODULE = "bioetl.composition._resource_management"
_PIPELINE_EXECUTION_MODULE = "bioetl.composition._pipeline_execution"
_PUBLIC_EXPORTS = {
    "ArchiveOptions": _PIPELINE_EXECUTION_MODULE,
    "VacuumOptions": _PIPELINE_EXECUTION_MODULE,
    "archive_table": _RESOURCE_MANAGEMENT_MODULE,
    "get_checkpoint_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_lifecycle_service": _RESOURCE_MANAGEMENT_MODULE,
    "get_quarantine_runtime_service": _RESOURCE_MANAGEMENT_MODULE,
    "inspect_quarantine": _RESOURCE_MANAGEMENT_MODULE,
    "list_checkpoints": _RESOURCE_MANAGEMENT_MODULE,
    "preview_cleanup": _RESOURCE_MANAGEMENT_MODULE,
    "vacuum_table": _RESOURCE_MANAGEMENT_MODULE,
}

if TYPE_CHECKING:

    async def archive_table(table: str, options: ArchiveOptions) -> int: ...

    def get_checkpoint_runtime_service(
        pipeline: str,
    ) -> CheckpointRuntimeServiceProtocol: ...

    def get_lifecycle_service() -> MedallionLifecycleServiceProtocol: ...

    def get_quarantine_runtime_service(
        pipeline: str,
    ) -> QuarantineRuntimeServiceProtocol: ...

    async def inspect_quarantine(
        pipeline: str,
        limit: int = 100,
    ) -> list[JsonDict]: ...

    async def list_checkpoints(pipeline: str) -> list[object]: ...

    async def preview_cleanup(pipeline: str) -> CleanupPreviewProtocol: ...

    async def vacuum_table(table: str, options: VacuumOptions) -> int: ...


install_lazy_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
    cache=True,
)
