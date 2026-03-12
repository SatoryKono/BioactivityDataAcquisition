"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

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
from bioetl.infrastructure.storage.silver_writer_pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
    execute_silver_write_with_tracing,
)
from bioetl.infrastructure.storage.silver_writer_postwrite_mixin import (
    SilverWriterPostwriteMixin,
)
from bioetl.infrastructure.storage.silver_writer_runtime_helpers import (
    resolve_silver_writer_runtime,
)
from bioetl.infrastructure.storage.silver_writer_validation_mixin import (
    SilverWriterValidationMixin,
)
from bioetl.infrastructure.storage.write_resilience import (
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


class SilverWriter(  # type: ignore[misc]  # Callable vs async-def in MRO
    SilverWriterArrowMixin,
    SilverWriterValidationMixin,
    SilverWriterDeltaMixin,
    SilverWriterMetadataMixin,
    SilverWriterMergedMixin,
    SilverWriterPostwriteMixin,
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
        self.csv_exporter = csv_exporter
        self._metrics = metrics
        self._audit = audit
        (
            self._tracing,
            self._write_policy,
            self._silver_validator,
            self._metadata_writer,
            self._dq_calculator,
            self._merge_resilience_policy,
        ) = resolve_silver_writer_runtime(
            tracing=tracing,
            write_policy=write_policy,
            silver_validator=silver_validator,
            metadata_writer=metadata_writer,
            dq_calculator=dq_calculator,
            merge_resilience_policy=merge_resilience_policy,
        )
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
        started_at, start_perf = datetime.now(UTC), time.perf_counter()
        return await execute_silver_write_with_tracing(
            tracing=self._tracing,
            module_name=__name__,
            invocation=_SilverWriteInvocation(
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
            ),
            started_at=started_at,
            start_perf=start_perf,
            execute_pipeline=self._execute_silver_write_pipeline,
        )

    async def _execute_silver_write_pipeline(
        self,
        *,
        invocation: _SilverWriteInvocation,
        ctx: _SilverWriteExecutionContext,
    ) -> SilverWriteResult | None:
        """Orchestrate the Silver write pipeline stages.

        Args:
            records: Normalized Bronze records to process and write.
            ctx: Immutable execution context with write parameters and span.

        Returns:
            SilverWriteResult with record count and write metadata, or None if no records.
        """
        return await execute_silver_write_pipeline(
            invocation=invocation,
            ctx=ctx,
            prepare_payload=self._prepare_silver_write_payload,
            dispatch_write=self._dispatch_write_with_domain_errors,
            complete_pipeline=self._complete_silver_write_pipeline,
        )
