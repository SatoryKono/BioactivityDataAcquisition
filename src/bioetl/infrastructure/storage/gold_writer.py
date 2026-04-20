"""Gold layer writer — RULES.md §2.1.1, REQ-DATA-009/010, REQ-CONTRACT-001."""

from __future__ import annotations

import asyncio  # noqa: F401 - compatibility monkeypatch target in tests
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, cast

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake  # noqa: F401
from deltalake.exceptions import TableNotFoundError  # noqa: F401

from bioetl.domain.exceptions import BioETLError
from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import (
    AuditPort,
    LineageStorePort,
    MetadataCoordinatorPort,
    MetadataWriterPort,
    MetricsPort,
    TracingPort,
)
from bioetl.domain.ports.noop import _NoOpSpan
from bioetl.domain.types import (
    GoldRecord,
    GoldSchemaPolicyByVersion,
    RunID,
    ScdConfig,
)
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.base_delta_writer import (
    BaseDeltaWriter,
    coerce_null_types_for_delta,  # noqa: F401
)
from bioetl.infrastructure.storage.gold.io_mixin import GoldWriterIOMixin
from bioetl.infrastructure.storage.gold.metadata_mixin import (
    GoldWriterMetadataMixin,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWritePostwriteContext as _GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteRequest as _GoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    PreparedGoldWriteContext as _PreparedGoldWriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    post_write_gold as _post_write_gold_impl,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    prepare_gold_write as _prepare_write_gold_impl,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    set_gold_write_span_attributes as _set_write_span_attributes_impl,
)
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.gold.validation_mixin import (
    GoldWriterValidationMixin,
)
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_write_targets,
)
from bioetl.infrastructure.storage.writer_common import (
    get_write_targets,
    iterate_write_targets,
    validate_write_versions,
)

if TYPE_CHECKING:
    from pandera.polars import DataFrameSchema

    from bioetl.domain.ports import LoggerPort
    from bioetl.domain.value_objects.silver_result import SilverWriteResult

__all__ = ["GoldWriteMode", "GoldWriter"]

GOLD_WRITE_RETRY_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    pa.ArrowException,
)


class _SchemaBuilder(Protocol):
    """Protocol for schema objects exposing ``to_schema``."""

    def to_schema(self) -> object:
        """Materialize runtime schema representation."""
        ...


class _ResolvedSchema(Protocol):
    """Protocol for resolved schema objects exposing columns mapping."""

    columns: dict[str, object]


def _normalize_scd_config(
    scd_config: ScdConfig,
    primary_keys: list[str] | None,
) -> ScdConfig:
    """Compatibility wrapper preserving canonical monkeypatch/import path."""
    from bioetl.infrastructure.storage.gold.pipeline_helpers import (
        normalize_scd_config,
    )

    return normalize_scd_config(scd_config, primary_keys)


def _schema_column_names(schema: object) -> tuple[str, ...]:
    """Extract ordered column names from a Pandera schema-like object."""
    if hasattr(schema, "to_schema"):
        try:
            resolved = cast(_ResolvedSchema, cast(_SchemaBuilder, schema).to_schema())
            return tuple(resolved.columns.keys())
        except (
            AttributeError,
            RuntimeError,
            TypeError,
            ValueError,
        ):
            pass
    if hasattr(schema, "columns"):
        columns = schema.columns
        if isinstance(columns, Mapping):
            return tuple(str(column) for column in columns)
    return ()


def _project_records_for_gold_schema(
    records: list[GoldRecord],
    *,
    schema: object,
) -> list[GoldRecord]:
    """Project raw Gold records to the ordered columns of one schema version."""
    schema_columns = _schema_column_names(schema)
    if not schema_columns:
        return records

    dq_defaults = {"_dq_warn": False, "_dq_error": False}
    return [
        {
            key: record.get(key, dq_defaults.get(key))
            for key in schema_columns
            if key in record or key in dq_defaults
        }
        for record in records
    ]


def _resolve_active_gold_schema(schema: object) -> object:
    """Return the active schema from version-aware routing or a plain schema."""
    if isinstance(schema, GoldSchemaPolicyByVersion):
        return schema.active_schema
    return schema


async def _write_single_target(
    writer: GoldWriter,
    *,
    request: _GoldWriteRequest,
) -> None:
    """Execute one physical Gold write target through the standard pipeline."""
    prepared = await writer._prepare_write_gold(
        table_name=request.table_name,
        records=request.records,
        mode=request.mode,
        schema=request.schema,
        scd_config=request.scd_config,
        ingestion_ts=request.ingestion_ts,
    )
    await writer._dispatch_write(
        _GoldWriteDispatchContext(
            prepared=prepared,
            request=request,
        )
    )
    await writer._post_write_gold(
        _GoldWritePostwriteContext(
            prepared=prepared,
            records=request.records,
            ingestion_ts=request.ingestion_ts,
            run_id=request.run_id,
            scd_config=request.scd_config,
            silver_refs=request.silver_refs,
            schema=request.schema,
        )
    )


async def _write_dual_targets(
    writer: GoldWriter,
    *,
    request: _GoldWriteRequest,
    schema_policy: GoldSchemaPolicyByVersion,
) -> None:
    """Write all versioned Gold targets and fail on the first error."""
    assert writer._contract_rollout_policy is not None  # guarded by caller

    write_versions = writer._contract_rollout_policy.write_versions

    # Use common functions to reduce duplication
    validate_write_versions(write_versions)
    write_targets = get_write_targets(request.table_name, write_versions)

    for contract_version, physical_table in iterate_write_targets(
        write_versions, write_targets
    ):
        target_schema = schema_policy.for_version(contract_version)
        if target_schema is None:
            raise ValueError(
                f"No Gold schema configured for contract version {contract_version}"
            )
        target_request = _GoldWriteRequest(
            table_name=physical_table,
            records=_project_records_for_gold_schema(
                request.records,
                schema=target_schema,
            ),
            schema=cast("DataFrameSchema", target_schema),
            primary_keys=request.primary_keys,
            mode=request.mode,
            partition_cols=request.partition_cols,
            scd_config=request.scd_config,
            column_order=request.column_order,
            ingestion_ts=request.ingestion_ts,
            run_id=request.run_id,
            silver_refs=request.silver_refs,
        )
        try:
            await writer._write_single_target(request=target_request)
        except (BioETLError, OSError, RuntimeError, ValueError):
            writer.logger.error(
                "gold_dual_write_failed",
                logical_table=request.table_name,
                failed_contract_version=contract_version,
                failed_target_table=physical_table,
                active_contract_version=writer._contract_rollout_policy.active_version,
                write_versions=writer._contract_rollout_policy.write_versions,
            )
            raise


class GoldWriter(
    GoldWriterValidationMixin,
    GoldWriterIOMixin,
    GoldWriterMetadataMixin,
    BaseDeltaWriter,
):
    """Gold layer writer: strict Pandera validation, Delta Lake, and SCD2."""

    def _should_dual_write(self) -> bool:
        """Return True when rollout policy requires Gold shadow writes."""
        if self._contract_rollout_policy is None:
            return False
        return (
            self._contract_rollout_policy.mode
            in {
                "dual_write",
                "dual_read_write",
            }
            and len(self._contract_rollout_policy.write_versions) > 1
        )

    def __init__(
        self,
        base_path: str | Path,
        logger: LoggerPort,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        runtime_services: GoldWriterRuntimeServices | None = None,
        flat_structure: bool = False,
        **legacy_kwargs: object,
    ) -> None:
        """Initialize Gold writer with explicit runtime collaborators."""
        csv_exporter = cast(
            "CsvExporter | None", legacy_kwargs.pop("csv_exporter", None)
        )
        tracing = cast("TracingPort | None", legacy_kwargs.pop("tracing", None))
        metrics = cast("MetricsPort | None", legacy_kwargs.pop("metrics", None))
        audit = cast("AuditPort | None", legacy_kwargs.pop("audit", None))
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
        contract_rollout_policy = legacy_kwargs.pop("contract_rollout_policy", None)
        if legacy_kwargs:
            unexpected = ", ".join(sorted(legacy_kwargs))
            raise TypeError(f"Unexpected GoldWriter options: {unexpected}")

        super().__init__(base_path, logger, flat_structure=flat_structure)
        services = (
            runtime_services
            or build_gold_writer_runtime_services(
                csv_exporter=csv_exporter,
                tracing=tracing,
                metrics=metrics,
                audit=audit,
                metadata_writer=metadata_writer,
                metadata_coordinator=metadata_coordinator,
                lineage_store=lineage_store,
                contract_rollout_policy=cast(
                    "Any",  # Any: rollout policy protocol narrows only after runtime service assembly.
                    contract_rollout_policy,
                ),
            )
        )
        self.csv_exporter = services.csv_exporter
        self._metrics = services.metrics
        self._audit = services.audit
        self._tracing = services.tracing
        self._metadata_writer = services.metadata_writer
        self._metadata_coordinator = services.metadata_coordinator
        self._lineage_store = services.lineage_store
        self._contract_rollout_policy = services.contract_rollout_policy
        self._transform_version = transform_version
        self._transform_steps = transform_steps or ()

    async def write_gold(
        self,
        table_name: str,
        records: list[GoldRecord],
        schema: object,
        primary_keys: list[str] | None = None,
        mode: str = "overwrite",
        partition_cols: list[str] | None = None,
        scd_config: ScdConfig | None = None,
        *,
        column_order: list[str] | None = None,
        ingestion_ts: datetime | None = None,
        run_id: RunID | None = None,
        silver_refs: list[SilverWriteResult] | None = None,
    ) -> None:
        """Validate and write Gold records, including SCD2 and dual-write flows."""
        span_context = (
            self._tracing.get_tracer(__name__).start_as_current_span("write_gold")
            if self._tracing is not None
            else _NoOpSpan()
        )
        with span_context as span:
            normalized_scd_config = (
                ScdConfig.from_mapping(scd_config, primary_keys=primary_keys)
                if isinstance(scd_config, Mapping)
                else scd_config
            )
            active_schema = _resolve_active_gold_schema(schema)
            request = _GoldWriteRequest(
                table_name=table_name,
                records=records,
                schema=cast("DataFrameSchema", active_schema),
                primary_keys=primary_keys,
                mode=mode,
                partition_cols=partition_cols,
                scd_config=normalized_scd_config,
                column_order=column_order,
                ingestion_ts=ingestion_ts,
                run_id=run_id,
                silver_refs=silver_refs,
            )
            self._set_write_span_attributes(
                span,
                request.table_name,
                request.mode,
                len(request.records),
            )
            if self._should_dual_write() and isinstance(
                schema,
                GoldSchemaPolicyByVersion,
            ):
                await self._write_dual_targets(request=request, schema_policy=schema)
                return
            prepared = await self._prepare_write_gold(
                table_name=request.table_name,
                records=request.records,
                mode=request.mode,
                schema=request.schema,
                scd_config=request.scd_config,
                ingestion_ts=request.ingestion_ts,
            )
            await self._dispatch_write(
                _GoldWriteDispatchContext(
                    prepared=prepared,
                    request=request,
                )
            )
            await self._post_write_gold(
                _GoldWritePostwriteContext(
                    prepared=prepared,
                    records=request.records,
                    ingestion_ts=request.ingestion_ts,
                    run_id=request.run_id,
                    scd_config=request.scd_config,
                    silver_refs=request.silver_refs,
                    schema=request.schema,
                )
            )

    async def _write_dual_targets(
        self,
        *,
        request: _GoldWriteRequest,
        schema_policy: GoldSchemaPolicyByVersion,
    ) -> None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        await _write_dual_targets(
            self,
            request=request,
            schema_policy=schema_policy,
        )

    async def _write_single_target(
        self,
        *,
        request: _GoldWriteRequest,
    ) -> None:
        """Compatibility seam for direct test patching and dual-write orchestration."""
        await _write_single_target(
            self,
            request=request,
        )

    async def _prepare_write_gold(
        self,
        *,
        table_name: str,
        records: list[GoldRecord],
        mode: str,
        schema: DataFrameSchema,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
    ) -> _PreparedGoldWriteContext:
        """Run validation and path resolution before a Gold write."""
        return await _prepare_write_gold_impl(
            self,
            table_name=table_name,
            records=records,
            mode=mode,
            schema=schema,
            scd_config=scd_config,
            ingestion_ts=ingestion_ts,
        )

    async def _post_write_gold(
        self,
        context: _GoldWritePostwriteContext,
    ) -> None:
        """Emit audit, lineage, and metadata after a successful Gold write."""
        await _post_write_gold_impl(self, context)

    @staticmethod
    def _set_write_span_attributes(
        span: Any,  # Any: tracing SDK span protocol is runtime-provided
        table_name: str,
        mode: str,
        record_count: int,
    ) -> None:
        """Set standard tracing attributes for a Gold write span."""
        _set_write_span_attributes_impl(span, table_name, mode, record_count)
