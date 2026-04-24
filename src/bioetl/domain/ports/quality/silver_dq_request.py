"""Structured request contract for Silver DQ analysis."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from datetime import datetime

    from bioetl.domain.ports.quality.dq_config import SilverDQConfigPort

DataContainer = (
    Any  # Any: polars.DataFrame | pyarrow.Table (avoids infra import in domain)
)


@dataclass(frozen=True, slots=True)
class SilverDQAnalyzeRequest:
    """Canonical Silver DQ analysis request shared across report seams."""

    data: DataContainer
    run_id: str
    pipeline: str
    target_table: str
    source_batch_ids: list[str]
    config: SilverDQConfigPort
    timestamp: datetime
    primary_keys: list[str]
    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20
    input_record_count: int | None = None
    quarantined_count: int = 0
    previous_schema: dict[str, str] | None = None
    key_nullability_rules: list[JsonDict] | None = None


_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS = (
    "data",
    "run_id",
    "pipeline",
    "target_table",
    "source_batch_ids",
    "config",
    "timestamp",
    "primary_keys",
    "soft_fail_threshold",
    "hard_fail_threshold",
    "input_record_count",
    "quarantined_count",
    "previous_schema",
    "key_nullability_rules",
)
_SILVER_DQ_ANALYZE_REQUIRED_FIELDS = (
    "data",
    "run_id",
    "pipeline",
    "target_table",
    "source_batch_ids",
    "config",
    "timestamp",
    "primary_keys",
)
_SILVER_DQ_ANALYZE_DEFAULTS: dict[str, object] = {
    "soft_fail_threshold": 0.05,
    "hard_fail_threshold": 0.20,
    "input_record_count": None,
    "quarantined_count": 0,
    "previous_schema": None,
    "key_nullability_rules": None,
}
_SILVER_DQ_ANALYZE_ALLOWED_FIELDS = frozenset(
    {*_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS, *tuple(_SILVER_DQ_ANALYZE_DEFAULTS)}
)


def coerce_silver_dq_analyze_request(
    request: SilverDQAnalyzeRequest | DataContainer | None = None,
    *,
    args: tuple[object, ...] = (),
    kwargs: Mapping[str, object] | None = None,
) -> SilverDQAnalyzeRequest:
    """Normalize legacy or request-style Silver DQ analysis arguments."""
    if isinstance(request, SilverDQAnalyzeRequest):
        if args or kwargs:
            raise TypeError(
                "SilverDQAnalyzeRequest cannot be combined with legacy args/kwargs"
            )
        return request
    resolved_kwargs = _resolve_silver_dq_analyze_kwargs(
        request=request,
        args=args,
        kwargs=kwargs,
    )
    return SilverDQAnalyzeRequest(
        data=resolved_kwargs["data"],
        run_id=resolved_kwargs["run_id"],  # type: ignore[arg-type]
        pipeline=resolved_kwargs["pipeline"],  # type: ignore[arg-type]
        target_table=resolved_kwargs["target_table"],  # type: ignore[arg-type]
        source_batch_ids=resolved_kwargs["source_batch_ids"],  # type: ignore[arg-type]
        config=resolved_kwargs["config"],  # type: ignore[arg-type]
        timestamp=resolved_kwargs["timestamp"],  # type: ignore[arg-type]
        primary_keys=resolved_kwargs["primary_keys"],  # type: ignore[arg-type]
        soft_fail_threshold=resolved_kwargs["soft_fail_threshold"],  # type: ignore[arg-type]
        hard_fail_threshold=resolved_kwargs["hard_fail_threshold"],  # type: ignore[arg-type]
        input_record_count=resolved_kwargs["input_record_count"],  # type: ignore[arg-type]
        quarantined_count=resolved_kwargs["quarantined_count"],  # type: ignore[arg-type]
        previous_schema=resolved_kwargs["previous_schema"],  # type: ignore[arg-type]
        key_nullability_rules=resolved_kwargs["key_nullability_rules"],  # type: ignore[arg-type]
    )


def _resolve_silver_dq_analyze_kwargs(
    *,
    request: SilverDQAnalyzeRequest | DataContainer | None,
    args: tuple[object, ...],
    kwargs: Mapping[str, object] | None,
) -> dict[str, object]:
    resolved_kwargs = dict(kwargs or {})
    legacy_values = list(args) if request is None else [request, *args]
    _merge_silver_dq_analyze_legacy_values(resolved_kwargs, legacy_values)
    _raise_on_unexpected_silver_dq_fields(resolved_kwargs)
    _raise_on_missing_silver_dq_fields(resolved_kwargs)
    for field_name, default in _SILVER_DQ_ANALYZE_DEFAULTS.items():
        resolved_kwargs.setdefault(field_name, default)
    return resolved_kwargs


def _merge_silver_dq_analyze_legacy_values(
    resolved_kwargs: dict[str, object],
    legacy_values: list[object],
) -> None:
    if len(legacy_values) > len(_SILVER_DQ_ANALYZE_POSITIONAL_FIELDS):
        raise TypeError("analyze() received too many positional arguments")
    positional_fields = _SILVER_DQ_ANALYZE_POSITIONAL_FIELDS[: len(legacy_values)]
    for field_name, value in zip(positional_fields, legacy_values, strict=False):
        if field_name in resolved_kwargs:
            raise TypeError(
                f"analyze() got multiple values for argument '{field_name}'"
            )
        resolved_kwargs[field_name] = value


def _raise_on_unexpected_silver_dq_fields(resolved_kwargs: dict[str, object]) -> None:
    unexpected_fields = sorted(set(resolved_kwargs) - _SILVER_DQ_ANALYZE_ALLOWED_FIELDS)
    if unexpected_fields:
        unexpected = ", ".join(unexpected_fields)
        raise TypeError(f"analyze() got unexpected keyword arguments: {unexpected}")


def _raise_on_missing_silver_dq_fields(resolved_kwargs: dict[str, object]) -> None:
    missing_fields = [
        field_name
        for field_name in _SILVER_DQ_ANALYZE_REQUIRED_FIELDS
        if field_name not in resolved_kwargs
    ]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise TypeError(f"analyze() missing required arguments: {missing}")


__all__ = ["SilverDQAnalyzeRequest", "coerce_silver_dq_analyze_request"]
