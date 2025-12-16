"""Unified storage adapter for Bronze/Silver/Gold."""

from typing import Any

from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold."""

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: DeltaWriter,
        gold_writer: DeltaWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    def write_bronze(self, *args: Any, **kwargs: Any) -> Any:
        return self.bronze.write_bronze(*args, **kwargs)

    def write_silver(self, *args: Any, **kwargs: Any) -> None:
        return self.silver.write_silver(*args, **kwargs)

    def write_gold(self, *args: Any, **kwargs: Any) -> None:
        return self.gold.write_gold(*args, **kwargs)
