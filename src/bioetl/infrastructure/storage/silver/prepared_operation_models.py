"""Prepared operation contexts and merged metadata write models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.merged_request_support import (
    _build_merged_write_request_from_mapping,
)
from bioetl.infrastructure.storage.silver.metadata_write_models import (
    _SilverMetadataWriteRequest,
)

__all__ = [
    "_PreparedSilverMetadataWriteOperation",
    "_PreparedSilverWriteFinalizationContext",
    "_ResolvedSilverMetadataContext",
    "_SilverMergedMetadataWriteRequest",
    "_build_silver_merged_metadata_write_request",
]


@dataclass(frozen=True, slots=True)
class _PreparedSilverMetadataWriteOperation:
    """Prepared Silver metadata operation carried into sidecar execution."""

    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: SilverMetadata
    lineage_fragment: LineageGraphFragment | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedSilverMetadataContext:
    """Shared provider/entity/version context for Silver metadata preparation."""

    provider_name: str
    entity_name: str
    version_after: int | None


@dataclass(frozen=True, slots=True)
class _PreparedSilverWriteFinalizationContext:
    """Prepared metadata/result context for one completed Silver write."""

    dq_metrics: BatchDQMetrics
    version_after: int | None
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class _SilverMergedMetadataWriteRequest:
    """Normalized request payload for one merged Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    completed_at: datetime | None = None
    run_id: str | None = None
    sources_used: list[str] | None = None


def _build_silver_merged_metadata_write_request(
    *,
    table_path: str,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str],
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
) -> _SilverMergedMetadataWriteRequest:
    """Build the canonical request for merged Silver metadata sidecar writes."""
    return _build_merged_write_request_from_mapping(
        _SilverMergedMetadataWriteRequest,
        locals(),
        table_path=table_path,
    )
