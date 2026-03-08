"""Metadata and audit helpers for SilverWriter."""

from __future__ import annotations

__all__ = ["SilverWriterMetadataMixin"]

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, ClassVar

from deltalake import DeltaTable
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.ports import (
    AuditEntry,
    AuditLayer,
    AuditOperation,
    SilverMetadataInput,
)
from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

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
    from bioetl.domain.value_objects.silver_result import SilverWriteResult


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
    _SILVER_AUDIT_OPERATION_MAP: ClassVar[dict[SilverWriteMode, AuditOperation]] = {
        SilverWriteMode.MERGE: AuditOperation.MERGE,
        SilverWriteMode.APPEND: AuditOperation.APPEND,
        SilverWriteMode.DELETE: AuditOperation.DELETE,
    }

    async def _compute_dq_metrics(
        self,
        table_name: str,
        records: list[BronzeRecord],
        quarantined_count: int = 0,
    ) -> BatchDQMetrics:
        """Compute DQ metrics using injected calculator.

        Args:
            table_name: Logical table name used for schema lookup.
            records: List of record dicts to analyse.
            quarantined_count: Number of records quarantined before this write.

        Returns:
            BatchDQMetrics instance with null rates, schema drift, and quarantine counts.
        """
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
        """Log audit entry for Silver write operation.

        Args:
            table_name: Logical table name for the audit entry.
            records: List of records written; first record provides run_id and ingestion timestamp.
            mode: Silver write mode used for this operation.
        """
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
        operation = self._SILVER_AUDIT_OPERATION_MAP[mode]
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
        """Get current Delta table version, if table exists.

        Args:
            table_path: File system path to the Delta table.

        Returns:
            Integer Delta table version if the table exists, None otherwise.
        """
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
        """Write Silver layer metadata sidecar file.

        Args:
            table_path: File system path to the Delta table.
            table_name: Logical table name used to derive provider and entity.
            records: List of records written; used to derive record count and run context.
            primary_keys: List of primary key column names for lineage metadata.
            mode: Silver write mode recorded in the metadata.
            bronze_refs: Optional list of Bronze write results linked to this Silver write.
            dq_metrics: Optional pre-computed DQ metrics to embed in metadata.
            dq_report_path: Optional file path to the DQ report for this table.
            partition_by: Optional list of partition column names.
            started_at: Optional datetime when the write operation started.
            completed_at: Optional datetime when the write operation completed.
        """
        if not records:
            return
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
        """Write Silver metadata sidecar for merged composite data.

        Args:
            table_path: File system path to the Delta table.
            table_name: Logical table name used to derive provider and entity.
            records: List of merged records; used for record count and context.
            primary_keys: List of primary key column names for lineage metadata.
            run_id: Optional run identifier to embed in the metadata.
            sources_used: Optional list of source identifiers contributing to the merge.
        """
        if not records:
            return
        from bioetl.infrastructure.storage.metadata_builder import (
            SilverMetadataBuilder,
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

    async def _maybe_log_silver_audit(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        mode: SilverWriteMode,
    ) -> None:
        """Guard for audit logging — only calls _log_silver_audit if enabled.

        Args:
            table_name: Logical table name for the audit entry.
            records: List of records written; must be non-empty to trigger audit.
            mode: Silver write mode to record in the audit entry.
        """
        if self._audit and records:
            await self._log_silver_audit(
                table_name=table_name,
                records=records,
                mode=mode,
            )

    async def _finalize_silver_write_result(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        table_path: str,
        primary_keys: list[str],
        validated_mode: SilverWriteMode,
        bronze_refs: list[BronzeWriteResult] | None,
        partition_cols: list[str] | None,
        started_at: datetime,
        start_perf: float,
    ) -> SilverWriteResult | None:
        """Compute DQ metrics, write metadata, and build final result.

        Args:
            table_name: Logical table name for the Silver write.
            records: List of records written; used for DQ metrics and metadata.
            table_path: File system path to the Delta table.
            primary_keys: List of primary key column names.
            validated_mode: Silver write mode used for this operation.
            bronze_refs: Optional list of Bronze write results linked to this write.
            partition_cols: Optional list of partition column names.
            started_at: Datetime when the write operation started.
            start_perf: Performance counter value at write start for duration calculation.

        Returns:
            SilverWriteResult instance if Delta version is available, None otherwise.
        """
        dq_metrics = await self._compute_dq_metrics(table_name, records)
        version_after = await self._get_delta_version(table_path)
        completed_at = started_at + timedelta(seconds=time.perf_counter() - start_perf)

        await self._write_silver_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            mode=validated_mode,
            bronze_refs=bronze_refs,
            dq_metrics=dq_metrics,
            partition_by=partition_cols,
            started_at=started_at,
            completed_at=completed_at,
        )
        if version_after is None:
            return None

        from bioetl.domain.value_objects.silver_result import SilverWriteResult

        return SilverWriteResult(
            table_name=table_name,
            table_path=table_path,
            delta_version=version_after,
            record_count=len(records),
        )
