"""Storage ports for Medallion layer operations.

This package defines narrow, layer-specific storage ports following the
Interface Segregation Principle (ISP). Each port covers a single concern:

- BronzeStoragePort: Bronze layer write and cleanup
- SilverStoragePort: Silver layer write, read, and clear
- GoldStoragePort: Gold layer write and clear
- MergedStoragePort: Composite pipeline merged writes
- StorageMaintenancePort: Cross-layer maintenance (vacuum, optimize, archive, path)
- StorageLifecyclePort: Resource lifecycle (aclose, health_check)

Note:
    Lock validation is performed at Application layer (BatchWriter)
    per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O adapters.
"""

from __future__ import annotations

from bioetl.domain.ports.storage.bronze_port import BronzeStoragePort
from bioetl.domain.ports.storage.gold_port import GoldStoragePort
from bioetl.domain.ports.storage.lifecycle_port import StorageLifecyclePort
from bioetl.domain.ports.storage.merged_port import MergedStoragePort
from bioetl.domain.ports.storage.silver_port import (
    SilverStoragePort,
    SilverWriteRequest,
    coerce_silver_write_request,
)
from bioetl.domain.ports.storage_maintenance import StorageMaintenancePort

__all__ = [
    "BronzeStoragePort",
    "GoldStoragePort",
    "MergedStoragePort",
    "SilverStoragePort",
    "SilverWriteRequest",
    "StorageLifecyclePort",
    "StorageMaintenancePort",
    "coerce_silver_write_request",
]
