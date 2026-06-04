"""Finalization request models and coercion for Silver write operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BatchID, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

__all__ = [
    "_SilverWriteFinalizationPreparationRequest",
    "_SilverWriteResultFinalizationRequest",
    "_coerce_request_fields",
    "_coerce_silver_write_finalization_preparation_request",
    "_coerce_silver_write_result_finalization_request",
]


@dataclass(frozen=True, slots=True)
class _SilverWriteFinalizationPreparationRequest:
    """Normalized request payload for finalization context preparation."""

    table_name: str
    records: list[BronzeRecord]
    table_path: str
    started_at: datetime
    start_perf: float
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None
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
    started_at: datetime
    start_perf: float
    quarantined_count: int | None = None
    validation_errors: tuple[str, ...] | None = None


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
                f"{method_name} got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value

    allowed_fields = frozenset({*positional_fields, *tuple(defaults)})
    unexpected_fields = sorted(set(resolved_kwargs) - allowed_fields)
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(
            f"{method_name} got unexpected keyword arguments: {unexpected}"
        )

    missing_fields = [
        field_name
        for field_name in required_fields
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"{method_name} missing required arguments: {missing}")

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
                "_SilverWriteResultFinalizationRequest cannot be combined "
                "with legacy args/kwargs"
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
