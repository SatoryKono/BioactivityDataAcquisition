"""Protocol contracts for Gold writer support helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from pandera.polars import DataFrameSchema

from bioetl.domain.types import GoldRecord, ScdConfig

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

    logger: Any  # Any: facade host may provide structlog-like or test-double logger implementations.
    _contract_rollout_policy: (
        Any  # Any: rollout policy is runtime-wired and only duck-typed at this seam.
    )

    async def _prepare_write_gold(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
    ) -> object: ...

    async def _dispatch_write(self, context: object) -> None: ...

    async def _post_write_gold(self, context: object) -> None: ...

    async def _write_single_target(self, *, request: object) -> None: ...
