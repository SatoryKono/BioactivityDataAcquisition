"""Metadata and audit helpers for GoldWriter."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
    )
    from bioetl.domain.types import GoldRecord, ScdConfig


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
            delta_table = cast(
                "Any", dt
            )  # Any: runtime DeltaTable is loaded dynamically
            version: int = delta_table.version()
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
        silver_refs: list[Any] | None = None,  # Any: SilverRef heterogeneous
        gold_schema: Any | None = None,  # Any: Pandera model class
    ) -> None:
        """Write Gold layer metadata sidecar file."""
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is not None:
            from bioetl.domain.ports import GoldMetadataInput, SilverRef

            converted_refs: list[SilverRef] | None = None
            if silver_refs:
                converted_refs = [
                    SilverRef(
                        table_name=ref.table_name,
                        table_path=ref.table_path,
                        delta_version=ref.delta_version,
                    )
                    for ref in silver_refs
                ]

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
            metadata = self._metadata_coordinator.create_gold_metadata(gold_input)
            await self._metadata_writer.write_gold_metadata(
                table_path,
                metadata,
                table_name=table_name,
                flat_structure=self._flat_structure,
                provider=provider_name,
                entity=entity_name,
            )
            return

        from bioetl.infrastructure.storage.metadata_builder import GoldMetadataBuilder

        builder = GoldMetadataBuilder(
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
        )
        metadata = builder.build_fallback_metadata(
            table_name=table_name,
            records=records,
            mode=mode,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
            run_id=run_id,
            gold_schema=gold_schema,
        )

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

        from bioetl.domain.ports import GoldMetadataInput

        first_record = records[0]
        completed_at_raw = first_record.get("_lineage_created_at") or first_record.get(
            "_ingestion_ts"
        )
        completed_at: datetime | None = None
        if isinstance(completed_at_raw, str):
            completed_at = datetime.fromisoformat(completed_at_raw)
        elif isinstance(completed_at_raw, datetime):
            completed_at = completed_at_raw

        metadata = self._metadata_coordinator.create_gold_metadata(
            GoldMetadataInput(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=GoldWriteMode.OVERWRITE,
                completed_at=completed_at,
                transform_version=self._transform_version,
                transform_steps=self._transform_steps,
                total_bytes=0,
                partition_count=0,
                schema_validation_enabled=schema is not None,
                schema_validation_strict=True if schema is not None else None,
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


GoldWriterMetadataHelper = GoldWriterMetadataMixin

__all__ = ["GoldWriterMetadataHelper", "GoldWriterMetadataMixin"]
