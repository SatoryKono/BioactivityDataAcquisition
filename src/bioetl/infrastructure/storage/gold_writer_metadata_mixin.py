"""Metadata and audit helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.models.metadata import GoldMetadata
    from bioetl.domain.ports import (
        AuditPort,
        GoldMetadataInput,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
    )
    from bioetl.domain.types import GoldRecord, ScdConfig
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


class GoldWriterMetadataMixin:
    """Mixin containing audit and metadata sidecar write helpers."""

    logger: LoggerPort
    _audit: AuditPort | None
    _metadata_coordinator: MetadataCoordinatorPort | None
    _metadata_writer: MetadataWriterPort
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]
    _load_gold_writer_module: Callable[[], ModuleType]
    _run_in_executor: Callable[..., Awaitable[object]]

    async def _log_gold_audit(
        self,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
    ) -> None:
        """Log audit entry for Gold write operation."""
        from uuid import uuid4

        if ingestion_ts is not None:
            timestamp = ingestion_ts
        else:
            self.logger.warning(
                "audit_missing_ingestion_ts",
                table=table_name,
                mode=mode.value,
            )
            raise ValueError("ingestion_ts is required for audit logging")
        if run_id is not None:
            audit_run_id = run_id
        else:
            self.logger.warning(
                "audit_missing_run_id",
                table=table_name,
                mode=mode.value,
            )
            audit_run_id = RunID(uuid4())
        operation_map = {
            GoldWriteMode.OVERWRITE: AuditOperation.OVERWRITE,
            GoldWriteMode.APPEND: AuditOperation.APPEND,
            GoldWriteMode.SCD2: AuditOperation.MERGE,
        }
        operation = operation_map[mode]
        audit_entry = AuditEntry(
            run_id=audit_run_id,
            timestamp=timestamp,
            layer=AuditLayer.GOLD,
            table_name=table_name,
            operation=operation,
            records_count=len(records),
            metadata={"write_mode": mode.value},
        )
        assert self._audit is not None, (
            "_log_gold_audit called without audit configured"
        )
        await self._audit.log_write(audit_entry)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version."""
        module = self._load_gold_writer_module()

        try:
            dt = await self._run_in_executor(lambda: module.DeltaTable(table_path))
            version: int = dt.version()  # type: ignore[union-attr]
            return version
        except module.TableNotFoundError:
            return None

    async def _write_gold_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[SilverWriteResult] | None = None,
        gold_schema: object | None = None,
    ) -> None:
        """Write Gold layer metadata sidecar file."""
        if not records:
            return
        provider_name, entity_name = self._resolve_provider_entity(table_name)
        metadata = self._create_gold_metadata_payload(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            silver_refs=silver_refs,
            gold_schema=gold_schema,
        )
        await self._write_gold_metadata_file(
            table_path=table_path,
            metadata=metadata,
            table_name=table_name,
            provider_name=provider_name,
            entity_name=entity_name,
        )

    def _resolve_provider_entity(self, table_name: str) -> tuple[str, str]:
        """Parse provider/entity pair from physical Gold table name."""
        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        return _parse_table_name(table_name)

    def _create_gold_metadata_payload(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[SilverWriteResult] | None,
        gold_schema: object | None,
    ) -> GoldMetadata:
        """Create metadata via coordinator when configured, else fallback builder."""
        if self._metadata_coordinator is not None:
            return self._create_gold_metadata_via_coordinator(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=mode,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
                silver_refs=silver_refs,
                gold_schema=gold_schema,
            )
        return self._create_gold_metadata_via_fallback(
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            gold_schema=gold_schema,
        )

    def _create_gold_metadata_via_coordinator(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        silver_refs: list[SilverWriteResult] | None,
        gold_schema: object | None,
    ) -> GoldMetadata:
        """Build Gold metadata using MetadataCoordinator."""
        from bioetl.domain.ports import GoldMetadataInput, SilverRef

        converted_refs = (
            [
                SilverRef(
                    table_name=ref.table_name,
                    table_path=ref.table_path,
                    delta_version=ref.delta_version,
                )
                for ref in silver_refs
            ]
            if silver_refs
            else None
        )
        gold_input = GoldMetadataInput(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            completed_at=ingestion_ts,
            silver_refs=converted_refs,
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            gold_schema=gold_schema,
        )
        assert self._metadata_coordinator is not None
        return self._metadata_coordinator.create_gold_metadata(gold_input)

    def _create_gold_metadata_via_fallback(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        gold_schema: object | None,
    ) -> GoldMetadata:
        """Build Gold metadata through fallback builder."""
        from bioetl.infrastructure.storage.metadata_builder import GoldMetadataBuilder

        builder = GoldMetadataBuilder(
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
        )
        return builder.build_fallback_metadata(
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            gold_schema=gold_schema,
        )

    async def _write_gold_metadata_file(
        self,
        *,
        table_path: str,
        metadata: GoldMetadata,
        table_name: str,
        provider_name: str,
        entity_name: str,
    ) -> None:
        """Persist metadata sidecar using configured writer."""
        await self._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
        schema: DataFrameSchema | None = None,
    ) -> None:
        """Write Gold layer metadata sidecar for merged composite data."""
        if not records:
            return
        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        provider_name, entity_name = _parse_table_name(table_name)
        if self._metadata_coordinator is None:
            self.logger.debug(
                "gold_merged_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return
        metadata = self._metadata_coordinator.create_gold_metadata(
            self._build_gold_merged_metadata_input(
                table_path=table_path,
                table_name=table_name,
                records=records,
                schema=schema,
            )
        )
        await self._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    def _build_gold_merged_metadata_input(
        self,
        *,
        table_path: str,
        table_name: str,
        records: list[GoldRecord],
        schema: DataFrameSchema | None,
    ) -> GoldMetadataInput:
        """Build metadata input payload for merged Gold writes."""
        from bioetl.domain.ports import GoldMetadataInput

        return GoldMetadataInput(
            table_path=table_path,
            table_name=table_name,
            records=records,
            mode=GoldWriteMode.OVERWRITE,
            completed_at=self._extract_completed_at(records[0]),
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            total_bytes=0,
            partition_count=0,
            schema_validation_enabled=schema is not None,
            schema_validation_strict=True if schema is not None else None,
        )

    @staticmethod
    def _extract_completed_at(first_record: GoldRecord) -> datetime | None:
        """Extract completed-at timestamp from merged lineage metadata."""
        completed_at_raw = first_record.get("_lineage_created_at") or first_record.get(
            "_ingestion_ts"
        )
        if isinstance(completed_at_raw, str):
            return datetime.fromisoformat(completed_at_raw)
        if isinstance(completed_at_raw, datetime):
            return completed_at_raw
        return None


__all__ = ["GoldWriterMetadataMixin"]
