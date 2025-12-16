"""Unified storage adapter for Bronze/Silver/Gold."""

from collections.abc import Iterable
from typing import Any

from bioetl.domain.types import BatchID
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from domain/ports.py.
    """

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: DeltaWriter,
        gold_writer: DeltaWriter | GoldWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    async def write_bronze(
        self,
        records: Iterable[bytes],
        provider: str,
        entity: str,
        date: Any,
        batch_id: BatchID,
    ) -> None:
        """Write raw records to Bronze layer."""
        await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        mode: str = "merge",
    ) -> None:
        """Write transformed records to Silver layer."""
        await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: str = "overwrite",
    ) -> None:
        """Write aggregated records to Gold layer."""
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            mode=mode,
        )

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        pass  # Writers don't need explicit cleanup
