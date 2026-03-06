"""No-op memory monitor and metadata writer implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.models.metadata import (
        BronzeMetadata,
        GoldMetadata,
        SilverMetadata,
    )
    from bioetl.domain.ports.memory import MemoryStats


class NoOpMemoryMonitor:
    """No-op implementation of MemoryMonitorPort."""

    def get_memory_stats(self) -> MemoryStats:
        from bioetl.domain.ports.memory import MemoryStats

        return MemoryStats(
            used_mb=4096.0,
            available_mb=4096.0,
            total_mb=8192.0,
            percent_used=0.5,
            process_mb=256.0,
        )

    def is_under_pressure(self) -> bool:
        return False

    def get_recommended_batch_size(self, current_batch_size: int) -> int:
        return current_batch_size

    def estimate_batch_memory_mb(
        self,
        record_count: int,
        avg_record_size_bytes: int = 1024,
    ) -> float:
        overhead_factor = 2.5
        return (record_count * avg_record_size_bytes * overhead_factor) / (1024 * 1024)

    def calculate_max_batch_size(self, _avg_record_size_bytes: int = 1024) -> int:
        return 10000


class NoOpMetadataWriter:
    """No-op implementation of MetadataWriterPort."""

    async def write_bronze_metadata(
        self,
        base_path: str | Path,  # noqa: ARG002
        metadata: BronzeMetadata,  # noqa: ARG002
        *,
        provider: str | None = None,  # noqa: ARG002
        entity: str | None = None,  # noqa: ARG002
    ) -> str:
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
        return ""

    async def aclose(self) -> None:
        return None
