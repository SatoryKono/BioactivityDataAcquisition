"""Aggregate storage port — backward-compatible facade combining all narrow ports."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Protocol, runtime_checkable

from bioetl.domain.ports.storage.silver_port import SilverWriteRequest
from bioetl.domain.types import (
    BatchID,
    BronzeRecord,
    GoldRecord,
    HealthStatus,
    MetaDict,
    RunID,
    RunType,
    ScdConfig,
)
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    from datetime import datetime

    from pandera.api.dataframe.container import DataFrameSchema

    from bioetl.domain.models.metadata import SourceMetadata

__all__ = ["StoragePort"]


@runtime_checkable
class StoragePort(Protocol):
    """Aggregate storage port — union of all narrow layer-specific ports.

    Exists for backward compatibility. New consumers SHOULD depend on the
    narrowest port they need (for example ``SilverStoragePort`` instead of
    ``StoragePort``).
    """

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeWriteResult: ...

    async def cleanup_bronze(
        self,
        cutoff_date: datetime,
        dry_run: bool = False,
    ) -> dict[str, int]: ...

    async def write_silver(
        self,
        request: SilverWriteRequest | str | None = None,
        *args: object,
        **kwargs: object,
    ) -> SilverWriteResult | None: ...

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[BronzeRecord]: ...

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int: ...

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: Any,  # Any: gold schemas may arrive as backend-specific validators
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
        *,
        scd_config: ScdConfig | None = None,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[Any]
        | None = None,  # Any: reference payload is backend-specific metadata
    ) -> None: ...

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int: ...

    async def write_silver_merged(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
    ) -> None: ...

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str] | None = None,
        *,
        completed_at: datetime | None = None,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        preserve_column_order: bool = False,
        schema: DataFrameSchema[Any]
        | None = None,  # Any: Pandera schema generic remains unconstrained here
    ) -> None: ...

    def get_table_path(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> Path: ...

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int: ...

    async def optimize(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> None: ...

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int: ...

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict: ...

    async def deduplicate_silver(
        self,
        table_name: str,
        primary_keys: list[str],
    ) -> int: ...

    async def clear_csv(self, table_name: str | None = None) -> int: ...

    def is_table_initialized(
        self,
        table_name: str,
        layer: Literal["silver", "gold"] = "silver",
    ) -> bool: ...

    async def clear_delta(self, table_name: str | None = None) -> int: ...

    def get_table_version(
        self,
        table_path: str,
        *,
        layer: Literal["silver", "gold"] = "silver",
    ) -> int | None: ...

    async def aclose(self) -> None: ...

    async def health_check(self) -> HealthStatus: ...
