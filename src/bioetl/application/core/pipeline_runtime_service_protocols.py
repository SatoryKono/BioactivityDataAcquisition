"""Narrow runtime-facing service protocols for application-core execution paths."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from bioetl.domain.ports import (
    BronzeStoragePort,
    CheckpointPort,
    DataSourcePort,
    GoldStoragePort,
    LockPort,
    MergedStoragePort,
    QuarantinePort,
    SilverStoragePort,
    StorageLifecyclePort,
    StorageMaintenancePort,
)


@runtime_checkable
class PipelineStorageProtocol(
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageMaintenancePort,
    StorageLifecyclePort,
    Protocol,
):
    """Application DI contract for a full pipeline storage adapter."""

@runtime_checkable
class PipelineDataSourceServicesProtocol(Protocol):
    """Services surface required by extraction and source-metadata helpers."""

    data_source: DataSourcePort

@runtime_checkable
class PipelineHealthServicesProtocol(PipelineDataSourceServicesProtocol, Protocol):
    """Infrastructure services required by preflight health checks."""

    storage: PipelineStorageProtocol

@runtime_checkable
class PipelineRuntimeControlServicesProtocol(Protocol):
    """Runtime lifecycle services required to coordinate one managed run."""

    lock: LockPort
    checkpoint: CheckpointPort
    quarantine: QuarantinePort

@runtime_checkable
class PipelineManagedRuntimeServicesProtocol(
    PipelineHealthServicesProtocol,
    PipelineRuntimeControlServicesProtocol,
    Protocol,
):
    """Managed run services that participate in async startup/shutdown."""

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def aclose(self) -> None: ...

__all__ = [
    "PipelineDataSourceServicesProtocol",
    "PipelineHealthServicesProtocol",
    "PipelineManagedRuntimeServicesProtocol",
    "PipelineRuntimeControlServicesProtocol",
    "PipelineStorageProtocol",
]
