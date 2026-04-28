"""Request models and coercion helpers for Silver metadata operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.models.metadata import SilverMetadata
from bioetl.domain.types import BatchID, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.infrastructure.storage.silver.merged_request_support import (
    _build_merged_write_request,
)

__all__ = [
    "_PreparedSilverMetadataWriteOperation",
    "_PreparedSilverWriteFinalizationContext",
    "_ResolvedSilverMetadataContext",
    "_SilverMergedMetadataWriteRequest",
    "_SilverMetadataWriteRequest",
    "_SilverWriteFinalizationPreparationRequest",
    "_SilverWriteResultFinalizationRequest",
    "_build_silver_merged_metadata_write_request",
    "_coerce_silver_metadata_write_request",
    "_coerce_silver_write_finalization_preparation_request",
    "_coerce_silver_write_result_finalization_request",
]


@dataclass(frozen=True, slots=True)
class _SilverMetadataWriteRequest:
    """Normalized request payload for one standard Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None = None
    dq_metrics: BatchDQMetrics | None = None
    dq_report_path: str | None = None
    partition_by: list[str] | None = None
    source_batch_ids: list[str] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    version_after: int | None = None


_SILVER_METADATA_WRITE_POSITIONAL_FIELDS = (
    "table_path",
    "table_name",
    "records",
    "primary_keys",
    "mode",
    "bronze_refs",
    "dq_metrics",
    "dq_report_path",
    "partition_by",
    "source_batch_ids",
    "started_at",
    "completed_at",
    "version_after",
)
_SILVER_METADATA_WRITE_REQUIRED_FIELDS = (
    "table_path",
    "table_name",
    "records",
    "primary_keys",
    "mode",
)
_SILVER_METADATA_WRITE_DEFAULTS: dict[str, object] = {
    "bronze_refs": None,
    "dq_metrics": None,
    "dq_report_path": None,
    "partition_by": None,
    "source_batch_ids": None,
    "started_at": None,
    "completed_at": None,
    "version_after": None,
}
_SILVER_METADATA_WRITE_ALLOWED_FIELDS = frozenset(
    {
        *_SILVER_METADATA_WRITE_POSITIONAL_FIELDS,
        *tuple(_SILVER_METADATA_WRITE_DEFAULTS),
    }
)


def _coerce_silver_metadata_write_request(
    request: _SilverMetadataWriteRequest | str | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> _SilverMetadataWriteRequest:
    """Normalize legacy or request-style Silver metadata write arguments."""
    resolved_kwargs = dict(kwargs or {})
    if isinstance(request, _SilverMetadataWriteRequest):
        if args or resolved_kwargs:
            raise TypeError(
                "_SilverMetadataWriteRequest cannot be combined with legacy args/kwargs"
            )
        return request

    legacy_values = list(args) if request is None else [request, *args]
    if len(legacy_values) > len(_SILVER_METADATA_WRITE_POSITIONAL_FIELDS):
        raise TypeError(
            "_write_silver_metadata() received too many positional arguments"
        )

    for field_name, value in zip(
        _SILVER_METADATA_WRITE_POSITIONAL_FIELDS,
        legacy_values,
        strict=False,
    ):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"_write_silver_metadata() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value

    unexpected_fields = sorted(
        set(resolved_kwargs) - _SILVER_METADATA_WRITE_ALLOWED_FIELDS
    )
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(
            f"_write_silver_metadata() got unexpected keyword arguments: {unexpected}"
        )

    missing_fields = [
        field_name
        for field_name in _SILVER_METADATA_WRITE_REQUIRED_FIELDS
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(
            f"_write_silver_metadata() missing required arguments: {missing}"
        )

    for field_name, default in _SILVER_METADATA_WRITE_DEFAULTS.items():
        resolved_kwargs.setdefault(field_name, default)

    return _SilverMetadataWriteRequest(
        table_path=resolved_kwargs["table_path"],  # type: ignore[arg-type]
        table_name=resolved_kwargs["table_name"],  # type: ignore[arg-type]
        records=resolved_kwargs["records"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        mode=resolved_kwargs["mode"],  # type: ignore[arg-type]
        bronze_refs=resolved_kwargs["bronze_refs"],  # type: ignore[arg-type]
        dq_metrics=resolved_kwargs["dq_metrics"],  # type: ignore[arg-type]
        dq_report_path=resolved_kwargs["dq_report_path"],  # type: ignore[arg-type]
        partition_by=resolved_kwargs["partition_by"],  # type: ignore[arg-type]
        source_batch_ids=resolved_kwargs["source_batch_ids"],  # type: ignore[arg-type]
        started_at=resolved_kwargs["started_at"],  # type: ignore[arg-type]
        completed_at=resolved_kwargs["completed_at"],  # type: ignore[arg-type]
        version_after=resolved_kwargs["version_after"],  # type: ignore[arg-type]
    )


@dataclass(frozen=True, slots=True)
class _SilverMergedMetadataWriteRequest:
    """Normalized request payload for one merged Silver metadata write."""

    table_path: str
    table_name: str
    records: list[BronzeRecord]
    primary_keys: list[str]
    completed_at: datetime | None = None
    run_id: str | None = None
    sources_used: list[str] | None = None


def _build_silver_merged_metadata_write_request(
    *,
    table_path: str,
    table_name: str,
    records: list[BronzeRecord],
    primary_keys: list[str],
    completed_at: datetime | None = None,
    run_id: str | None = None,
    sources_used: list[str] | None = None,
) -> _SilverMergedMetadataWriteRequest:
    """Build the canonical request for merged Silver metadata sidecar writes."""
    return _build_merged_write_request(
        _SilverMergedMetadataWriteRequest,
        table_path=table_path,
        table_name=table_name,
        records=records,
        primary_keys=primary_keys,
        completed_at=completed_at,
        run_id=run_id,
        sources_used=sources_used,
    )


@dataclass(frozen=True, slots=True)
class _PreparedSilverMetadataWriteOperation:
    """Prepared Silver metadata operation carried into sidecar execution."""

    request: _SilverMetadataWriteRequest | _SilverMergedMetadataWriteRequest
    provider_name: str
    entity_name: str
    metadata: SilverMetadata
    lineage_fragment: LineageGraphFragment | None = None


@dataclass(frozen=True, slots=True)
class _ResolvedSilverMetadataContext:
    """Shared provider/entity/version context for Silver metadata preparation."""

    provider_name: str
    entity_name: str
    version_after: int | None


@dataclass(frozen=True, slots=True)
class _PreparedSilverWriteFinalizationContext:
    """Prepared metadata/result context for one completed Silver write."""

    dq_metrics: BatchDQMetrics
    version_after: int | None
    completed_at: datetime


@dataclass(frozen=True, slots=True)
class _SilverWriteFinalizationPreparationRequest:
    """Normalized request payload for finalization context preparation."""

    table_name: str
    records: list[BronzeRecord]
    table_path: str
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None
    started_at: datetime | None = None
    start_perf: float | None = None
    primary_keys: list[str] | None = None
    validated_mode: SilverWriteMode | None = None


@dataclass(frozen=True, slots=True)
class _SilverWriteResultFinalizationRequest:
    """Normalized request payload for final Silver write result assembly."""

    table_name: str
    records: list[BronzeRecord]
    table_path: str
    primary_keys: list[str]
    validated_mode: SilverWriteMode
    bronze_refs: list[BronzeWriteResult] | None
    partition_cols: list[str] | None
    source_batch_id: BatchID | None
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None
    started_at: datetime | None = None
    start_perf: float | None = None


_FINALIZATION_PREPARATION_FIELDS = (
    "table_name",
    "records",
    "table_path",
    "quarantined_count",
    "validation_errors",
    "started_at",
    "start_perf",
    "primary_keys",
    "validated_mode",
)
_FINALIZATION_PREPARATION_REQUIRED_FIELDS = (
    "table_name",
    "records",
    "table_path",
    "started_at",
    "start_perf",
)
_FINALIZATION_PREPARATION_DEFAULTS: dict[str, object] = {
    "quarantined_count": None,
    "validation_errors": None,
    "primary_keys": None,
    "validated_mode": None,
}

_FINALIZATION_RESULT_FIELDS = (
    "table_name",
    "records",
    "table_path",
    "primary_keys",
    "validated_mode",
    "bronze_refs",
    "partition_cols",
    "source_batch_id",
    "quarantined_count",
    "validation_errors",
    "started_at",
    "start_perf",
)
_FINALIZATION_RESULT_REQUIRED_FIELDS = (
    "table_name",
    "records",
    "table_path",
    "primary_keys",
    "validated_mode",
    "bronze_refs",
    "partition_cols",
    "source_batch_id",
    "started_at",
    "start_perf",
)
_FINALIZATION_RESULT_DEFAULTS: dict[str, object] = {
    "quarantined_count": None,
    "validation_errors": None,
}


def _coerce_request_fields(
    *,
    method_name: str,
    request: object | None,
    args: tuple[object, ...],
    kwargs: dict[str, object] | None,
    positional_fields: tuple[str, ...],
    required_fields: tuple[str, ...],
    defaults: dict[str, object],
) -> dict[str, object]:
    """Normalize legacy positional/keyword calls into one request field mapping."""
    resolved_kwargs = dict(kwargs or {})
    legacy_values = list(args) if request is None else [request, *args]
    if len(legacy_values) > len(positional_fields):
        raise TypeError(f"{method_name}() received too many positional arguments")

    for field_name, value in zip(positional_fields, legacy_values, strict=False):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"{method_name}() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value

    allowed_fields = frozenset({*positional_fields, *tuple(defaults)})
    unexpected_fields = sorted(set(resolved_kwargs) - allowed_fields)
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(
            f"{method_name}() got unexpected keyword arguments: {unexpected}"
        )

    missing_fields = [
        field_name
        for field_name in required_fields
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"{method_name}() missing required arguments: {missing}")

    for field_name, default in defaults.items():
        resolved_kwargs.setdefault(field_name, default)
    return resolved_kwargs


def _coerce_silver_write_finalization_preparation_request(
    request: _SilverWriteFinalizationPreparationRequest | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> _SilverWriteFinalizationPreparationRequest:
    """Normalize legacy or request-style finalization preparation arguments."""
    if isinstance(request, _SilverWriteFinalizationPreparationRequest):
        if args or kwargs:
            raise TypeError(
                "_SilverWriteFinalizationPreparationRequest cannot be combined "
                "with legacy args/kwargs"
            )
        return request

    resolved_kwargs = _coerce_request_fields(
        method_name="_prepare_silver_write_finalization_context",
        request=request,
        args=args,
        kwargs=kwargs,
        positional_fields=_FINALIZATION_PREPARATION_FIELDS,
        required_fields=_FINALIZATION_PREPARATION_REQUIRED_FIELDS,
        defaults=_FINALIZATION_PREPARATION_DEFAULTS,
    )
    return _SilverWriteFinalizationPreparationRequest(
        table_name=resolved_kwargs["table_name"],  # type: ignore[arg-type]
        records=resolved_kwargs["records"],  # type: ignore[arg-type]
        table_path=resolved_kwargs["table_path"],  # type: ignore[arg-type]
        quarantined_count=resolved_kwargs["quarantined_count"],  # type: ignore[arg-type]
        validation_errors=resolved_kwargs["validation_errors"],  # type: ignore[arg-type]
        started_at=resolved_kwargs["started_at"],  # type: ignore[arg-type]
        start_perf=resolved_kwargs["start_perf"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        validated_mode=resolved_kwargs["validated_mode"],  # type: ignore[arg-type]
    )


def _coerce_silver_write_result_finalization_request(
    request: _SilverWriteResultFinalizationRequest | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: dict[str, object] | None = None,
) -> _SilverWriteResultFinalizationRequest:
    """Normalize legacy or request-style final result arguments."""
    if isinstance(request, _SilverWriteResultFinalizationRequest):
        if args or kwargs:
            raise TypeError(
                "_SilverWriteResultFinalizationRequest cannot be combined with "
                "legacy args/kwargs"
            )
        return request

    resolved_kwargs = _coerce_request_fields(
        method_name="_finalize_silver_write_result",
        request=request,
        args=args,
        kwargs=kwargs,
        positional_fields=_FINALIZATION_RESULT_FIELDS,
        required_fields=_FINALIZATION_RESULT_REQUIRED_FIELDS,
        defaults=_FINALIZATION_RESULT_DEFAULTS,
    )
    return _SilverWriteResultFinalizationRequest(
        table_name=resolved_kwargs["table_name"],  # type: ignore[arg-type]
        records=resolved_kwargs["records"],  # type: ignore[arg-type]
        table_path=resolved_kwargs["table_path"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        validated_mode=resolved_kwargs["validated_mode"],  # type: ignore[arg-type]
        bronze_refs=resolved_kwargs["bronze_refs"],  # type: ignore[arg-type]
        partition_cols=resolved_kwargs["partition_cols"],  # type: ignore[arg-type]
        source_batch_id=resolved_kwargs["source_batch_id"],  # type: ignore[arg-type]
        quarantined_count=resolved_kwargs["quarantined_count"],  # type: ignore[arg-type]
        validation_errors=resolved_kwargs["validation_errors"],  # type: ignore[arg-type]
        started_at=resolved_kwargs["started_at"],  # type: ignore[arg-type]
        start_perf=resolved_kwargs["start_perf"],  # type: ignore[arg-type]
    )
