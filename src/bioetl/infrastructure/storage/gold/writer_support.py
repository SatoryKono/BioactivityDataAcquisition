"""Support helpers for the public ``gold_writer`` facade."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any, Protocol, cast

from pandera.polars import DataFrameSchema

from bioetl.domain.exceptions import BioETLError
from bioetl.domain.types import GoldRecord, GoldSchemaPolicyByVersion, RunID, ScdConfig
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteDispatchContext as _GoldWriteDispatchContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWritePostwriteContext as _GoldWritePostwriteContext,
)
from bioetl.infrastructure.storage.gold.pipeline_helpers import (
    GoldWriteRequest as _GoldWriteRequest,
)
from bioetl.infrastructure.storage.gold.runtime_helpers import (
    GoldWriterRuntimeServices,
    build_gold_writer_runtime_services,
)
from bioetl.infrastructure.storage.writer_common import (
    get_write_targets,
    iterate_write_targets,
    validate_write_versions,
)

__all__ = [
    "_build_gold_write_request",
    "_project_records_for_gold_schema",
    "_resolve_active_gold_schema",
    "_resolve_runtime_services",
    "_write_dual_targets_impl",
    "_write_single_target_impl",
]


class _SchemaBuilder(Protocol):
    """Protocol for schema objects exposing ``to_schema``."""

    def to_schema(self) -> object:
        """Materialize runtime schema representation."""
        ...


class _ResolvedSchema(Protocol):
    """Protocol for resolved schema objects exposing columns mapping."""

    columns: dict[str, object]


class _GoldWriterHost(Protocol):
    """Host contract needed by Gold write support helpers."""

    logger: Any  # Any: facade host may provide structlog-like or test-double logger implementations.
    _contract_rollout_policy: (
        Any  # Any: rollout policy is runtime-wired and only duck-typed at this seam.
    )

    async def _prepare_write_gold(self, **kwargs: object) -> None: ...

    async def _dispatch_write(self, context: _GoldWriteDispatchContext) -> None: ...

    async def _post_write_gold(self, context: _GoldWritePostwriteContext) -> None: ...

    async def _write_single_target(self, *, request: _GoldWriteRequest) -> None: ...


def _schema_column_names(schema: object) -> tuple[str, ...]:
    """Extract ordered column names from a Pandera schema-like object."""
    if hasattr(schema, "to_schema"):
        try:
            resolved = cast(_ResolvedSchema, cast(_SchemaBuilder, schema).to_schema())
            return tuple(resolved.columns.keys())
        except (AttributeError, RuntimeError, TypeError, ValueError):
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


def _resolve_runtime_services(
    *,
    runtime_services: GoldWriterRuntimeServices | None,
    legacy_kwargs: dict[str, object],
) -> GoldWriterRuntimeServices:
    """Normalize legacy constructor kwargs into grouped Gold runtime services."""
    csv_exporter = legacy_kwargs.pop("csv_exporter", None)
    tracing = legacy_kwargs.pop("tracing", None)
    metrics = legacy_kwargs.pop("metrics", None)
    audit = legacy_kwargs.pop("audit", None)
    metadata_writer = legacy_kwargs.pop("metadata_writer", None)
    metadata_coordinator = legacy_kwargs.pop("metadata_coordinator", None)
    lineage_store = legacy_kwargs.pop("lineage_store", None)
    contract_rollout_policy = legacy_kwargs.pop("contract_rollout_policy", None)
    if legacy_kwargs:
        unexpected = ", ".join(sorted(legacy_kwargs))
        raise TypeError(f"Unexpected GoldWriter options: {unexpected}")

    return runtime_services or build_gold_writer_runtime_services(
        csv_exporter=csv_exporter,
        tracing=tracing,
        metrics=metrics,
        audit=audit,
        metadata_writer=metadata_writer,
        metadata_coordinator=metadata_coordinator,
        lineage_store=lineage_store,
        contract_rollout_policy=cast(
            Any,  # Any: builder accepts runtime-wired rollout policy implementations.
            contract_rollout_policy,
        ),
    )


def _build_gold_write_request(
    *,
    table_name: str,
    records: list[GoldRecord],
    schema: object,
    primary_keys: list[str] | None,
    mode: str,
    partition_cols: list[str] | None,
    scd_config: ScdConfig | None,
    column_order: list[str] | None,
    ingestion_ts: datetime | None,
    run_id: RunID | None,
    silver_refs: list[SilverWriteResult] | None,
) -> _GoldWriteRequest:
    """Build the canonical Gold write request."""
    return _GoldWriteRequest(
        table_name=table_name,
        records=records,
        schema=cast("DataFrameSchema", schema),
        primary_keys=primary_keys,
        mode=mode,
        partition_cols=partition_cols,
        scd_config=scd_config,
        column_order=column_order,
        ingestion_ts=ingestion_ts,
        run_id=run_id,
        silver_refs=silver_refs,
    )


async def _write_single_target_impl(
    writer: _GoldWriterHost,
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


async def _write_dual_targets_impl(
    writer: _GoldWriterHost,
    *,
    request: _GoldWriteRequest,
    schema_policy: GoldSchemaPolicyByVersion,
) -> None:
    """Write all versioned Gold targets and fail on the first error."""
    assert writer._contract_rollout_policy is not None

    write_versions = writer._contract_rollout_policy.write_versions
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
