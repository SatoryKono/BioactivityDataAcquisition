"""Protocol contracts for Gold writer support helpers."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.ports import LoggerPort
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

__all__ = [
    "_GoldWriterHost",
    "_ResolvedSchema",
    "_SchemaBuilder",
]


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
