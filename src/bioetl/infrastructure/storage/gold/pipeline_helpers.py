"""Pre/post-write orchestration helpers for GoldWriter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import AuditPort
from bioetl.domain.types import GoldRecord, RunID, ScdConfig
from bioetl.domain.value_objects.silver_result import SilverWriteResult


@dataclass(frozen=True, slots=True)
class GoldWriteRequest:
    """Normalized request payload for one standard Gold write."""

    table_name: str
    records: list[GoldRecord]
    schema: object
    primary_keys: list[str] | None = None
    mode: str = "overwrite"
    partition_cols: list[str] | None = None
    scd_config: ScdConfig | None = None
    column_order: list[str] | None = None
    ingestion_ts: datetime | None = None
    run_id: RunID | None = None
    silver_refs: list[SilverWriteResult] | None = None
    contract_version: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedGoldWriteContext:
    """Prepared pre-write state shared by Gold write phases."""

    table_name: str
    table_path: str
    validated_mode: GoldWriteMode


@dataclass(frozen=True, slots=True)
class GoldWriteDispatchContext:
    """Prepared dispatch state carried into Gold IO mode routing."""

    prepared: PreparedGoldWriteContext
    request: GoldWriteRequest


@dataclass(frozen=True, slots=True)
class GoldWritePostwriteContext:
    """Post-write data passed through Gold audit and metadata stages."""

    prepared: PreparedGoldWriteContext
    records: list[GoldRecord]
    ingestion_ts: datetime | None
    run_id: RunID | None
    scd_config: ScdConfig | None
    silver_refs: list[SilverWriteResult] | None
    schema: object


class _GoldWritePreparationHostProtocol(Protocol):
    """Typed host contract for Gold pre-write validation and path resolution."""

    def _validate_write_mode(self, mode: str) -> GoldWriteMode: ...

    def _validate_records(self, records: list[GoldRecord]) -> None: ...

    def _validate_scd2_requirements(
        self,
        mode: GoldWriteMode,
        scd_config: ScdConfig | None,
        ingestion_ts: datetime | None,
    ) -> None: ...

    def _validate_schema_strict(
        self,
        schema: object,
        contract_version: str | None = None,
    ) -> None: ...

    async def _validate_records_against_schema(
        self,
        records: list[GoldRecord],
        schema: object,
        contract_version: str | None = None,
    ) -> None: ...

    def _resolve_table_path(self, table_name: str) -> str: ...


class _GoldWritePostwriteHostProtocol(Protocol):
    """Typed host contract for Gold post-write side effects."""

    _audit: AuditPort | None

    async def _log_gold_audit(
        self,
        table_name: str,
        records: list[GoldRecord],
        mode: GoldWriteMode,
        ingestion_ts: datetime | None,
        run_id: RunID | None,
    ) -> None: ...

    async def _write_gold_metadata(
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
        gold_schema: object,
    ) -> None: ...


def normalize_scd_config(
    scd_config: ScdConfig,
    primary_keys: list[str] | None,
) -> ScdConfig:
    """Return the already-normalized domain SCD config."""
    del primary_keys
    return scd_config


def set_gold_write_span_attributes(
    span: Any,  # Any: tracing SDK span protocol is runtime-provided
    table_name: str,
    mode: str,
    record_count: int,
) -> None:
    """Set standard tracing attributes for one Gold write span."""
    span.set_attribute("table_name", table_name)
    span.set_attribute("mode", mode)
    span.set_attribute("record_count", record_count)


async def prepare_gold_write(
    host: _GoldWritePreparationHostProtocol,
    *,
    table_name: str,
    records: list[GoldRecord],
    mode: str,
    schema: object,
    scd_config: ScdConfig | None,
    ingestion_ts: datetime | None,
    contract_version: str | None = None,
) -> PreparedGoldWriteContext:
    """Validate one Gold write request and resolve target path."""
    validated_mode = host._validate_write_mode(mode)
    host._validate_records(records)
    host._validate_scd2_requirements(validated_mode, scd_config, ingestion_ts)
    host._validate_schema_strict(schema, contract_version=contract_version)
    await host._validate_records_against_schema(
        records,
        schema,
        contract_version=contract_version,
    )
    return PreparedGoldWriteContext(
        table_name=table_name,
        table_path=host._resolve_table_path(table_name),
        validated_mode=validated_mode,
    )


async def post_write_gold(
    host: _GoldWritePostwriteHostProtocol,
    context: GoldWritePostwriteContext,
) -> None:
    """Run Gold audit and metadata side effects after a successful write."""
    prepared = context.prepared
    if host._audit:
        await host._log_gold_audit(
            table_name=prepared.table_name,
            records=context.records,
            mode=prepared.validated_mode,
            ingestion_ts=context.ingestion_ts,
            run_id=context.run_id,
        )

    await host._write_gold_metadata(
        table_path=prepared.table_path,
        table_name=prepared.table_name,
        records=context.records,
        mode=prepared.validated_mode,
        scd_config=context.scd_config,
        ingestion_ts=context.ingestion_ts,
        run_id=context.run_id,
        silver_refs=context.silver_refs,
        gold_schema=context.schema,
    )


__all__ = [
    "GoldWriteDispatchContext",
    "GoldWritePostwriteContext",
    "GoldWriteRequest",
    "PreparedGoldWriteContext",
    "normalize_scd_config",
    "post_write_gold",
    "prepare_gold_write",
    "set_gold_write_span_attributes",
]
