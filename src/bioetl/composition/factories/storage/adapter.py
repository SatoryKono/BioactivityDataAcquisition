"""StorageAdapter - Unified storage adapter for Bronze/Silver/Gold layers.

Implements the narrow storage protocols from ``bioetl.domain.ports``.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.

Note:
    Lock validation is performed at Application layer (BatchWriter).
    Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

from typing import ClassVar

from bioetl.composition.factories.storage.clear_mixin import (
    StorageAdapterClearMixin,
)
from bioetl.composition.factories.storage.health_mixin import (
    StorageAdapterHealthMixin,
)
from bioetl.composition.factories.storage.maintenance_mixin import (
    StorageAdapterMaintenanceMixin,
)
from bioetl.composition.factories.storage.merged_mixin import (
    StorageAdapterMergedMixin,
)
from bioetl.composition.factories.storage.write_mixin import (
    StorageAdapterWriteMixin,
)
from bioetl.domain.contracts.gold.composite import (
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = ["StorageAdapter"]


class StorageAdapter(
    StorageAdapterWriteMixin,
    StorageAdapterMergedMixin,
    StorageAdapterClearMixin,
    StorageAdapterMaintenanceMixin,
    StorageAdapterHealthMixin,
):
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements the narrow storage protocols from ``bioetl.domain.ports``.
    Delegates to specialized writers for each layer.
    """

    _COMPOSITE_GOLD_SCHEMAS: ClassVar[
        JsonDict  # Any: record/metadata values are heterogeneous
    ] = {
        "composite/publication": CompositePublicationGoldSchema,
        "composite_publication": CompositePublicationGoldSchema,
        "composite/molecule": CompositeMoleculeGoldSchema,
        "composite_molecule": CompositeMoleculeGoldSchema,
    }

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: SilverWriter,
        gold_writer: GoldWriter,
    ):
        """Initialize StorageAdapter with injected layer writers.

        Args:
            bronze_writer: Writer for raw data ingestion into Bronze layer
                (zst-compressed JSONL files with optional JSON and metadata).
            silver_writer: Writer for transformed data into Silver layer
                (Delta Lake tables with schema enforcement and optional CSV export).
            gold_writer: Writer for aggregated/validated data into Gold layer
                (Delta Lake tables with Pandera validation and optional CSV export).
        """
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer
