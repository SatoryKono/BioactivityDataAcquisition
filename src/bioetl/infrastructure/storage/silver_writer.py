"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa
from deltalake import DeltaTable as _DeltaTable
from deltalake import write_deltalake as _write_deltalake

from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
)
from bioetl.infrastructure.storage.silver_writer_arrow_mixin import (
    SilverWriterArrowMixin,
)
from bioetl.infrastructure.storage.silver_writer_delta_mixin import (
    SilverWriterDeltaMixin,
)
from bioetl.infrastructure.storage.silver_writer_maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver_writer_merged_mixin import (
    SilverWriterMergedMixin,
)
from bioetl.infrastructure.storage.silver_writer_metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver_writer_validation_mixin import (
    SilverWriterValidationMixin,
)
from bioetl.infrastructure.storage.write_resilience import (
    DEFAULT_SILVER_MERGE_POLICY,
    SilverMergeResiliencePolicy,
)

# Backward-compatible module aliases for tests patching historical symbols.
asyncio = _asyncio
DeltaTable = _DeltaTable
write_deltalake = _write_deltalake

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult
    from bioetl.infrastructure.export.csv_exporter import CsvExporter

__all__ = ["SilverWriteMode", "SilverWriter"]


@dataclass(frozen=True, slots=True)
class _SilverWriteExecutionContext:
    """Immutable execution context carried through the Silver write pipeline.

    Bundles the write parameters and per-call timing artefacts created at the start
    of ``SilverWriter._write_silver_with_tracing``. Passing a single context object
    between the private pipeline stages avoids wide parameter lists and keeps each
    stage's interface stable as new cross-cutting concerns are added.

    Attributes:
        table_name: Logical Delta table name (e.g. ``"chembl/activity"``).
        primary_keys: List of field names that uniquely identify a record; used for
            MERGE/upsert predicate construction.
        schema: PyArrow schema applied when creating or evolving the Delta table.
        mode: Write mode string (``"merge"``, ``"append"``, ``"overwrite"``).
        partition_cols: Optional list of column names for Delta table partitioning.
        on_schema_mismatch: Policy when incoming schema differs from the stored table
            schema; one of ``"error"``, ``"evolve"``, or ``"ignore"``.
        column_order: Optional explicit column ordering applied to the Arrow table
            before writing.
        bronze_refs: Optional list of ``BronzeWriteResult`` objects written to the
            Silver metadata as lineage references (ADR-014).
        key_nullability_rules: Optional per-key nullability override rules applied
            before the MERGE predicate is evaluated.
        started_at: Wall-clock UTC datetime at the start of the write call; stored in
            result metadata.
        start_perf: High-resolution ``time.perf_counter()`` snapshot for duration
            measurement.
        span: Active OpenTelemetry span passed through pipeline stages for attribute
            updates; type is ``Any`` because the OTel interface is runtime-dependent.
    """

    table_name: str
    primary_keys: list[str]
    schema: pa.Schema
    mode: str
    partition_cols: list[str] | None
    on_schema_mismatch: Literal["error", "evolve", "ignore"]
    column_order: list[str] | None
    bronze_refs: list[BronzeWriteResult] | None
    key_nullability_rules: list[KeyNullabilityRule] | None
    started_at: datetime
    start_perf: float
    span: Any  # Any: OpenTelemetry span interface is runtime-dependent


class SilverWriter(  # type: ignore[misc]  # Callable vs async-def in MRO
    SilverWriterArrowMixin,
    SilverWriterValidationMixin,
    SilverWriterDeltaMixin,
    SilverWriterMetadataMixin,
    SilverWriterMergedMixin,
    SilverWriterMaintenanceMixin,
    BaseDeltaWriter,
):
    """Writer for Silver layer (normalized data in Delta Lake)."""

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        csv_exporter: CsvExporter | None = None,
        write_policy: WriteModePolicy | None = None,
        metrics: MetricsPort | None = None,
        audit: AuditPort | None = None,
        silver_validator: SilverValidatorPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        flat_structure: bool = False,
        dq_calculator: DQMetricsCalculator | None = None,
        merge_resilience_policy: SilverMergeResiliencePolicy | None = None,
    ) -> None:
        """Initialize Silver writer.

        Args:
            base_path: Root directory for Silver layer Delta Lake tables.
            logger: Structured logger for write events and errors.
            tracing: Optional tracing port for span propagation; defaults to
                NoOpTracing when None.
            csv_exporter: Optional CSV exporter for post-write CSV snapshots;
                disabled when None.
            write_policy: Medallion write mode policy; uses default policy when None.
            metrics: Optional metrics port for recording write telemetry; disabled
                when None.
            audit: Optional audit port for Silver lineage logging; disabled when None.
            silver_validator: Optional Pandera schema validator; defaults to
                NoOpSilverValidator when None.
            metadata_writer: Optional sidecar metadata writer; defaults to
                NoOpMetadataWriter when None.
            metadata_coordinator: Optional coordinator for metadata orchestration;
                disabled when None.
            transform_version: Optional version string embedded in Silver metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            flat_structure: When True, omit the table-based subdirectory hierarchy.
            dq_calculator: Optional DQ metrics calculator; uses default instance when None.
            merge_resilience_policy: Optional resilience policy for merge retries
                and timeouts; uses default policy when None.
        """
        super().__init__(base_path, logger, flat_structure=flat_structure)
        self._dq_calculator = dq_calculator or DQMetricsCalculator()
        self._merge_resilience_policy = (
            merge_resilience_policy or DEFAULT_SILVER_MERGE_POLICY
        )
        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()
        self.csv_exporter = csv_exporter
        self._write_policy = write_policy or WriteModePolicy()
        self._metrics = metrics
        self._audit = audit
        self._tracing: TracingPort = tracing
        if silver_validator is None:
            from bioetl.infrastructure.validation.pandera_validator import (
                NoOpSilverValidator,
            )

            silver_validator = NoOpSilverValidator()
        self._silver_validator: SilverValidatorPort = silver_validator
        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_silver(
        self,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Write normalized records to Silver layer (Delta Lake merge/upsert).

        Args:
            table_name: Logical Delta table name (e.g., ``"chembl/activity"``).
            records: Normalized Bronze records to upsert into the Silver table.
            primary_keys: Field names used to construct the MERGE predicate.
            schema: PyArrow schema for table creation or evolution.
            mode: Write mode string (``"merge"``, ``"append"``, or ``"overwrite"``).
            partition_cols: Optional column names for Delta table partitioning;
                disables partitioning when None.
            on_schema_mismatch: Policy when incoming schema differs from stored
                table schema; one of ``"error"``, ``"evolve"``, or ``"ignore"``.
            column_order: Optional explicit column ordering applied before writing;
                uses schema order when None.
            bronze_refs: Optional Bronze write results included as lineage
                references in Silver metadata (ADR-014).
            key_nullability_rules: Optional per-key nullability overrides applied
                before MERGE predicate evaluation.

        Returns:
            SilverWriteResult with record count and write metadata, or None if
            no records were provided.
        """
        return await self._write_silver_with_tracing(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
            on_schema_mismatch=on_schema_mismatch,
            column_order=column_order,
            bronze_refs=bronze_refs,
            key_nullability_rules=key_nullability_rules,
        )

    async def _write_silver_with_tracing(
        self,
        *,
        table_name: str,
        records: list[BronzeRecord],
        primary_keys: list[str],
        schema: pa.Schema,
        mode: str,
        partition_cols: list[str] | None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
        column_order: list[str] | None,
        bronze_refs: list[BronzeWriteResult] | None,
        key_nullability_rules: list[KeyNullabilityRule] | None,
    ) -> SilverWriteResult | None:
        """Execute the Silver write pipeline within an OTel tracing span.

        Args:
            table_name: Logical Delta table name (e.g., "chembl/activity").
            records: Normalized Bronze records to upsert.
            primary_keys: Field names used to construct the MERGE predicate.
            schema: PyArrow schema for table creation or evolution.
            mode: Write mode string ("merge", "append", or "overwrite").
            partition_cols: Optional column names for Delta table partitioning.
            on_schema_mismatch: Schema mismatch policy ("error", "evolve", or "ignore").
            column_order: Optional explicit column ordering applied before writing.
            bronze_refs: Optional Bronze write results for lineage metadata.
            key_nullability_rules: Optional per-key nullability override rules.

        Returns:
            SilverWriteResult with record count and write metadata, or None if no records.
        """
        started_at, start_perf = datetime.now(UTC), time.perf_counter()
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_silver") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))
            ctx = _SilverWriteExecutionContext(
                table_name=table_name,
                primary_keys=primary_keys,
                schema=schema,
                mode=mode,
                partition_cols=partition_cols,
                on_schema_mismatch=on_schema_mismatch,
                column_order=column_order,
                bronze_refs=bronze_refs,
                key_nullability_rules=key_nullability_rules,
                started_at=started_at,
                start_perf=start_perf,
                span=span,
            )
            return await self._execute_silver_write_pipeline(
                records=records,
                ctx=ctx,
            )

    async def _execute_silver_write_pipeline(
        self,
        *,
        records: list[BronzeRecord],
        ctx: _SilverWriteExecutionContext,
    ) -> SilverWriteResult | None:
        """Orchestrate the Silver write pipeline stages.

        Args:
            records: Normalized Bronze records to process and write.
            ctx: Immutable execution context with write parameters and span.

        Returns:
            SilverWriteResult with record count and write metadata, or None if no records.
        """
        (
            records,
            validated_mode,
            table_path,
            arrow_data,
        ) = await self._prepare_silver_write_payload(
            table_name=ctx.table_name,
            records=records,
            primary_keys=ctx.primary_keys,
            schema=ctx.schema,
            mode=ctx.mode,
            on_schema_mismatch=ctx.on_schema_mismatch,
            column_order=ctx.column_order,
            partition_cols=ctx.partition_cols,
            key_nullability_rules=ctx.key_nullability_rules,
        )
        ctx.span.set_attribute("record_count", len(records))
        await self._dispatch_write_with_domain_errors(
            table_name=ctx.table_name,
            validated_mode=validated_mode,
            table_path=table_path,
            arrow_data=arrow_data,
            primary_keys=ctx.primary_keys,
            partition_cols=ctx.partition_cols,
        )
        return await self._complete_silver_write_pipeline(
            ctx=ctx,
            records=records,
            validated_mode=validated_mode,
            table_name=ctx.table_name,
            table_path=table_path,
            arrow_data=arrow_data,
        )

    async def _complete_silver_write_pipeline(
        self,
        *,
        ctx: _SilverWriteExecutionContext,
        records: list[BronzeRecord],
        validated_mode: SilverWriteMode,
        table_name: str,
        table_path: str,
        arrow_data: pa.Table,
    ) -> SilverWriteResult | None:
        """Run post-write stages: CSV export, audit, and result finalization.

        Args:
            ctx: Immutable execution context with write parameters, span, and timing.
            records: Normalized Bronze records that were written.
            validated_mode: Resolved write mode enum from the preparation step.
            table_name: Logical Delta table name for audit and metadata.
            table_path: Resolved filesystem path of the Silver Delta table.
            arrow_data: PyArrow table built from the normalized records.

        Returns:
            SilverWriteResult with record count and write metadata, or None if no records.
        """
        await self._maybe_export_csv(
            table_name=ctx.table_name,
            arrow_data=arrow_data,
            mode=ctx.mode,
            validated_mode=validated_mode,
            primary_keys=ctx.primary_keys,
        )
        await self._maybe_log_silver_audit(
            table_name=ctx.table_name,
            records=records,
            mode=validated_mode,
        )
        return await self._finalize_silver_write_result(
            table_name=table_name,
            records=records,
            table_path=table_path,
            primary_keys=ctx.primary_keys,
            validated_mode=validated_mode,
            bronze_refs=ctx.bronze_refs,
            partition_cols=ctx.partition_cols,
            started_at=ctx.started_at,
            start_perf=ctx.start_perf,
        )
