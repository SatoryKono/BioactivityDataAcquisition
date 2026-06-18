"""Reusable Delta table helper operations."""

from __future__ import annotations

import shutil
from pathlib import Path

import pyarrow as pa
from deltalake import DeltaTable

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.storage.delta.schema_ops import delta_schema_to_pyarrow


def read_delta_records(
    table: DeltaTable,
    columns: list[str] | None = None,
) -> list[BronzeRecord]:
    """Read Delta rows into generic record dictionaries.

    Prefer RecordBatchReader iteration to reduce peak memory compared to
    materializing a full Arrow table before conversion.
    """
    to_dataset = getattr(table, "to_pyarrow_dataset", None)
    if callable(to_dataset):
        dataset = to_dataset()
        scanner = dataset.scanner(columns=columns)
        to_reader = getattr(scanner, "to_reader", None)
        if callable(to_reader):
            records: list[BronzeRecord] = []
            for batch in to_reader():
                records.extend(batch.to_pylist())
            return records

    arrow_table = table.to_pyarrow_table(columns=columns)
    rows: list[BronzeRecord] = arrow_table.to_pylist()
    return rows


def load_delta_table(table_path: str) -> DeltaTable:
    """Open a Delta table from its resolved filesystem path."""
    return DeltaTable(table_path)


def resolve_delta_table_path(
    *,
    base_path: str,
    table_name: str,
    flat_structure: bool,
) -> str:
    """Resolve the filesystem path for a Delta table."""
    if flat_structure:
        return base_path
    return f"{base_path}/{table_name.replace('.', '/')}"


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
