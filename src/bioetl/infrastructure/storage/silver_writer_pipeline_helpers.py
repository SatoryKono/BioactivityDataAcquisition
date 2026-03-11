"""Pipeline helper objects for Silver write orchestration."""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Literal

import pyarrow as pa

from bioetl.infrastructure.storage.silver_writer_delta_mixin import (
    _DeltaWriteRequest,
)
from bioetl.infrastructure.storage.silver_writer_validation_mixin import (
    _PreparedSilverWritePayload,
)

if TYPE_CHECKING:
    from bioetl.domain.config import KeyNullabilityRule
    from bioetl.domain.value_objects.bronze_result import BronzeWriteResult


__all__ = [
    "_SilverWriteExecutionContext",
    "build_delta_write_request",
    "build_silver_write_execution_context",
    "set_silver_write_span_attributes",
]


@dataclass(frozen=True, slots=True)
class _SilverWriteExecutionContext:
    """Immutable execution context carried through the Silver write pipeline."""

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

def set_silver_write_span_attributes(
    span: Any,  # Any: OpenTelemetry span type varies by backend
    *,
    table_name: str,
    mode: str,
    record_count: int,
) -> None:
    """Populate core tracing attributes for a Silver write span."""
    span.set_attribute("table_name", table_name)
    span.set_attribute("mode", mode)
    span.set_attribute("record_count", record_count)


def build_silver_write_execution_context(
    *,
    table_name: str,
    primary_keys: list[str],
    schema: pa.Schema,
    mode: str,
    partition_cols: list[str] | None,
    on_schema_mismatch: Literal["error", "evolve", "ignore"],
    column_order: list[str] | None,
    bronze_refs: list[BronzeWriteResult] | None,
    key_nullability_rules: list[KeyNullabilityRule] | None,
    started_at: datetime,
    start_perf: float,
    span: Any,  # Any: OpenTelemetry span type varies by backend
) -> _SilverWriteExecutionContext:
    """Build immutable execution context for the Silver write pipeline."""
    return _SilverWriteExecutionContext(
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


def build_delta_write_request(
    *,
    ctx: _SilverWriteExecutionContext,
    payload: _PreparedSilverWritePayload,
) -> _DeltaWriteRequest:
    """Create the Delta dispatch request from prepared payload and execution context."""
    return _DeltaWriteRequest(
        validated_mode=payload.validated_mode,
        table_path=payload.table_path,
        arrow_data=payload.arrow_data,
        primary_keys=ctx.primary_keys,
        partition_cols=ctx.partition_cols,
    )
