"""Thin BronzeWriter wrappers around pure metadata builders."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.types import BatchID, JsonDict, RunID, RunType
from bioetl.infrastructure.storage.bronze.metadata_builders import (
    BronzeLineageMetadataRequest,
    BronzeMetadataPayloadRequest,
    build_bronze_lineage_metadata,
    build_bronze_metadata_payload,
    build_full_bronze_metadata,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata


class BronzeWriterMetadataMixin:
    """Mixin with bronze metadata construction helpers."""

    def _build_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        effective_ts: datetime,
        provider: str,
        entity: str,
        batch_id: BatchID,
    ) -> dict[str, str]:
        """Build metadata dict for lineage tracking.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            effective_ts: UTC ingestion timestamp to embed in the metadata.
            provider: Data provider name.
            entity: Entity type name.
            batch_id: Unique identifier for this write batch.

        Returns:
            Dictionary of string metadata fields for Bronze lineage tracking.
        """
        return build_bronze_lineage_metadata(
            BronzeLineageMetadataRequest(
                run_id=run_id,
                run_type=run_type,
                effective_ts=effective_ts,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
            )
        )

    def _build_full_bronze_metadata(
        self,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None = None,
    ) -> BronzeMetadata:
        """Build rich BronzeMetadata for sidecar file.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            provider: Data provider name.
            entity: Entity type name.
            batch_id: Unique identifier for this write batch.
            record_count: Number of records written.
            compressed_size: Compressed byte size of the written file.
            output_path: Relative path of the output file for metadata reference.
            started_at: UTC datetime when the write operation started.
            completed_at: UTC datetime when the write operation completed.
            duration_seconds: Total write duration in seconds.
            source_metadata: Optional provider metadata to embed in the sidecar.

        Returns:
            BronzeMetadata instance populated with runtime, pipeline, source, and output fields.
        """
        del batch_id
        return build_full_bronze_metadata(
            BronzeMetadataPayloadRequest(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                record_count=record_count,
                compressed_size=compressed_size,
                output_path=output_path,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                source_metadata=source_metadata,
            )
        )

    def _build_bronze_metadata_payload(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        record_count: int,
        compressed_size: int,
        output_path: str,
        started_at: datetime,
        completed_at: datetime,
        duration_seconds: float,
        source_metadata: SourceMetadata | None,
    ) -> JsonDict:  # Any: bronze metadata model fields are heterogeneous
        """Build Bronze metadata constructor payload.

        Args:
            run_id: Pipeline run identifier for lineage.
            run_type: Run classification (INCREMENTAL, BACKFILL, or REBUILD).
            provider: Data provider name.
            entity: Entity type name.
            record_count: Number of records written.
            compressed_size: Compressed byte size of the written file.
            output_path: Relative path of the output file for metadata reference.
            started_at: UTC datetime when the write operation started.
            completed_at: UTC datetime when the write operation completed.
            duration_seconds: Total write duration in seconds.
            source_metadata: Optional provider metadata to embed in the sidecar.

        Returns:
            Dictionary of constructor keyword arguments for BronzeMetadata.
        """
        return build_bronze_metadata_payload(
            BronzeMetadataPayloadRequest(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                record_count=record_count,
                compressed_size=compressed_size,
                output_path=output_path,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration_seconds,
                source_metadata=source_metadata,
            )
        )


__all__ = ["BronzeWriterMetadataMixin"]
