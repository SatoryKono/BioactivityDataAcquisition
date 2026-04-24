"""Record-level validation helpers for Silver write preparation."""

from __future__ import annotations

import re
from typing import Any

import pyarrow as pa

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.types import BronzeRecord

__all__ = [
    "_deduplicate_by_primary_keys_impl",
    "_pipeline_name_from_table_name",
    "_validate_records",
    "_validate_silver_pandera",
]

_VERSIONED_TABLE_SUFFIX_RE = re.compile(r"__v\d+_\d+_\d+$")


# Any: Silver write batches preserve heterogeneous BronzeRecord-compatible values.
def _primary_key_tuple(
    record: BronzeRecord,
    primary_keys: list[str],
) -> tuple[object, ...]:
    """Return one stable primary-key tuple for a batch record."""
    return tuple(record.get(primary_key) for primary_key in primary_keys)


# Any: content identity canonicalizes heterogeneous batch payloads.
def _content_identity(
    record: BronzeRecord,
) -> str:
    """Return deterministic content identity for one batch record."""
    content_hash = record.get("content_hash")
    if content_hash is not None:
        return str(content_hash)
    return str(
        serialize_hash_identity_canonical_json(normalize_hash_identity_record(record))
    )


def _pipeline_name_from_table_name(table_name: str) -> str:
    """Derive the canonical pipeline label from a logical or versioned table name."""
    normalized_table = _VERSIONED_TABLE_SUFFIX_RE.sub("", table_name.strip())
    return normalized_table.replace(".", "_").replace("/", "_")


# Any: dedup logic operates on heterogeneous BronzeRecord-compatible rows.
# Any: winner selection preserves original heterogeneous row values.
def _deduplicate_by_primary_keys_impl(
    records: list[BronzeRecord],
    primary_keys: list[str],
) -> list[BronzeRecord]:
    """Deduplicate records by business key using deterministic content identity.

    The current-batch contract mirrors Silver retention compaction:
    - exact duplicate rows for one business key collapse by
      ``(primary_keys, content identity)``
    - conflicting rows for one business key choose the lexicographically
      smallest content identity

    This makes winner selection independent of incoming row order.
    """
    if not primary_keys or not records:
        return records

    ranked_records = sorted(
        (
            (
                _primary_key_tuple(record, primary_keys),
                _content_identity(record),
                record,
            )
            for record in records
        ),
        key=lambda item: (item[0], item[1]),
    )

    seen_exact_keys: set[tuple[tuple[object, ...], str]] = set()
    seen_primary_keys: set[tuple[object, ...]] = set()
    deduplicated: list[BronzeRecord] = []
    for primary_key, content_identity, record in ranked_records:
        exact_key = (primary_key, content_identity)
        if exact_key in seen_exact_keys:
            continue
        seen_exact_keys.add(exact_key)
        if primary_key in seen_primary_keys:
            continue
        seen_primary_keys.add(primary_key)
        deduplicated.append(record)
    return deduplicated


# Any: validation helper accepts SilverWriter host objects and lightweight test doubles.
# Any: validation runs before Pandera coercion on heterogeneous rows.
def _validate_records(
    host: Any,  # Any: validation helper accepts SilverWriter host objects and lightweight test doubles.
    records: list[BronzeRecord],
    table_name: str,
    schema: pa.Schema,
) -> None:
    """Validate core Silver write payload shape before persistence."""
    if not records:
        raise ValueError("No records to write")

    keys = set(records[0].keys())
    optional_missing = [key for key in schema.names if key not in keys]
    if optional_missing:
        host.logger.debug(
            "Optional fields missing in batch",
            table=table_name,
            missing=optional_missing,
        )


# Any: validation helper accepts SilverWriter host objects and lightweight test doubles.
# Any: Pandera validation consumes heterogeneous pre-coercion row payloads.
def _validate_silver_pandera(
    host: Any,  # Any: validation helper accepts SilverWriter host objects and lightweight test doubles.
    records: list[BronzeRecord],
    table_name: str,
) -> None:
    """Validate records using Pandera schema before writing to Silver."""
    schema = getattr(host._silver_validator, "_schema", None)
    schema_columns = getattr(schema, "columns", {})
    preserve_state = "_state" in schema_columns
    cleaned_records = (
        records
        if preserve_state
        else [
            {key: value for key, value in record.items() if key != "_state"}
            for record in records
        ]
    )

    result = host._silver_validator.validate(cleaned_records)
    if not result.valid:
        host.logger.error(
            "Silver Pandera validation failed",
            table=table_name,
            errors=result.errors,
        )
        if host._metrics:
            host._metrics.increment_counter(
                "bioetl_silver_validation_failures_total",
                1,
                {
                    "table": table_name,
                    "pipeline": _pipeline_name_from_table_name(table_name),
                },
            )
        raise SchemaViolationError(table_name, result.errors)
