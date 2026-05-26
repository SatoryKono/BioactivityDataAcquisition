"""Integration tests for version-aware fallback reads via export bootstrap wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pyarrow as pa
import pytest

from bioetl.composition.bootstrap.cli.storage import bootstrap_export_service
import bioetl.infrastructure.storage.delta_reader as delta_reader_module
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_versioned_table_name,
)


def _make_storage_settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(data_dir=str(tmp_path))


class _FakeDeltaScanner:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def head(self, limit: int) -> pa.Table:
        return self._table.slice(0, max(0, limit))


class _FakeDeltaDataset:
    def __init__(self, table: pa.Table) -> None:
        self._table = table

    def scanner(self, columns: list[str] | None = None) -> _FakeDeltaScanner:
        table = self._table.select(columns) if columns is not None else self._table
        return _FakeDeltaScanner(table)


@pytest.fixture
def fake_delta_tables(monkeypatch: pytest.MonkeyPatch) -> dict[str, pa.Table]:
    """Patch delta-rs reads with deterministic tables for fallback wiring tests."""
    registry: dict[str, pa.Table] = {}

    class _FakeDeltaTable:
        def __init__(self, table_uri: str) -> None:
            self._table_uri = str(Path(table_uri))
            try:
                self._table = registry[self._table_uri]
            except KeyError as exc:
                raise delta_reader_module.DeltaTableNotFoundError(table_uri) from exc

        def count(self) -> int:
            return self._table.num_rows

        def to_pyarrow_dataset(self) -> _FakeDeltaDataset:
            return _FakeDeltaDataset(self._table)

    monkeypatch.setattr(delta_reader_module, "DeltaTable", _FakeDeltaTable)
    return registry


def _write_versioned_delta_table(
    base_path: Path,
    *,
    logical_table: str,
    contract_version: str,
    rows: list[dict[str, object]],
    registry: dict[str, pa.Table],
) -> None:
    provider, _ = logical_table.split(".", 1)
    table_name = resolve_versioned_table_name(logical_table, contract_version)
    physical_path = base_path / provider / table_name.split(".", 1)[1]
    registry[str(physical_path)] = pa.Table.from_pylist(rows)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_export_service_reader_falls_back_to_next_version(
    tmp_path: Path,
    fake_delta_tables: dict[str, pa.Table],
) -> None:
    logical_table = "chembl.activity"
    silver_base_path = tmp_path / "output" / "silver"
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="1.0.0",
        rows=[{"id": "legacy", "value": "v1"}],
        registry=fake_delta_tables,
    )

    with patch(
        "bioetl.composition.bootstrap.cli.storage.get_settings",
        return_value=_make_storage_settings(tmp_path),
    ):
        service = bootstrap_export_service()
    reader = cast(DeltaReader, service.reader)

    result = await reader.read_with_fallback(
        logical_table,
        ["2.0.0", "1.0.0"],
    )

    assert result.to_pylist() == [{"id": "legacy", "value": "v1"}]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_export_service_reader_prefers_new_active_version(
    tmp_path: Path,
    fake_delta_tables: dict[str, pa.Table],
) -> None:
    logical_table = "chembl.activity"
    silver_base_path = tmp_path / "output" / "silver"
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="1.0.0",
        rows=[{"id": "legacy", "value": "v1"}],
        registry=fake_delta_tables,
    )
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="2.0.0",
        rows=[{"id": "shadow", "value": "v2"}],
        registry=fake_delta_tables,
    )

    with patch(
        "bioetl.composition.bootstrap.cli.storage.get_settings",
        return_value=_make_storage_settings(tmp_path),
    ):
        service = bootstrap_export_service()
    reader = cast(DeltaReader, service.reader)

    result = await reader.read_with_fallback(
        logical_table,
        ["2.0.0", "1.0.0"],
    )

    assert result.to_pylist() == [{"id": "shadow", "value": "v2"}]
