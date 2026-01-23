"""Gold layer writer (business-ready data with strict validation).

Implements RULES.md §2.1.1 - Gold Layer specifications.

Requirements:
- REQ-DATA-009: Strict validation (strict=True)
- REQ-DATA-010: SCD Type 2 or date partitioning
- REQ-CONTRACT-001: Published schemas in docs/contracts/

Architecture:
- Uses Pandera for strict schema validation
- Local filesystem storage with Delta Lake format
- Implements SCD Type 2 (Slowly Changing Dimensions) for history tracking
- Enforces data contracts
- CSV export delegated to CsvExporter (composition)
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from typing import TYPE_CHECKING, Any, TypeVar

import pandera as pandera_pa
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from deltalake.exceptions import TableNotFoundError

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditEntry, AuditLayer, AuditOperation
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from pathlib import Path

    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetadataCoordinatorPort,
        MetadataWriterPort,
        TracingPort,
    )
    from bioetl.infrastructure.export.csv_exporter import CsvExporter


# Re-export GoldWriteMode for backward compatibility
# Consumers importing from gold_writer will still work
__all__ = ["GoldWriteMode", "GoldWriter"]


class GoldWriter(BaseDeltaWriter):
    """Writer for Gold layer (validated business data).

    Inherits from BaseDeltaWriter for common Delta Lake operations
    (get_table_path, clear).

    Enforces strict validation before writing. All records must pass
    schema validation or the entire batch fails.
    CSV export is delegated to an optional CsvExporter (composition pattern).
    """

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        tracing: TracingPort | None = None,
        csv_exporter: CsvExporter | None = None,
        audit: AuditPort | None = None,
        metadata_writer: MetadataWriterPort | None = None,
        metadata_coordinator: MetadataCoordinatorPort | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        flat_structure: bool = False,
    ) -> None:
        """Initialize Gold writer.

        Args:
            base_path: Base path for Gold tables (local filesystem)
            logger: Structured logger for observability (MUST be injected)
            tracing: TracingPort for distributed tracing. Use NoOpTracing from
                    composition layer if tracing is disabled. If None, NoOpTracing
                    is used automatically (for test convenience).
            csv_exporter: Optional CsvExporter for CSV output (None to disable)
            audit: Optional AuditPort for write operation traceability.
                  Use NoOpAudit from composition layer if audit disabled.
            metadata_writer: Optional MetadataWriterPort for writing _metadata.yaml
                           sidecar files. Use NoOpMetadataWriter if disabled.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation. If provided, uses coordinator
                                instead of local _write_gold_metadata() logic.
                                Ensures consistent run_id across layers.
            transform_version: Optional semver version of transform (e.g., '1.0.0')
                             for lineage tracking in metadata.
            transform_steps: Optional tuple of transform step names for lineage.
            flat_structure: If True, Delta data written directly to base_path
                          without table_name subdirectory.

        Note:
            LoggerPort is required per RULES.md DI requirements.
            Lock validation is now performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
        """
        # Initialize base class (sets base_path, logger, _retention_manager, _flat_structure)
        super().__init__(base_path, logger, flat_structure=flat_structure)

        # Use NoOpTracing if not provided (test convenience, production uses composition)
        # Import from domain.ports.noop to maintain proper layer separation
        if tracing is None:
            from bioetl.domain.ports import NoOpTracing

            tracing = NoOpTracing()

        self.csv_exporter = csv_exporter
        self._audit = audit
        self._tracing: TracingPort = tracing

        # Use NoOpMetadataWriter if not provided (metadata is optional)
        if metadata_writer is None:
            from bioetl.domain.ports import NoOpMetadataWriter

            metadata_writer = NoOpMetadataWriter()
        self._metadata_writer: MetadataWriterPort = metadata_writer
        self._metadata_coordinator: MetadataCoordinatorPort | None = (
            metadata_coordinator
        )

        # Transform version tracking for lineage metadata
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: DataFrameSchema,
        primary_keys: list[str] | None = None,
        mode: str = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: dict[str, Any] | None = None,
        *,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[Any] | None = None,
    ) -> None:
        """Write validated records to Gold layer.

        Args:
            table_name: Target table name
            records: List of records to write
            schema: Pandera schema for validation (must have strict=True)
            primary_keys: Primary key columns for deterministic sorting
            mode: Write mode - 'overwrite', 'append', or 'scd2'
            partition_cols: Optional partition columns
            scd_config: Required config for SCD2 mode
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014). Required for SCD2 mode
                         and audit logging.
            run_id: Run identifier for audit correlation across layers.
            silver_refs: List of SilverRef for Gold lineage tracking
                        (Silver table name → Delta version mapping).

        Raises:
            ValueError: If mode is invalid, records empty, schema not strict,
                       or SCD2 mode without ingestion_ts

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard.
        """
        tracer = self._tracing.get_tracer(__name__)
        with tracer.start_as_current_span("write_gold") as span:
            span.set_attribute("table_name", table_name)
            span.set_attribute("mode", mode)
            span.set_attribute("record_count", len(records))

            validated_mode = self._validate_write_mode(mode)
            self._validate_records(records)
            self._validate_scd2_requirements(validated_mode, scd_config, ingestion_ts)
            self._validate_schema_strict(schema)
            await self._validate_records_against_schema(records, schema)

            table_path = self._resolve_table_path(table_name)

            await self._dispatch_write(
                validated_mode,
                table_path,
                table_name,
                records,
                partition_cols,
                primary_keys,
                schema,
                scd_config,
                ingestion_ts,
            )

            if self._audit:
                await self._log_gold_audit(
                    table_name=table_name,
                    records=records,
                    mode=validated_mode,
                    ingestion_ts=ingestion_ts,
                    run_id=run_id,
                )

            # Write metadata sidecar file if configured
            await self._write_gold_metadata(
                table_path=table_path,
                table_name=table_name,
                records=records,
                mode=validated_mode,
                scd_config=scd_config,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
                gold_schema=schema,
            )

    def _validate_write_mode(self, mode: str) -> GoldWriteMode:
        """Validate and return the write mode enum."""
        try:
            return GoldWriteMode(mode)
        except ValueError:
            valid_modes = [m.value for m in GoldWriteMode]
            raise ValueError(
                f"Invalid Gold write mode '{mode}'. Allowed: {valid_modes}"
            ) from None

    def _validate_records(self, records: list[dict[str, Any]]) -> None:
        """Validate that records list is not empty."""
        if not records:
            raise ValueError("No records to write")

    def _validate_scd2_requirements(
        self,
        mode: GoldWriteMode,
        scd_config: dict[str, Any] | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Validate SCD2-specific requirements."""
        if mode != GoldWriteMode.SCD2:
            return

        if scd_config is None:
            raise ValueError("scd_config required for SCD Type 2 mode")
        if ingestion_ts is None:
            raise ValueError(
                "ingestion_ts required for SCD Type 2 mode "
                "(timestamp must come from application layer per ADR-014)"
            )

    def _validate_schema_strict(self, schema: DataFrameSchema) -> None:
        """Validate that schema has strict=True."""
        is_strict = getattr(schema, "strict", False) or getattr(
            getattr(schema, "Config", None), "strict", False
        )
        if not is_strict:
            raise ValueError("Gold layer requires strict=True schema validation")

    async def write_gold_merged(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        *,
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write merged records to Gold layer without Pandera schema.

        Used by composite pipelines where schema is dynamically determined
        by the merge operation. No Pandera validation is performed.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries representing merged records.
            primary_keys: Optional list of column names for sorting.
            run_id: Optional composite run ID for metadata tracking.
            sources_used: Optional list of source pipelines used in merge.
        """
        from bioetl.domain.schemas.column_order import canonical_column_order

        if not records:
            self.logger.warning(
                "No records to write for merged Gold",
                table_name=table_name,
            )
            return

        # Convert to Arrow and apply canonical column order
        arrow_table = pa.Table.from_pylist(records)

        # Coerce Null-typed columns for Delta Lake compatibility
        arrow_table = coerce_null_types_for_delta(arrow_table)

        # Enforce canonical column order (ADR-014, RULES.md §2.4)
        ordered_columns = canonical_column_order(list(arrow_table.column_names))
        arrow_table = arrow_table.select(ordered_columns)

        if primary_keys:
            valid_keys = [pk for pk in primary_keys if pk in arrow_table.schema.names]
            if valid_keys:
                arrow_table = arrow_table.sort_by(
                    [(pk, "ascending") for pk in valid_keys]
                )

        table_path = self._resolve_table_path(table_name)

        self.logger.info(
            "Writing merged Gold records",
            table_name=table_name,
            path=table_path,
            records=len(records),
        )

        await self._run_in_executor(
            lambda: write_deltalake(
                table_path,
                arrow_table,
                mode="overwrite",
                schema_mode="overwrite",
            ),
        )

        # Export to CSV if configured (composite pipelines use overwrite mode)
        if self.csv_exporter:
            await self.csv_exporter.export(
                table_name,
                arrow_table,
                append=False,  # Merged data replaces existing CSV
            )

        # Write metadata sidecar for composite merged data
        await self._write_gold_merged_metadata(
            table_path=table_path,
            table_name=table_name,
            records=records,
            primary_keys=primary_keys or [],
            run_id=run_id,
            sources_used=sources_used,
        )

    async def _write_gold_merged_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        run_id: str | None = None,
        sources_used: list[str] | None = None,
    ) -> None:
        """Write Gold layer metadata sidecar for merged composite data.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name (used for filename generation).
            records: List of records written.
            primary_keys: Primary key columns used.
            run_id: Composite run ID for tracking.
            sources_used: List of source pipelines (e.g., ['seed', 'crossref', 'openalex']).
        """
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import (
            GoldMetadataBuilder,
            _parse_table_name,
        )

        provider_name, entity_name = _parse_table_name(table_name)

        if self._metadata_coordinator is None:
            self.logger.debug(
                "gold_merged_metadata_skipped",
                reason="MetadataCoordinator not configured",
                table_path=table_path,
            )
            return

        # Build metadata using the extracted builder
        builder = GoldMetadataBuilder(
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
        )

        await self._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _validate_records_against_schema(
        self, records: list[dict[str, Any]], schema: DataFrameSchema
    ) -> None:
        """Validate records against Pandera schema."""
        import pandas as pd

        df = pd.DataFrame(records)
        try:
            await self._run_in_executor(lambda: schema.validate(df, lazy=False))
        except pandera_pa.errors.SchemaError as e:
            raise ValueError(f"Schema validation failed: {e}") from e

    async def _dispatch_write(
        self,
        mode: GoldWriteMode,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        partition_cols: list[str] | None,
        primary_keys: list[str] | None,
        schema: DataFrameSchema,
        scd_config: dict[str, Any] | None,
        ingestion_ts: datetime | None,
    ) -> None:
        """Dispatch to appropriate write method based on mode."""
        if mode == GoldWriteMode.SCD2:
            assert ingestion_ts is not None  # Validated in _validate_scd2_requirements
            assert scd_config is not None
            await self._write_scd2(
                table_path, records, scd_config, partition_cols, ingestion_ts
            )
        else:
            await self._write_simple(
                table_path,
                table_name,
                records,
                mode.value,
                partition_cols,
                primary_keys,
                schema,
            )

    async def _log_gold_audit(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
    ) -> None:
        """Log audit entry for Gold write operation.

        Args:
            table_name: Target table name
            records: List of records written
            mode: Write mode used
            ingestion_ts: Ingestion timestamp from application layer (ADR-014)
            run_id: Run identifier for audit correlation across layers

        Note:
            Uses provided ingestion_ts and run_id for audit correlation.
            Falls back to current time and generated UUID only if not provided
            (for backward compatibility with non-pipeline callers).
        """
        from uuid import uuid4

        # Use provided values or fallback for backward compatibility
        # ADR-014: Prefer passed values from application layer
        if ingestion_ts is not None:
            timestamp = ingestion_ts
        else:
            # Fallback for non-pipeline callers (e.g., direct API usage)
            self.logger.warning(
                "audit_missing_ingestion_ts",
                table=table_name,
                mode=mode.value,
            )
            raise ValueError("ingestion_ts is required for audit logging")

        if run_id is not None:
            audit_run_id = run_id
        else:
            # Fallback for non-pipeline callers
            self.logger.warning(
                "audit_missing_run_id",
                table=table_name,
                mode=mode.value,
            )
            audit_run_id = RunID(uuid4())

        # Map GoldWriteMode to AuditOperation
        operation_map = {
            GoldWriteMode.OVERWRITE: AuditOperation.OVERWRITE,
            GoldWriteMode.APPEND: AuditOperation.APPEND,
            GoldWriteMode.SCD2: AuditOperation.MERGE,  # SCD2 is a type of merge
        }
        operation = operation_map[mode]

        audit_entry = AuditEntry(
            run_id=audit_run_id,
            timestamp=timestamp,
            layer=AuditLayer.GOLD,
            table_name=table_name,
            operation=operation,
            records_count=len(records),
            metadata={
                "write_mode": mode.value,
            },
        )
        # Safety assertion: this method is only called when self._audit is not None
        assert self._audit is not None, (
            "_log_gold_audit called without audit configured"
        )
        await self._audit.log_write(audit_entry)

    async def _get_delta_version(self, table_path: str) -> int | None:
        """Get current Delta table version.

        Args:
            table_path: Full path to the Delta table.

        Returns:
            Current version number, or None if table doesn't exist.
        """
        try:
            dt = await self._run_in_executor(lambda: DeltaTable(table_path))
            version: int = dt.version()
            return version
        except TableNotFoundError:
            return None

    async def _write_gold_metadata(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        mode: GoldWriteMode,
        scd_config: dict[str, Any] | None,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
        silver_refs: list[Any] | None = None,
        gold_schema: Any | None = None,
    ) -> None:
        """Write Gold layer metadata sidecar file.

        Args:
            table_path: Full path to the Delta table.
            table_name: Table name.
            records: List of records written.
            mode: Write mode used (overwrite, append, scd2).
            scd_config: SCD2 configuration if applicable.
            ingestion_ts: Ingestion timestamp.
            run_id: Run identifier.
            silver_refs: List of SilverRef for Gold lineage tracking.
            gold_schema: Optional Pandera schema class for extracting schema metadata.
        """
        if not records:
            return

        from bioetl.infrastructure.storage.metadata_builder import _parse_table_name

        provider_name, entity_name = _parse_table_name(table_name)

        # Use MetadataCoordinator if available (centralized metadata)
        if self._metadata_coordinator is not None:
            from bioetl.domain.ports import GoldMetadataInput, SilverRef

            # Convert silver_refs to SilverRef if they're SilverWriteResult
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

        # Fallback to local metadata building (backward compatibility)
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

        # Write metadata sidecar file
        await self._metadata_writer.write_gold_metadata(
            table_path,
            metadata,
            table_name=table_name,
            flat_structure=self._flat_structure,
            provider=provider_name,
            entity=entity_name,
        )

    async def _run_in_executor(self, func: Callable[..., T], *args: Any) -> T:
        """Run a function in the executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, func, *args)

    def _to_arrow_table(self, records: list[dict[str, Any]]) -> pa.Table:
        """Convert records to PyArrow table, handling null types.

        Delta Lake doesn't support null type, so we convert null columns to string.
        This includes nested null types (e.g., list<null>).

        Delegates to ArrowDataConverter for the actual conversion.
        """
        from bioetl.infrastructure.storage.arrow_converter import ArrowDataConverter

        converter = ArrowDataConverter(logger=self.logger)
        return converter.convert_records_to_arrow(records)

    async def _write_simple(
        self,
        table_path: str,
        table_name: str,
        records: list[dict[str, Any]],
        mode: str,
        partition_cols: list[str] | None,
        primary_keys: list[str] | None = None,
        _schema: DataFrameSchema | None = None,
    ) -> None:
        """Write records using simple overwrite or append mode."""
        arrow_data = self._to_arrow_table(records)

        # Sort by primary keys for deterministic writing
        if primary_keys:
            arrow_data = arrow_data.sort_by([(pk, "ascending") for pk in primary_keys])

        # UPDATED: Use schema_mode="overwrite" if mode is "overwrite" to allow schema evolution
        schema_mode = "overwrite" if mode == "overwrite" else None

        for attempt in range(3):
            try:
                await self._run_in_executor(
                    lambda table_or_uri=table_path,
                    data=arrow_data,
                    mode=mode,
                    partition_by=partition_cols,
                    schema_mode=schema_mode: write_deltalake(
                        table_or_uri=table_or_uri,
                        data=pa.RecordBatchReader.from_batches(
                            data.schema, data.to_batches()
                        ),
                        mode=mode,
                        partition_by=partition_by,
                        schema_mode=schema_mode,
                    )
                )
                break
            except Exception as e:
                # Retry on potential concurrency/protocol errors
                if attempt == 2:
                    raise e
                # Exponential backoff with fixed jitter (Base 0.5s, Multiplier 2)
                # Fixed 0.05s jitter for deterministic behavior (see ADR-014)
                delay = 0.5 * (2**attempt) + 0.05
                await asyncio.sleep(delay)

        # Delegate CSV export to CsvExporter if configured
        if self.csv_exporter:
            # Match CSV append behavior to Delta mode
            csv_append = mode != "overwrite"
            # Pass primary_keys to CSV exporter for deduplication if mode is merge/append
            csv_primary_keys = primary_keys if mode != "overwrite" else None
            await self.csv_exporter.export(
                table_name, arrow_data, append=csv_append, primary_keys=csv_primary_keys
            )

    async def _write_scd2(
        self,
        table_path: str,
        records: list[dict[str, Any]],
        scd_config: dict[str, Any],
        partition_cols: list[str] | None,
        ingestion_ts: datetime,
    ) -> None:
        """Write records using SCD Type 2 (history tracking).

        Args:
            table_path: Path to the Delta table.
            records: List of records to write.
            scd_config: SCD2 configuration (business_key, version_col, etc.).
            partition_cols: Optional partition columns.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014).
        """
        business_key = scd_config["business_key"]

        # Sort records by business key for deterministic processing
        sort_keys = [business_key] if isinstance(business_key, str) else business_key

        # Sort the input records list since we modify it in place
        records.sort(key=lambda r: tuple(r.get(k) for k in sort_keys))
        version_col = scd_config.get("version_col", "version")
        valid_from_col = scd_config.get("valid_from_col", "valid_from")
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")

        # Use ingestion_ts from application layer (ADR-014: single source of truth)
        ts_iso = ingestion_ts.isoformat()
        for record in records:
            record[valid_from_col] = ts_iso
            record[valid_to_col] = None
            record[current_flag_col] = True
            record[version_col] = record.get(version_col, 1)

        for attempt in range(3):
            try:
                try:
                    dt = await self._run_in_executor(
                        lambda table_path=table_path: DeltaTable(table_path)
                    )
                    await self._merge_scd2(
                        dt, records, business_key, scd_config, ingestion_ts
                    )
                except TableNotFoundError:
                    arrow_data = self._to_arrow_table(records)
                    await self._run_in_executor(
                        lambda table_or_uri=table_path,
                        data=arrow_data,
                        mode="append",
                        partition_by=partition_cols: write_deltalake(
                            table_or_uri=table_or_uri,
                            data=pa.RecordBatchReader.from_batches(
                                data.schema, data.to_batches()
                            ),
                            mode=mode,
                            partition_by=partition_by,
                        )
                    )
                break
            except Exception as e:
                if attempt == 2:
                    raise e
                # Exponential backoff with fixed jitter (see ADR-014)
                delay = 0.5 * (2**attempt) + 0.05
                await asyncio.sleep(delay)

    async def _merge_scd2(
        self,
        dt: DeltaTable,
        records: list[dict[str, Any]],
        business_key: str | list[str],
        scd_config: dict[str, Any],
        ingestion_ts: datetime,
    ) -> None:
        """Merge records using SCD Type 2 logic.

        Args:
            dt: DeltaTable instance to merge into.
            records: List of records to merge.
            business_key: Business key column(s) for matching.
            scd_config: SCD2 configuration.
            ingestion_ts: Ingestion timestamp from application layer
                         (single source of time per ADR-014).
        """
        if isinstance(business_key, str):
            business_keys = [business_key]
        else:
            business_keys = business_key

        new_data = self._to_arrow_table(records)
        valid_to_col = scd_config.get("valid_to_col", "valid_to")
        current_flag_col = scd_config.get("current_flag_col", "is_current")
        merge_condition = " AND ".join(
            f"target.{key} = source.{key}" for key in business_keys
        )
        merge_condition += f" AND target.{current_flag_col} = true"
        # Use ingestion_ts from application layer (ADR-014: single source of truth)
        ts_iso = ingestion_ts.isoformat()

        await self._run_in_executor(
            lambda: (
                dt.merge(
                    source=pa.RecordBatchReader.from_batches(
                        new_data.schema, new_data.to_batches()
                    ),
                    predicate=merge_condition,
                    source_alias="source",
                    target_alias="target",
                )
                .when_matched_update(
                    updates={
                        valid_to_col: f"'{ts_iso}'",
                        current_flag_col: "false",
                    }
                )
                .when_not_matched_insert_all()
                .execute()
            )
        )

    # NOTE: get_table_path() and clear() are inherited from BaseDeltaWriter

    async def read_gold(
        self,
        table_name: str,
        columns: list[str] | None = None,
        current_only: bool = True,
    ) -> list[dict[str, Any]]:
        """Read data from Gold table.

        Args:
            table_name: Table name.
            columns: Optional list of columns to read.
            current_only: If True, filter to current records only (for SCD2 tables).

        Returns:
            List of records as dictionaries.

        """
        table_path = self._resolve_table_path(table_name)
        # Delta Lake (Gold) -> Arrow -> Pydict
        dt = await self._run_in_executor(lambda: DeltaTable(table_path))
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)
        if current_only and "is_current" in arrow_table.column_names:
            import pyarrow.compute as pc

            arrow_table = arrow_table.filter(pc.equal(arrow_table["is_current"], True))
        result: list[dict[str, Any]] = arrow_table.to_pylist()
        return result

    async def get_history(
        self,
        table_name: str,
        business_key_values: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get history of records in Gold table (for SCD2 tracking).

        Args:
            table_name: Table name.
            business_key_values: Optional dict of business key column -> value to filter by.
            limit: Maximum number of history entries.

        Returns:
            List of historical records.

        """
        table_path = self._resolve_table_path(table_name)
        dt = await self._run_in_executor(lambda: DeltaTable(table_path))
        arrow_table = await self._run_in_executor(dt.to_pyarrow_table)

        if business_key_values:
            import pyarrow.compute as pc

            mask = None
            for key, value in business_key_values.items():
                condition = pc.equal(arrow_table[key], value)
                mask = condition if mask is None else pc.and_(mask, condition)
            if mask is not None:
                arrow_table = arrow_table.filter(mask)

        if "valid_from" in arrow_table.column_names:
            arrow_table = arrow_table.sort_by([("valid_from", "ascending")])
        result: list[dict[str, Any]] = arrow_table.to_pylist()
        return result
