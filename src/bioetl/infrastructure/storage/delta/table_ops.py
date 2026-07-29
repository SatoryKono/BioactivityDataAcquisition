# Host attrs/methods provided by concrete composition.
"""Reusable Delta table helper operations."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any, cast
from urllib.parse import unquote, urlparse

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

    tables = [
        pq.read_table(
            resolve_parquet_file_uri(file_uri),
            columns=columns,
            # Threaded parquet reads have hung on some Windows checkouts during
            # first-touch native library bring-up; keep single-thread IO here.
            use_threads=False,
        )
        for file_uri in file_uris
    ]
    if len(tables) == 1:
        rows: list[BronzeRecord] = tables[0].to_pylist()
        return rows
    concatenated = pa.concat_tables(tables)
    return cast("list[BronzeRecord]", concatenated.to_pylist())


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
        scanner = cast(Any, dataset).scanner(columns=columns)  # Any: pyarrow dataset duck-type
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
        # Dataset path available but no reader — fall through carefully.
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
