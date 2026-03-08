"""Aggregate storage port — backward-compatible facade combining all narrow ports."""

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
    narrowest port they need (e.g., ``SilverStoragePort`` instead of
    ``StoragePort``).

    See Also:
        BronzeStoragePort, SilverStoragePort, GoldStoragePort,
        MergedStoragePort, StorageMaintenancePort, StorageLifecyclePort.
    """

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> MetaDict:
        """Compatibility re-declaration for legacy StoragePort patch points.

        The authoritative contract lives on ``StorageMaintenancePort``.

        Args:
            silver_table: Name of the Silver table to preview cleanup for.
            gold_table: Optional name of the Gold table; defaults to None.

        Returns:
            MetaDict with preview information about what would be cleared.
        """
        ...

    ...
