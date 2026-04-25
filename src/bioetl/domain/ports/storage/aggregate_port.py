"""Aggregate storage port combining all narrow storage protocols."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.ports.storage.bronze_port import BronzeStoragePort
from bioetl.domain.ports.storage.gold_port import GoldStoragePort
from bioetl.domain.ports.storage.lifecycle_port import StorageLifecyclePort
from bioetl.domain.ports.storage.merged_port import MergedStoragePort
from bioetl.domain.ports.storage.silver_port import SilverStoragePort
from bioetl.domain.ports.storage_maintenance import StorageMaintenancePort
from bioetl.domain.types import MetaDict

__all__ = ["StoragePort"]


@runtime_checkable
class StoragePort(
    BronzeStoragePort,
    SilverStoragePort,
    GoldStoragePort,
    MergedStoragePort,
    StorageMaintenancePort,
    StorageLifecyclePort,
    Protocol,
):
    """Aggregate storage port — union of all narrow layer-specific ports.

    Exists for backward compatibility. New consumers SHOULD depend on the
    narrowest port they need (for example ``SilverStoragePort`` instead of
    ``StoragePort``).
    """

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Preview Silver and optional Gold cleanup without deleting data."""
        ...
