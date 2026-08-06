"""Deterministic Silver deduplication helpers for retention operations."""

from __future__ import annotations

import platform
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
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow
from bioetl.infrastructure.storage.delta_reader_helpers import (
    FULL_READ_HEAD_LIMIT,
    try_native_delta_row_count,
)

DEFAULT_DEDUPLICATION_TIMEOUT_SECONDS = 60.0
TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS = 10.0
WINDOWS_TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS = 60.0


def resolve_test_mode_deduplication_timeout_seconds() -> float:
    """Return the platform-aware test-mode timeout budget for Silver dedup."""
    # Windows delta-rs overwrite paths can exceed the Linux/WSL budget for the
    # same tiny test tables under suite load.
    if platform.system().lower() == "windows":
        return WINDOWS_TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS
    return TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS


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
        return resolve_test_mode_deduplication_timeout_seconds()
    return configured_timeout


def primary_key_tuple(
    row: JsonDict,
    primary_keys: Sequence[str],
) -> tuple[object, ...]:
    """Return one stable primary-key tuple for a Delta row."""
    return tuple(row.get(key) for key in primary_keys)


def _total_order_component(value: object) -> tuple[int, str]:
    """Map a PK component to a total order for deterministic sorting.

    None and heterogeneous types must not raise TypeError under Python 3
    rich comparisons during dedup ranking.
    """
    if value is None:
        return (0, "")
    return (1, f"{type(value).__name__}:{value!s}")


def primary_key_sort_key(primary_key: tuple[object, ...]) -> tuple[tuple[int, str], ...]:
    """Return a total-order sort key for one primary-key tuple."""
    return tuple(_total_order_component(part) for part in primary_key)


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
        table_handle = runtime_delta_table(table_path)
    except DeltaTableNotFoundError as exc:
        raise TableNotFoundError(table_path) from exc

    dataset = table_handle.to_pyarrow_dataset()
    scanner = dataset.scanner()
    row_count = try_native_delta_row_count(table_handle)
    table = scanner.head(row_count if row_count is not None else FULL_READ_HEAD_LIMIT)
    total_before = table.num_rows
    if total_before == 0:
        return 0

    table_schema = delta_schema_to_pyarrow(table_handle.schema())

    ranked_rows = sorted(
        (
            (
                primary_key_tuple(row, primary_keys),
                content_identity(row),
                row,
            )
            for row in table.to_pylist()
        ),
        key=lambda item: (primary_key_sort_key(item[0]), item[1]),
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
                data=pa.Table.from_pylist(deduped_rows, schema=table_schema),
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
    "TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS",
    "WINDOWS_TEST_MODE_DEDUPLICATION_TIMEOUT_SECONDS",
    "content_identity",
    "deduplicate_delta_rows",
    "primary_key_tuple",
    "resolve_deduplication_timeout_seconds",
    "resolve_test_mode_deduplication_timeout_seconds",
]
