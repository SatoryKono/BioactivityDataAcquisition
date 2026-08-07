"""Shared deduplication helpers for infrastructure adapter fetch flows."""

from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator, Iterable, Iterator
from typing import TYPE_CHECKING, Literal

from bioetl.domain.types import BronzeRecord

__all__ = [
    "async_iter_deduplicated_records",
    "build_record_dedup_key",
    "compute_composite_dedup_key",
    "deduplicate_preserving_order",
    "is_duplicate_record",
    "is_new_record",
    "iter_deduplicated_records",
    "register_record_dedup_key",
]

RecordDedupRegistration = Literal["new", "duplicate", "missing_key"]

if TYPE_CHECKING:
    from collections.abc import Callable

    from bioetl.domain.ports import LoggerPort as _DuplicateLoggerPort
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.adapters.base_metrics import (
        AdapterMetricsRecorder as _DuplicateMetricsPort,
    )
else:
    _DuplicateLoggerPort = object
    _DuplicateMetricsPort = object


def deduplicate_preserving_order(values: Iterable[str]) -> list[str]:
    """Return unique values while preserving the original order."""
    unique_values: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        if value in seen_values:
            continue
        seen_values.add(value)
        unique_values.append(value)
    return unique_values


def iter_deduplicated_records(
    records: Iterable[BronzeRecord],
    *,
    seen_keys: set[str],
    primary_field: str,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
    entity_type: str | None = None,
    logger: _DuplicateLoggerPort | None = None,
    metrics: _DuplicateMetricsPort | None = None,
    log_context: dict[str, object] | None = None,
) -> Iterator[BronzeRecord]:
    """Yield records while skipping duplicates for the configured key semantics."""
    for record in records:
        status = register_record_dedup_key(
            record=record,
            seen_keys=seen_keys,
            primary_field=primary_field,
            composite_fields=composite_fields,
            composite_key_builder=composite_key_builder,
            entity_type=entity_type,
            logger=logger,
            metrics=metrics,
            log_context=log_context,
        )
        if status == "duplicate":
            continue
        yield record


async def async_iter_deduplicated_records(
    records: AsyncIterable[BronzeRecord],
    *,
    seen_keys: set[str],
    primary_field: str,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
    entity_type: str | None = None,
    logger: _DuplicateLoggerPort | None = None,
    metrics: _DuplicateMetricsPort | None = None,
    log_context: dict[str, object] | None = None,
) -> AsyncIterator[BronzeRecord]:
    """Yield async records while skipping duplicates for the configured key semantics."""
    async for record in records:
        status = register_record_dedup_key(
            record=record,
            seen_keys=seen_keys,
            primary_field=primary_field,
            composite_fields=composite_fields,
            composite_key_builder=composite_key_builder,
            entity_type=entity_type,
            logger=logger,
            metrics=metrics,
            log_context=log_context,
        )
        if status == "duplicate":
            continue
        yield record


def compute_composite_dedup_key(
    record: JsonDict,
    composite_fields: tuple[str, ...],
) -> str:
    """Serialize a composite deduplication key using pipe-joined field values."""
    parts = []
    for field in composite_fields:
        value = record.get(field, "")
        parts.append(str(value) if value is not None else "")
    return "|".join(parts)


def build_record_dedup_key(
    record: BronzeRecord,
    primary_field: str,
    *,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
) -> str | None:
    """Build the deduplication key for a record.

    Returns ``None`` when the record does not contain a usable key and should
    therefore remain eligible for downstream handling rather than being dropped.
    """
    # One or more composite fields uses the composite path (do not silently
    # fall back to primary when composite_fields is a one-element tuple).
    if composite_fields is not None and len(composite_fields) >= 1:
        if composite_key_builder is None:
            composite_key = compute_composite_dedup_key(record, composite_fields)
        else:
            composite_key = composite_key_builder(record, composite_fields)
        empty_key = "|".join([""] * len(composite_fields))
        return (
            None if not composite_key or composite_key == empty_key else composite_key
        )

    record_id = str(record.get(primary_field, ""))
    return record_id or None


def register_record_dedup_key(
    *,
    record: BronzeRecord,
    seen_keys: set[str],
    primary_field: str,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
    entity_type: str | None = None,
    logger: _DuplicateLoggerPort | None = None,
    metrics: _DuplicateMetricsPort | None = None,
    log_context: dict[str, object] | None = None,
) -> RecordDedupRegistration:
    """Register a record dedup key and return its registration status."""
    dedup_key = build_record_dedup_key(
        record,
        primary_field,
        composite_fields=composite_fields,
        composite_key_builder=composite_key_builder,
    )
    if dedup_key is None:
        return "missing_key"
    if dedup_key not in seen_keys:
        seen_keys.add(dedup_key)
        return "new"

    if logger is not None:
        duplicate_context: dict[str, object] = {
            "entity_type": entity_type,
        }
        if composite_fields is not None and len(composite_fields) > 1:
            duplicate_context["pk_fields"] = composite_fields
            duplicate_context["composite_key"] = dedup_key
        else:
            duplicate_context["pk_field"] = primary_field
            duplicate_context["record_id"] = dedup_key
        if log_context:
            duplicate_context.update(log_context)
        logger.debug("skipping_duplicate_record", **duplicate_context)

    if metrics is not None and entity_type is not None:
        metrics.record_dropped_duplicates(entity_type)
    return "duplicate"


def is_duplicate_record(
    *,
    record: BronzeRecord,
    seen_keys: set[str],
    primary_field: str,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
    entity_type: str | None = None,
    logger: _DuplicateLoggerPort | None = None,
    metrics: _DuplicateMetricsPort | None = None,
    log_context: dict[str, object] | None = None,
) -> bool:
    """Register the key and report whether it was already present."""
    return (
        register_record_dedup_key(
            record=record,
            seen_keys=seen_keys,
            primary_field=primary_field,
            composite_fields=composite_fields,
            composite_key_builder=composite_key_builder,
            entity_type=entity_type,
            logger=logger,
            metrics=metrics,
            log_context=log_context,
        )
        == "duplicate"
    )


def is_new_record(
    *,
    record: BronzeRecord,
    seen_keys: set[str],
    primary_field: str,
    composite_fields: tuple[str, ...] | None = None,
    composite_key_builder: Callable[[JsonDict, tuple[str, ...]], str] | None = None,
    entity_type: str | None = None,
    logger: _DuplicateLoggerPort | None = None,
    metrics: _DuplicateMetricsPort | None = None,
    log_context: dict[str, object] | None = None,
) -> bool:
    """Register the key and report whether it is new."""
    return (
        register_record_dedup_key(
            record=record,
            seen_keys=seen_keys,
            primary_field=primary_field,
            composite_fields=composite_fields,
            composite_key_builder=composite_key_builder,
            entity_type=entity_type,
            logger=logger,
            metrics=metrics,
            log_context=log_context,
        )
        == "new"
    )
