"""Post-write side effects for Bronze writer."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

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

        audit_entry = AuditEntry(
            run_id=run_id,
            timestamp=ingestion_ts,
            layer=AuditLayer.BRONZE,
            table_name=relative_path,
            operation=AuditOperation.WRITE,
            records_count=record_count,
            metadata={
                "provider": provider,
                "entity": entity,
                "batch_id": str(batch_id),
                "run_type": run_type.value,
                "compressed_bytes": compressed_size,
                "uncompressed_bytes": uncompressed_size,
            },
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
        bronze_metadata = self._create_bronze_metadata_payload(
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
        )
        metadata_base_path = self._resolve_bronze_metadata_base_path(provider, entity)
        await host._metadata_writer.write_bronze_metadata(
            base_path=metadata_base_path,
            metadata=bronze_metadata,
            provider=provider,
            entity=entity,
        )
        host.logger.debug(
            "bronze_metadata_written",
            metadata_path=str(
                metadata_base_path / f"{provider}_{entity}_metadata.yaml"
            ),
            run_id=str(run_id),
        )

    def _create_bronze_metadata_payload(
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
    ) -> BronzeMetadata:
        """Build Bronze metadata via coordinator when configured, else fallback."""
        host = cast("_BronzeWriterSideEffectsHost", self)
        completed_at = ingestion_ts + timedelta(seconds=duration)
        if host._metadata_coordinator is None:
            return host._build_full_bronze_metadata(
                run_id=run_id,
                run_type=run_type,
                provider=provider,
                entity=entity,
                batch_id=batch_id,
                record_count=record_count,
                compressed_size=compressed_size,
                output_path=relative_path,
                started_at=ingestion_ts,
                completed_at=completed_at,
                duration_seconds=duration,
                source_metadata=source_metadata,
            )

        from bioetl.domain.ports import BronzeMetadataInput

        bronze_input = BronzeMetadataInput(
            batch_id=batch_id,
            record_count=record_count,
            compressed_size=compressed_size,
            output_path=relative_path,
            started_at=ingestion_ts,
            completed_at=completed_at,
            source_metadata=source_metadata,
            query_string=source_metadata.query_string if source_metadata else None,
        )
        return host._metadata_coordinator.create_bronze_metadata(bronze_input)

    def _resolve_bronze_metadata_base_path(self, provider: str, entity: str) -> Path:
        """Resolve base path for Bronze metadata sidecar output."""
        host = cast("_BronzeWriterSideEffectsHost", self)
        if host._flat_structure:
            return host.base_path
        return host.base_path / provider / entity

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
