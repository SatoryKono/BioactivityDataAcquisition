"""Deterministic Silver deduplication helpers for retention operations."""

from __future__ import annotations

from collections.abc import Sequence

from deltalake.exceptions import CommitFailedError
from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

from bioetl.domain.exceptions import DeltaWriteConflictError, TableNotFoundError
from bioetl.domain.normalization import (
    normalize_hash_identity_record,
    serialize_hash_identity_canonical_json,
)
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.settings_api import get_settings

DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS = 60.0
TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS = 10.0


def resolve_deduplication_timeout_seconds() -> float:
    """Return the centralized dedup timeout setting with a safe fallback."""
    settings = get_settings()
    configured_timeout = float(
        getattr(
            settings,
            "silver_dedup_timeout_seconds",
            DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS,
        )
    )
    if (
        getattr(settings, "test_mode", False)
        and configured_timeout >= DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS
    ):
        return TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
    return configured_timeout


def primary_key_tuple(
    row: JsonDict,
    primary_keys: Sequence[str],
) -> tuple[object, ...]:
    """Return one stable primary-key tuple for a Delta row."""
    return tuple(row.get(key) for key in primary_keys)


def content_identity(row: JsonDict) -> str:
    """Return deterministic content identity for one Delta row."""
    content_hash = row.get("content_hash")
    if content_hash is not None:
        return str(content_hash)
    return serialize_hash_identity_canonical_json(normalize_hash_identity_record(row))


def deduplicate_delta_rows(
    table_path: str,
    primary_keys: Sequence[str],
) -> int:
    """Deduplicate one Delta table using deterministic content identity."""
    import pyarrow as pa
    from deltalake import DeltaTable as runtime_delta_table
    from deltalake import write_deltalake

    try:
        table = runtime_delta_table(table_path).to_pyarrow_table()
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc
    total_before = table.num_rows
    if total_before == 0:
        return 0

    ranked_rows = sorted(
        (
            (
                primary_key_tuple(row, primary_keys),
                content_identity(row),
                row,
            )
            for row in table.to_pylist()
        ),
        key=lambda item: (item[0], item[1]),
    )

    seen_exact_keys: set[tuple[tuple[object, ...], str]] = set()
    seen_primary_keys: set[tuple[object, ...]] = set()
    deduped_rows: list[JsonDict] = []
    for primary_key, row_identity, row in ranked_rows:
        exact_key = (primary_key, row_identity)
        if exact_key in seen_exact_keys:
            continue
        seen_exact_keys.add(exact_key)
        if primary_key in seen_primary_keys:
            continue
        seen_primary_keys.add(primary_key)
        deduped_rows.append(row)

    duplicates_removed = total_before - len(deduped_rows)
    if duplicates_removed > 0:
        try:
            write_deltalake(
                table_or_uri=table_path,
                data=pa.Table.from_pylist(deduped_rows, schema=table.schema),
                mode="overwrite",
                schema_mode="overwrite",
            )
        except CommitFailedError as exc:
            raise DeltaWriteConflictError(
                table_path=table_path,
                operation="deduplicate",
            ) from exc
    return int(duplicates_removed)


__all__ = [
    "DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS",
    "content_identity",
    "deduplicate_delta_rows",
    "primary_key_tuple",
    "resolve_deduplication_timeout_seconds",
]
