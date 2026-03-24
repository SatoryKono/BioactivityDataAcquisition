"""Silver layer writer (Delta Lake with merge/upsert)."""

from __future__ import annotations

import asyncio as _asyncio
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal, cast

import pyarrow as pa
from deltalake import DeltaTable as _DeltaTable
from deltalake import write_deltalake as _write_deltalake

from bioetl.domain.medallion import SilverWriteMode, WriteModePolicy
from bioetl.domain.ports import (
    AuditPort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    SilverValidatorPort,
    TracingPort,
)
from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
)
from bioetl.infrastructure.storage.delta.resilience import (
    SilverMergeResiliencePolicy,
)
from bioetl.infrastructure.storage.silver.arrow_mixin import (
    SilverWriterArrowMixin,
)
from bioetl.infrastructure.storage.silver.delta_mixin import (
    SilverWriterDeltaMixin,
)
from bioetl.infrastructure.storage.silver.maintenance_mixin import (
    SilverWriterMaintenanceMixin,
)
from bioetl.infrastructure.storage.silver.merged_mixin import (
    SilverWriterMergedMixin,
)
from bioetl.infrastructure.storage.silver.metadata_mixin import (
    SilverWriterMetadataMixin,
)
from bioetl.infrastructure.storage.silver.pipeline_helpers import (
    _SilverWriteExecutionContext,
    _SilverWriteInvocation,
    execute_silver_write_pipeline,
    execute_silver_write_with_tracing,
)
from bioetl.infrastructure.storage.silver.postwrite_mixin import (
    SilverWriterPostwriteMixin,
)
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServices,
    build_silver_writer_runtime_services,
)
from bioetl.infrastructure.storage.silver.validation_mixin import (
    SilverWriterValidationMixin,
)

# Backward-compatible module aliases for tests patching historical symbols.
asyncio = _asyncio
DeltaTable = _DeltaTable
write_deltalake = _write_deltalake
# Architecture marker imports keep SilverWriter policy/schema hooks discoverable
# in this root module while the implementations live in split validation helpers.

if TYPE_CHECKING:
    from pathlib import Path

    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.ports import LineageStorePort, LoggerPort
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

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
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: SilverWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        **legacy_kwargs: object,
    ) -> None:
        """Initialize Silver writer.

        Args:
            base_path: Root directory for Silver layer Delta Lake tables.
            logger: Structured logger for write events and errors.
            transform_version: Optional version string embedded in Silver metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            runtime_services: Optional grouped runtime collaborators for tracing,
                validation, metadata, DQ, resilience, and optional CSV export.
            flat_structure: When True, omit the table-based subdirectory hierarchy.
        """
        csv_exporter = cast(
            "CsvExporter | None", legacy_kwargs.pop("csv_exporter", None)
        )
        tracing = cast("TracingPort | None", legacy_kwargs.pop("tracing", None))
        write_policy = cast(
            "WriteModePolicy | None",
            legacy_kwargs.pop("write_policy", None),
        )
        metrics = cast("MetricsPort | None", legacy_kwargs.pop("metrics", None))
        audit = cast("AuditPort | None", legacy_kwargs.pop("audit", None))
        silver_validator = cast(
            "SilverValidatorPort | None",
            legacy_kwargs.pop("silver_validator", None),
        )
        metadata_writer = cast(
            "MetadataWriterPort | None",
            legacy_kwargs.pop("metadata_writer", None),
        )
        metadata_coordinator = cast(
            "MetadataCoordinatorPort | None",
            legacy_kwargs.pop("metadata_coordinator", None),
        )
        lineage_store = cast(
            "LineageStorePort | None",
            legacy_kwargs.pop("lineage_store", None),
        )
        dq_calculator = cast(
            "DQMetricsCalculator | None",
            legacy_kwargs.pop("dq_calculator", None),
        )
        merge_resilience_policy = cast(
            "SilverMergeResiliencePolicy | None",
            legacy_kwargs.pop("merge_resilience_policy", None),
        )
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs))
            raise TypeError(f"Unexpected SilverWriter options: {unexpected}")

        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = runtime_services or build_silver_writer_runtime_services(
            csv_exporter=csv_exporter,
            tracing=tracing,
            write_policy=write_policy,
            metrics=metrics,
            audit=audit,
            silver_validator=silver_validator,
            metadata_writer=metadata_writer,
            metadata_coordinator=metadata_coordinator,
            lineage_store=lineage_store,
            dq_calculator=dq_calculator,
            merge_resilience_policy=merge_resilience_policy,
        )
        self.csv_exporter = services.csv_exporter
        self._metrics = services.metrics
        self._audit = services.audit
        self._tracing = services.tracing
        self._write_policy = services.write_policy
        self._silver_validator = services.silver_validator
        self._metadata_writer = services.metadata_writer
        self._metadata_coordinator = services.metadata_coordinator
        self._lineage_store = services.lineage_store
        self._dq_calculator = services.dq_calculator
        self._merge_resilience_policy = services.merge_resilience_policy
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    def _enforce_write_policy(
        self,
        mode: SilverWriteMode,
        table_name: str,
    ) -> None:
        """Delegate Silver write-mode enforcement to the validation mixin."""
        SilverWriterValidationMixin._enforce_write_policy(self, mode, table_name)

    def _validate_silver_pandera(
        self,
        records: list[BronzeRecord],
        table_name: str,
    ) -> None:
        """Delegate Pandera validation to the canonical Silver validation seam."""
        SilverWriterValidationMixin._validate_silver_pandera(
            self,
            records,
            table_name,
        )

    async def _check_schema_drift(
        self,
        table_name: str,
        records: list[BronzeRecord],
        on_schema_mismatch: Literal["error", "evolve", "ignore"],
    ) -> None:
        """Delegate schema-drift handling to the canonical Silver validation seam."""
        await SilverWriterValidationMixin._check_schema_drift(
            self,
            table_name,
            records,
            on_schema_mismatch,
        )

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
            invocation: Silver write invocation with records and parameters.
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
