"""No-op memory monitor and metadata writer implementations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports.runtime import MemoryStats


class NoOpMemoryMonitor:
    """No-op implementation of MemoryMonitorPort."""

    def get_memory_stats(self) -> MemoryStats:
        """Return conservative fixed MemoryStats suitable for local-only deployment."""
        from bioetl.domain.ports.runtime import MemoryStats

        return MemoryStats(
            used_mb=4096.0,
            available_mb=4096.0,
            total_mb=8192.0,
            percent_used=0.5,
            process_mb=256.0,
        )

    def is_under_pressure(self) -> bool:
        """Return False — no-op monitor never reports memory pressure."""
        return False

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        """Return the current batch size unchanged — no memory-based adjustment.

        Args:
            current_batch_size: The current batch size requested by the caller.

        Returns:
            The same batch size with no modification.
        """
        return current_batch_size

    def estimate_batch_memory_mb(
        self,
        record_count: int,
        avg_record_size_bytes: int = 1024,
    ) -> float:
        """Estimate memory required for a batch using a fixed overhead factor.

        Args:
            record_count: Number of records in the batch.
            avg_record_size_bytes: Average size of each record in bytes. Defaults to 1024.

        Returns:
            Estimated memory usage in megabytes.
        """
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, _avg_record_size_bytes: int = 1024) -> int:
        """Return a fixed maximum batch size of 10000 records.

        Args:
            _avg_record_size_bytes: Average record size in bytes (ignored).

        Returns:
            Fixed maximum batch size.
        """
        return 10000


class NoOpMetadataWriter:
    """No-op implementation of MetadataWriterPort."""

    def attach_artifact_recorder(
        self,
        recorder: Callable[[str, str, dict[str, object] | None], object] | None,
    ) -> None:
        """Accept an artifact recorder and intentionally ignore it."""
        _ = recorder

    async def write_bronze_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: BronzeMetadata,  # noqa: ARG002
        *,
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """No-op implementation — discards Bronze metadata and returns empty string.

        Args:
            base_path: Base directory path for metadata output (ignored).
            metadata: Bronze layer metadata to write (ignored).
            provider: Optional provider name qualifier (ignored).
            entity: Optional entity type qualifier (ignored).

        Returns:
            Empty string.
        """
        del base_path, metadata, provider, entity
        await asyncio.sleep(0)
        return ""

    async def write_silver_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: SilverMetadata,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """No-op implementation — discards Silver metadata and returns empty string.

        Args:
            base_path: Base directory path for metadata output (ignored).
            metadata: Silver layer metadata to write (ignored).
            table_name: Optional Delta table name qualifier (ignored).
            flat_structure: Whether to use a flat directory structure (ignored).
            provider: Optional provider name qualifier (ignored).
            entity: Optional entity type qualifier (ignored).

        Returns:
            Empty string.
        """
        del base_path, metadata, table_name, flat_structure, provider, entity
        await asyncio.sleep(0)
        return ""

    async def finalize_silver_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
        dq_report_path: str | None = None,  # noqa: ARG002
        completed_at: datetime | None = None,  # noqa: ARG002
        delta_version_after: int | None = None,  # noqa: ARG002
    ) -> str | None:
        """No-op Silver finalization returns empty string when invoked."""
        del base_path, table_name, flat_structure, provider, entity
        del dq_report_path, completed_at, delta_version_after
        await asyncio.sleep(0)
        return ""

    async def write_gold_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: GoldMetadata,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
        """No-op implementation — discards Gold metadata and returns empty string.

        Args:
            base_path: Base directory path for metadata output (ignored).
            metadata: Gold layer metadata to write (ignored).
            table_name: Optional Delta table name qualifier (ignored).
            flat_structure: Whether to use a flat directory structure (ignored).
            provider: Optional provider name qualifier (ignored).
            entity: Optional entity type qualifier (ignored).

        Returns:
            Empty string.
        """
        del base_path, metadata, table_name, flat_structure, provider, entity
        await asyncio.sleep(0)
        return ""

    async def finalize_gold_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        *,
        table_name: str | None = None,  # noqa: ARG002
        flat_structure: bool = False,  # noqa: ARG002
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
        dq_report_path: str | None = None,  # noqa: ARG002
        completed_at: datetime | None = None,  # noqa: ARG002
    ) -> str | None:
        """No-op Gold finalization returns empty string when invoked."""
        del base_path, table_name, flat_structure, provider, entity
        del dq_report_path, completed_at
        await asyncio.sleep(0)
        return ""

    async def aclose(self) -> None:
        """No-op implementation of aclose — no resources to release."""
        await asyncio.sleep(0)
        return None
