"""Metadata operations facade for Silver layer lineage, audit, and DQ writes."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.behavior.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    LoggerPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
)
from bioetl.infrastructure.storage.silver.metadata_operations import (
    _execute_silver_metadata_write,
)
from bioetl.infrastructure.storage.silver.operations.metadata_write_facade import (
    _SilverMetadataWriteFacade,
)

__all__ = ["SilverMetadataOperations", "_execute_silver_metadata_write"]


@dataclass(frozen=True, slots=True)
class SilverMetadataOperations(
    _SilverMetadataWriteFacade,
):
    """Silver-layer metadata operations via composition."""

    _logger: LoggerPort
    _metrics: MetricsPort | None = None
    _audit: AuditPort | None = None
    _metadata_writer: MetadataWriterPort | None = None
    _metadata_coordinator: MetadataCoordinatorPort | None = None
    _lineage_store: LineageStorePort | None = None
    _dq_calculator: DQMetricsCalculator | None = None
    _host: object | None = None
