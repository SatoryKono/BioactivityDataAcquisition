"""Facade contracts and constants for the Bronze writer."""

from __future__ import annotations

from dataclasses import dataclass

import zstandard as zstd

from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    TracingPort,
)

BRONZE_WRITE_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    zstd.ZstdError,
)
BRONZE_REQUIRED_METADATA_FIELDS = (
    "ingestion_ts",
    "run_id",
    "run_type",
    "batch_id",
)


@dataclass(frozen=True, slots=True)
class BronzeWriterRuntimeServices:
    """Optional Bronze runtime collaborators grouped behind one local seam."""

    tracing: TracingPort | None
    audit: AuditPort | None
    metadata_writer: MetadataWriterPort
    save_metadata: bool
    metadata_coordinator: MetadataCoordinatorPort | None
    lineage_store: LineageStorePort | None = None


__all__ = [
    "BRONZE_REQUIRED_METADATA_FIELDS",
    "BRONZE_WRITE_ERRORS",
    "BronzeWriterRuntimeServices",
]
