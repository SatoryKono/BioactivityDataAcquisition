"""Protocol contracts for Gold writer support helpers."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.ports import (
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.domain.types import GoldRecord, ScdConfig
from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext,
    GoldWritePostwriteContext,
    GoldWriteRequest,
    PreparedGoldWriteContext,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.models.metadata import GoldMetadata

__all__ = [
    "_GoldWriterHost",
    "_ResolvedSchema",
    "_SchemaBuilder",
]


class _GoldMetadataHost(Protocol):
    """Required metadata dependencies initialized by the concrete writer."""

    logger: LoggerPort
    _metadata_writer: MetadataWriterPort
    _metadata_coordinator: MetadataCoordinatorPort | None
    _lineage_store: LineageStorePort | None
    _metrics: MetricsPort | None
    _transform_version: str | None
    _flat_structure: bool
    _transform_steps: tuple[str, ...]

    def _load_gold_writer_module(self) -> ModuleType: ...

    async def _run_in_executor[ResultT](
        self, func: Callable[..., ResultT], *args: object
    ) -> ResultT: ...

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


class _SchemaBuilder(Protocol):
    """Protocol for schema objects exposing ``to_schema``."""

    def to_schema(self) -> object:
        """Materialize runtime schema representation."""
        ...


class _ResolvedSchema(Protocol):
    """Protocol for resolved schema objects exposing columns mapping."""

    columns: dict[str, object]


class _GoldWriterHost(Protocol):
    """Host contract needed by Gold write support helpers."""

    @property
    def logger(self) -> LoggerPort: ...

    @property
    def _contract_rollout_policy(self) -> ContractRolloutPolicy | None: ...

    async def _prepare_write_gold(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        contract_version: str | None = None,
    ) -> PreparedGoldWriteContext: ...

    async def _dispatch_write(self, context: GoldWriteDispatchContext) -> None: ...

    async def _post_write_gold(self, context: GoldWritePostwriteContext) -> None: ...

    async def _write_single_target(self, *, request: GoldWriteRequest) -> None: ...
