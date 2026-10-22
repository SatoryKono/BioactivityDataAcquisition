"""Delta log fallback keeps null partitions and evolved nullable columns."""

from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from tests.helpers.delta_partition_read import read_partitioned_delta_file

pytestmark = pytest.mark.unit


def _schema_json() -> str:
    return json.dumps(
        {
            "type": "struct",
            "fields": [
                {
                    "name": "entity_id",
                    "type": "string",
                    "nullable": False,
                    "metadata": {},
                },
                {
                    "name": "year",
                    "type": "integer",
                    "nullable": True,
                    "metadata": {},
                },
                {
                    "name": "note",
                    "type": "string",
                    "nullable": True,
                    "metadata": {},
                },
            ],
        }
    )


def _write_physical(path: Path) -> None:
    pq.write_table(pa.table({"entity_id": ["one"]}), path)


def test_empty_partition_value_is_null_before_type_cast(tmp_path: Path) -> None:
    parquet_path = tmp_path / "part.parquet"
    _write_physical(parquet_path)

    table = read_partitioned_delta_file(
        parquet_path,
        {"year": ""},
        _schema_json(),
        ["entity_id", "year"],
    )

    assert table.column("year").to_pylist() == [None]


def test_missing_nullable_column_is_filled_before_select(tmp_path: Path) -> None:
    parquet_path = tmp_path / "part.parquet"
    _write_physical(parquet_path)

    table = read_partitioned_delta_file(
        parquet_path,
        {"year": "2026"},
        _schema_json(),
        None,
    )

    assert table.column("year").to_pylist() == [2026]
    assert table.column("note").to_pylist() == [None]
    assert table.column_names == ["entity_id", "year", "note"]
