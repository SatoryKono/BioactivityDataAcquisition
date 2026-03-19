"""Post-write side effects for Bronze writer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.infrastructure.storage.bronze.metadata_operations import (
    BronzeMetadataWriteRequest,
    prepare_bronze_metadata_write,
)
from bioetl.infrastructure.storage.bronze.reporting_helpers import (
    BronzeAuditWriteRequest,
    build_bronze_audit_entry,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import BronzeMetadata, SourceMetadata
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
    )

    class _BronzeWriterSideEffectsHost:
        _audit: AuditPort | None
        _metadata_writer: MetadataWriterPort
        _metadata_coordinator: MetadataCoordinatorPort | None
        _flat_structure: bool
        base_path: Path
        logger: LoggerPort

        def _build_full_bronze_metadata(
            self,
            *,
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
            source_metadata: SourceMetadata | None,
        ) -> BronzeMetadata: ...

        async def _calculate_checksum(self, path: Path) -> str: ...


class BronzeWriterSideEffectsMixin:
    """Handles audit and metadata side effects after Bronze write."""

    async def _log_bronze_audit(
        self,
        *,
        run_id: RunID,
        ingestion_ts: datetime,
        relative_path: str,
        batch_id: BatchID,
        run_type: RunType,
        record_count: int,
        compressed_size: int,
        uncompressed_size: int,
        provider: str,
        entity: str,
    ) -> None:
        host = cast("_BronzeWriterSideEffectsHost", self)
        if not host._audit:
            return

        audit_entry = build_bronze_audit_entry(
            BronzeAuditWriteRequest(
                run_id=run_id,
                ingestion_ts=ingestion_ts,
                relative_path=relative_path,
                batch_id=batch_id,
                run_type=run_type,
                record_count=record_count,
                compressed_size=compressed_size,
                uncompressed_size=uncompressed_size,
                provider=provider,
                entity=entity,
            )
        )
        await host._audit.log_write(audit_entry)

    async def _maybe_write_bronze_metadata(
        self,
        *,
        run_id: RunID,
        run_type: RunType,
        provider: str,
        entity: str,
        batch_id: BatchID,
        record_count: int,
        compressed_size: int,
        relative_path: str,
        ingestion_ts: datetime,
        duration: float,
        source_metadata: SourceMetadata | None,
    ) -> None:
        """Create and persist Bronze metadata via coordinator or fallback."""
        host = cast("_BronzeWriterSideEffectsHost", self)
        prepared = prepare_bronze_metadata_write(
            host,
            BronzeMetadataWriteRequest(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                record_count=record_count,
                compressed_size=compressed_size,
                relative_path=relative_path,
                ingestion_ts=ingestion_ts,
                duration=duration,
                source_metadata=source_metadata,
            ),
        )
        await host._metadata_writer.write_bronze_metadata(
            base_path=prepared.metadata_base_path,
            metadata=prepared.metadata,
            provider=provider,
            entity=entity,
        )
        host.logger.debug(
            "bronze_metadata_written",
            metadata_path=str(
                prepared.metadata_base_path / f"{provider}_{entity}_metadata.yaml"
            ),
            run_id=str(run_id),
        )

    async def _build_bronze_write_result(
        self,
        *,
        prepared: Any,  # Any: local prepared payload type is owned by BronzeWriter module
        batch_id: BatchID,
        record_count: int,
        uncompressed_size: int,
        compressed_size: int,
        span: Any,  # Any: OpenTelemetry span interface is runtime-dependent
    ) -> BronzeWriteResult:
        """Build write result payload and include checksum."""
        host = cast("_BronzeWriterSideEffectsHost", self)
        span.set_attribute("record_count", record_count)
        span.set_attribute("compressed_size", compressed_size)
        checksum = await host._calculate_checksum(prepared.full_path)
        return BronzeWriteResult(
            batch_id=batch_id,
            relative_path=prepared.relative_path,
            absolute_path=str(prepared.full_path),
            record_count=record_count,
            compressed_size=compressed_size,
            uncompressed_size=uncompressed_size,
            checksum_blake2=checksum,
        )


__all__ = ["BronzeWriterSideEffectsMixin"]
