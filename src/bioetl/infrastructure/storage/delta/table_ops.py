# Host attrs/methods provided by concrete composition.
"""Reusable Delta table helper operations."""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast
from urllib.parse import quote, unquote, urlparse

import pyarrow as pa
import pyarrow.parquet as pq
from deltalake import DeltaTable

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow


def _can_use_pyarrow_dataset_scanner(*, platform: str = sys.platform) -> bool:
    """Return whether Delta reads should use the PyArrow dataset scanner path."""
    # On Windows, importing ``pyarrow.dataset`` through ``to_pyarrow_dataset()``
    # can hang long enough to trip E2E timeout guards on local mixed checkouts.
    return platform != "win32"


def resolve_parquet_file_uri(file_uri: str) -> str:
    """Resolve a Delta active-file URI to a local filesystem path when needed."""
    if not file_uri.startswith("file://"):
        return file_uri
    parsed_path = unquote(urlparse(file_uri).path)
    # Windows file URIs look like file:///C:/path -> /C:/path
    if len(parsed_path) >= 3 and parsed_path[0] == "/" and parsed_path[2] == ":":
        return parsed_path[1:]
    return parsed_path


def _read_records_from_active_parquet_files(
    table: DeltaTable,
    columns: list[str] | None = None,
) -> list[BronzeRecord]:
    """Read active Delta files via parquet without native full-table Arrow scans.

    ``DeltaTable.to_pyarrow_table()`` / dataset scanners have been observed to
    hang indefinitely on Windows and some mixed/cloud-synced checkouts. Active
    ``file_uris()`` + ``pyarrow.parquet.read_table`` stays bounded and reliable.
    """
    file_uris = list(table.file_uris())
    if not file_uris:
        return []

    if columns == []:
        count = sum(
            pq.read_metadata(resolve_parquet_file_uri(uri)).num_rows
            for uri in file_uris
        )
        return [{} for _ in range(count)]
    schema = delta_schema_to_pyarrow(table.schema())
    partition_info = _partition_info(table, schema=schema)
    tables = [
        _read_active_file(uri, columns, partition_info, schema) for uri in file_uris
    ]
    if len(tables) == 1:
        rows: list[BronzeRecord] = tables[0].to_pylist()
        return rows
    # Files written before and after an evolution may differ in nullability.
    concatenated = pa.concat_tables(tables, promote_options="default")
    return cast("list[BronzeRecord]", concatenated.to_pylist())


@dataclass(frozen=True)
class _PartitionInfo:
    root: Path
    columns: list[str]
    schema: pa.Schema
    values: dict[str, dict[str, object]]


def _partition_info(
    table: DeltaTable, *, schema: pa.Schema | None = None
) -> _PartitionInfo | None:
    columns = table.metadata().partition_columns
    if not columns:
        return None
    actions = pa.table(table.get_add_actions())
    partition_field = (
        "partition" if "partition" in actions.column_names else "partition_values"
    )
    return _PartitionInfo(
        Path(resolve_parquet_file_uri(table.table_uri)).resolve(),
        columns,
        schema if schema is not None else delta_schema_to_pyarrow(table.schema()),
        {item["path"]: item[partition_field] for item in actions.to_pylist()},
    )


def _align_table_to_schema(
    result: pa.Table, schema: pa.Schema, columns: list[str] | None
) -> pa.Table:
    """Fill schema-evolved columns missing from older Parquet payloads as typed nulls."""
    target = list(schema.names) if columns is None else list(columns)
    schema_names = set(schema.names)
    for name in target:
        if name in result.column_names or name not in schema_names:
            continue
        result = result.append_column(
            name, pa.nulls(result.num_rows, type=schema.field(name).type)
        )
    if not target:
        return result
    projected = result.select(target)
    for index, name in enumerate(target):
        target_type = schema.field(name).type
        column = projected.column(index)
        if column.type != target_type:
            projected = projected.set_column(index, name, column.cast(target_type))
    return projected


def _physical_columns_for_read(
    columns: list[str] | None,
    partition_columns: frozenset[str],
    available: set[str],
) -> list[str]:
    """Select readable non-partition columns present in the active Parquet file."""
    if columns is None:
        return list(available)
    return [
        name for name in columns if name not in partition_columns and name in available
    ]


def _list_available_parquet_columns(path: str) -> set[str] | None:
    """Return Parquet column names, or None when the schema probe is unavailable."""
    try:
        return set(pq.read_schema(path).names)
    except (OSError, ValueError, pa.ArrowInvalid, pa.ArrowIOError):
        # Windows-style URIs can fail schema probes on non-Windows hosts; defer
        # filtering to pq.read_table and typed null alignment.
        return None


def _empty_row_table(row_count: int) -> pa.Table:
    """Build a zero-column Arrow table with a fixed row count for typed null fills."""
    return pa.table(
        {"__bioetl_row_pad__": pa.nulls(row_count, type=pa.null())}
    ).drop_columns(["__bioetl_row_pad__"])


def _parquet_row_count(path: str) -> int:
    """Preserve read failures instead of presenting an unreadable file as empty."""
    return int(pq.read_metadata(path).num_rows)


def _read_physical_parquet(
    path: str,
    columns: list[str] | None,
    partition_columns: frozenset[str],
) -> pa.Table:
    """Read active-file physical columns, tolerating unavailable schema probes."""
    available = _list_available_parquet_columns(path)
    if available is None:
        physical_columns = (
            None
            if columns is None
            else [name for name in columns if name not in partition_columns]
        )
    else:
        physical_columns = _physical_columns_for_read(
            columns, partition_columns, available
        )
    if physical_columns is None or physical_columns:
        return pq.read_table(path, columns=physical_columns, use_threads=False)
    return _empty_row_table(_parquet_row_count(path))


def _append_partition_columns(
    result: pa.Table,
    *,
    path: str,
    partition_info: _PartitionInfo,
    columns: list[str] | None,
    schema: pa.Schema,
) -> pa.Table:
    """Restore partition fields from Delta add-actions with Delta-native types."""
    relative = Path(path).resolve().relative_to(partition_info.root).as_posix()
    values = partition_info.values.get(relative)
    if values is None:
        # delta-rs and the local filesystem can expose different URI escaping.
        aliases = {unquote(relative), quote(relative, safe="/=")}
        matches = [
            partition_info.values[key]
            for key in aliases
            if key in partition_info.values
        ]
        if len(matches) != 1:
            raise KeyError(f"Cannot match Delta add action for {relative!r}")
        (values,) = matches
    for name in partition_info.columns:
        if columns is not None and name not in columns:
            continue
        if name in result.column_names:
            continue
        value = pa.scalar(values[name]).cast(schema.field(name).type)
        result = result.append_column(
            name, pa.array([value.as_py()] * result.num_rows, type=value.type)
        )
    return result


def _read_active_file(
    file_uri: str,
    columns: list[str] | None,
    partition_info: _PartitionInfo | None,
    schema: pa.Schema,
) -> pa.Table:
    """Restore partition columns from Delta actions, including typed nulls.

    Parquet payloads omit partition fields. Inferring them from Hive directory
    names loses Delta's types and depends on PyArrow's version-specific defaults.
    After schema evolution, older active files may also omit newly added columns;
    fill those as typed nulls before selecting the Delta schema projection.
    """
    path = resolve_parquet_file_uri(file_uri)
    partition_columns = frozenset(partition_info.columns if partition_info else [])
    result = _read_physical_parquet(path, columns, partition_columns)

    if partition_info is not None:
        result = _append_partition_columns(
            result,
            path=path,
            partition_info=partition_info,
            columns=columns,
            schema=schema,
        )
    return _align_table_to_schema(result, schema, columns)


def read_delta_records(
    table: DeltaTable,
    columns: list[str] | None = None,
) -> list[BronzeRecord]:
    """Read Delta rows into generic record dictionaries.

    Prefer RecordBatchReader iteration to reduce peak memory compared to
    materializing a full Arrow table before conversion. On Windows, prefer
    active parquet file reads over native ``to_pyarrow_table`` scans.
    """
    to_dataset = getattr(table, "to_pyarrow_dataset", None)
    if _can_use_pyarrow_dataset_scanner() and callable(to_dataset):
        dataset = to_dataset()
        scanner = cast(Any, dataset).scanner(
            columns=columns
        )  # Any: pyarrow dataset duck-type
        to_reader = getattr(scanner, "to_reader", None)
        if callable(to_reader):
            from collections.abc import Iterable

            records: list[BronzeRecord] = []
            batches = cast(
                Iterable[Any],  # Any: optional Arrow reader is dynamically discovered.
                to_reader(),
            )
            for batch in batches:
                records.extend(batch.to_pylist())
            return records
        # Dataset path available but no reader - fall through carefully.
        return _read_records_from_active_parquet_files(table, columns=columns)

    return _read_records_from_active_parquet_files(table, columns=columns)


def load_delta_table(table_path: str) -> DeltaTable:
    """Open a Delta table from its resolved filesystem path."""
    return DeltaTable(normalize_delta_filesystem_path(table_path))


def normalize_delta_filesystem_path(path: str | Path) -> str:
    """Return a canonical absolute POSIX-style path for Delta Lake filesystem I/O."""
    normalized = str(path).replace("\\", "/")
    if "://" in normalized:
        return normalized.rstrip("/")
    return Path(normalized).expanduser().resolve().as_posix()


def resolve_delta_table_path(
    *,
    base_path: str,
    table_name: str,
    flat_structure: bool,
) -> str:
    """Resolve the contract path for a Delta table."""
    normalized_input = base_path.replace("\\", "/")
    if "://" in normalized_input:
        normalized_remote_base = normalized_input.rstrip("/")
        if flat_structure:
            return normalized_remote_base
        relative_path = "/".join(part for part in table_name.split(".") if part)
        return (
            f"{normalized_remote_base}/{relative_path}"
            if relative_path
            else normalized_remote_base
        )

    normalized_base_path = Path(normalized_input).expanduser()
    if flat_structure:
        return normalized_base_path.as_posix()
    relative_parts = [part for part in table_name.split(".") if part]
    return normalized_base_path.joinpath(*relative_parts).as_posix()


def get_delta_table_arrow_schema(table: DeltaTable) -> pa.Schema:
    """Extract the PyArrow schema from an opened Delta table."""
    return delta_schema_to_pyarrow(table.schema())


def clear_delta_tables(
    *,
    base_path: Path,
    table_path: Path | None,
    dry_run: bool,
) -> int:
    """Clear one Delta table or all Delta tables rooted at a base path."""
    if not base_path.exists():
        return 0

    if table_path is not None:
        if not table_path.exists():
            return 0
        if not dry_run:
            shutil.rmtree(table_path)
        return 1

    cleared = 0
    for item in base_path.iterdir():
        if item.is_dir() and (item / "_delta_log").exists():
            if not dry_run:
                shutil.rmtree(item)
            cleared += 1
    return cleared
