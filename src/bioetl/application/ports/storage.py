"""Storage application ports migrated from composition (ADR-058)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from bioetl.domain.ports import MergedStoragePort, SilverStoragePort

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types import JsonDict

    CompositeSchemaProvider = object
    MetadataCoordinator = object
    PipelineYamlConfig = object
    Settings = object
    StorageContext = object


@runtime_checkable
class CompositeRuntimeStorageProtocol(MergedStoragePort, SilverStoragePort, Protocol):
    """Storage capabilities required by composite runtime bootstrap."""


@runtime_checkable
class CompositeMergeStorageProtocol(MergedStoragePort, SilverStoragePort, Protocol):
    """Storage capabilities required by composite merge assembly."""


@runtime_checkable
class SilverMergedWriteProtocol(Protocol):
    """Minimal bound-method contract for merged Silver writes."""

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[JsonDict],
        primary_keys: list[str] | None = None,
        *,
        schema: CompositeSchemaProvider | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...


@runtime_checkable
class GoldMergedWriteProtocol(Protocol):
    """Minimal bound-method contract for merged Gold writes."""

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[JsonDict],
        primary_keys: list[str] | None = None,
        *,
        schema: CompositeSchemaProvider,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...


@runtime_checkable
class StorageContextProtocol(Protocol):
    """Minimal storage context required for checkpoint-port creation."""

    @property
    def checkpoints_path(self) -> Path: ...


StorageContextLike = StorageContextProtocol
CompositeMergeStorage = CompositeMergeStorageProtocol


@runtime_checkable
class StorageFactoryProtocol(Protocol):
    """Structural contract shared by the lazy and concrete storage factories."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        audit: AuditPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
        pipeline_name: str | None = None,
    ) -> StorageContext: ...
