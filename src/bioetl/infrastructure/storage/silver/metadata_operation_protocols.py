"""Protocols for canonical Silver metadata write/finalization helpers."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.ports import (
    LineageStorePort,
    MetadataCoordinatorPort,
    MetricsPort,
)
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics

__all__ = [
    "_SilverMetadataWriteHostProtocol",
    "_SilverWriteFinalizationHostProtocol",
]


class _SilverMetadataWriteHostProtocol(Protocol):
    """Typed host contract for Silver metadata sidecar stages."""

    @property
    def _metadata_coordinator(self) -> MetadataCoordinatorPort | None: ...

    @property
    def _lineage_store(self) -> LineageStorePort | None: ...

    @property
    def _metrics(self) -> MetricsPort | None: ...

    @property
    def _flat_structure(self) -> bool: ...

    @property
    def _transform_version(self) -> str | None: ...

    @property
    def _transform_steps(self) -> tuple[str, ...]: ...

    async def _get_delta_version(self, table_path: str) -> int | None: ...

    async def _write_silver_metadata_file(
        self,
        *,
        table_path: str,
        metadata: SilverMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None: ...


class _SilverWriteFinalizationHostProtocol(Protocol):
    """Host contract for DQ/version finalization before metadata persistence."""

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
        validation_errors: Sequence[str] | None = None,
    ) -> BatchDQMetrics: ...

    async def _get_delta_version(self, table_path: str) -> int | None: ...
