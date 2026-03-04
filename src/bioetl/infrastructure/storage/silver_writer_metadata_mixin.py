"""Metadata and audit helpers for SilverWriter."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    SilverMetadataInput,
)

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
    )
    from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
    from bioetl.domain.types import BronzeRecord
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics


class SilverWriterMetadataMixin:
    """Mixin with metadata, lineage, and audit helpers."""

    logger: LoggerPort
    _audit: AuditPort | None
    _metadata_coordinator: MetadataCoordinatorPort | None
    _metadata_writer: MetadataWriterPort
    _flat_structure: bool
    _transform_version: str | None
    _transform_steps: tuple[str, ...]
    _dq_calculator: DQMetricsCalculator
    _get_table_schema: Callable[[str], Awaitable[pa.Schema | None]]

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
    ) -> BatchDQMetrics:
        """Compute DQ metrics using injected calculator."""
        from bioetl.domain.services.dq_metrics_calculator import DQMetricsInput

        existing_schema = await self._get_table_schema(table_name)
        existing_fields: set[str] | None = None
        if existing_schema is not None:
            existing_fields = set(existing_schema.names)

        input_data = DQMetricsInput(
            records=records,
            existing_schema_fields=existing_fields,
            quarantined_count=quarantined_count,
        )
        return self._dq_calculator.calculate(input_data)

    async def _log_silver_audit(
        self,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None:
        """Log audit entry for Silver write operation."""
        if self._audit is None:
            return

        from uuid import UUID

        from bioetl.domain.types import RunID

        first_record = records[0]
        run_id_str = first_record.get("_run_id", "")
        ingestion_ts = first_record.get("_ingestion_ts")

        try:
            run_id = RunID(UUID(run_id_str))
        except (ValueError, TypeError):
            self.logger.warning(
                "audit_skipped_invalid_run_id",
                table=table_name,
                run_id=run_id_str,
            )
            return

        if isinstance(ingestion_ts, str):
            timestamp = datetime.fromisoformat(ingestion_ts)
        elif isinstance(ingestion_ts, datetime):
            timestamp = ingestion_ts
        else:
            timestamp = datetime.fromtimestamp(0, tz=UTC)
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=UTC)

        operation_map = {
            SilverWriteMode.MERGE: AuditOperation.MERGE,
            SilverWriteMode.APPEND: AuditOperation.APPEND,
            SilverWriteMode.DELETE: AuditOperation.DELETE,
        }
        operation = operation_map[mode]

        audit_entry = AuditEntry(
            run_id=run_id,
            timestamp=timestamp,
            layer=AuditLayer.SILVER,
            table_name=table_name,
            operation=operation,
            records_count=len(records),
            metadata={
                "run_type": first_record.get("_run_type", ""),
                "source_batch_id": first_record.get("_source_batch_id", ""),
            },
        )
        await self._audit.log_write(audit_entry)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version, if table exists."""
        loop = asyncio.get_running_loop()
        try:
            delta_table = await loop.run_in_executor(
                None, lambda: DeltaTable(table_path)
            )
            version: int = delta_table.version()
            return version
        except DeltaTableNotFoundError:
            return None

    async def _write_silver_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None = None,
        dq_metrics: BatchDQMetrics | None = None,
        dq_report_path: str | None = None,
        partition_by: list[str] | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Write Silver layer metadata sidecar file."""
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is None:
            self.logger.warning(
                "silver_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return

        version_after = await self._get_delta_version(table_path)

        silver_input = SilverMetadataInput(
            table_path=table_path,
            records=records,
            primary_keys=primary_keys,
            mode=mode,
            bronze_refs=bronze_refs,
            dq_metrics=dq_metrics,
            version_after=version_after,
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
            dq_report_path=dq_report_path,
            partition_by=partition_by,
            started_at=started_at,
            completed_at=completed_at,
        )
        metadata = self._metadata_coordinator.create_silver_metadata(silver_input)
        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _write_silver_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write Silver metadata sidecar for merged composite data."""
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import (
            SilverMetadataBuilder,
            _parse_table_name,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is None:
            self.logger.debug(
                "silver_merged_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return

        version_after = await self._get_delta_version(table_path)

        builder = SilverMetadataBuilder(
            transform_version=self._transform_version,
            transform_steps=self._transform_steps,
        )
        metadata = builder.build_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            run_id=run_id,
            sources_used=sources_used,
            version_after=version_after,
        )

        await self._metadata_writer.write_silver_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )
