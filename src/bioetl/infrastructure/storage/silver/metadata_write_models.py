"""Standard Silver metadata write request models and coercion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bioetl.domain.medallion import SilverWriteMode
from bioetl.domain.types import BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics

__all__ = [
    "_SilverMetadataWriteRequest",
    "_coerce_silver_metadata_write_request",
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
