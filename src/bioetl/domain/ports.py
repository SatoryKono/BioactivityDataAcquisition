"""Port interfaces (Protocols) for dependency inversion.

Implements RULES.md §1.1 - Ports & Adapters architecture.
These interfaces define contracts for external systems like data sources,
storage, and other infrastructure components.
"""

from collections.abc import AsyncIterator, Iterable
from typing import Any, Protocol, runtime_checkable

from bioetl.domain.types import (
    BatchID,
    HealthStatus,
    RunID,
    Watermark,
)


@runtime_checkable
class DataSourcePort(Protocol):
    """Port for data sources (e.g., ChEMBL, PubChem)."""

    provider_name: str

    async def fetch(
        self,
        entity_type: str,
        watermark: Watermark | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records from the data source."""
        ...

    async def health_check(self) -> HealthStatus:
        """Check the health of the data source."""
        ...


@runtime_checkable
class StoragePort(Protocol):
    """Port for data storage (Bronze, Silver, Gold layers)."""

    def write_bronze(
        self,
        records: Iterable[bytes],
        provider: str,
        entity: str,
        date: Any,
        batch_id: BatchID,
    ) -> None:
        """Write raw records to Bronze layer."""
        ...

    def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        mode: str = "merge",
    ) -> None:
        """Write transformed records to Silver layer."""
        ...

    def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: str = "overwrite",
    ) -> None:
        """Write aggregated/validated records to Gold layer."""
        ...


@runtime_checkable
class LockPort(Protocol):
    """Port for distributed locking."""

    async def acquire(
        self,
        key: str,
        owner_id: RunID,
        ttl: int | None = None,
        wait: bool = False,
        wait_timeout: int = 300,
        exclusive: bool = False,
    ) -> bool:
        """Acquire a lock."""
        ...

    async def release(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Release a lock."""
        ...

    async def heartbeat(
        self,
        key: str,
        owner_id: RunID,
        exclusive: bool = False,
    ) -> bool:
        """Refresh a lock's TTL."""
        ...


@runtime_checkable
class CheckpointPort(Protocol):
    """Port for pipeline checkpointing."""

    def save(
        self,
        pipeline: str,
        watermark: Watermark,
        run_id: RunID,
        metadata: dict[str, Any],
    ) -> None:
        """Save a checkpoint."""
        ...

    def load(
        self,
        pipeline: str,
    ) -> tuple[Watermark, RunID, dict[str, Any]] | None:
        """Load a checkpoint."""
        ...

    def list_all(self) -> list[str]:
        """List all pipelines with checkpoints."""
        ...

    def delete(self, pipeline: str) -> None:
        """Delete a checkpoint."""
        ...


@runtime_checkable
class QuarantinePort(Protocol):
    """Port for quarantining failed records."""

    def write(
        self,
        pipeline: str,
        error_code: str,
        payload: dict[str, Any],
        bronze_batch_id: BatchID,
        # Allow optional args in implementation (Liskov) but enforce common ones here
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Write a record to quarantine."""
        ...

    def inspect(
        self,
        pipeline: str,
        limit: int = 10,
        error_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """Inspect quarantined records."""
        ...

    def get_stats(self, pipeline: str) -> dict[str, Any]:
        """Get quarantine statistics."""
        ...
