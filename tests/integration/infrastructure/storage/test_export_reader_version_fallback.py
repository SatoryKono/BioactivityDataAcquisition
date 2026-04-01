"""Integration tests for version-aware fallback reads via export bootstrap wiring."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

import pyarrow as pa
import pytest
from deltalake import write_deltalake

from bioetl.composition.bootstrap.cli.storage import bootstrap_export_service
from bioetl.infrastructure.storage.delta_reader import DeltaReader
from bioetl.infrastructure.storage.versioned_table_resolver import (
    resolve_versioned_table_name,
)


def _make_storage_settings(tmp_path: Path) -> SimpleNamespace:
    return SimpleNamespace(data_dir=str(tmp_path))


def _write_versioned_delta_table(
    base_path: Path,
    *,
    logical_table: str,
    contract_version: str,
    rows: list[dict[str, object]],
) -> None:
    provider, _ = logical_table.split(".", 1)
    table_name = resolve_versioned_table_name(logical_table, contract_version)
    physical_path = base_path / provider / table_name.split(".", 1)[1]
    physical_path.parent.mkdir(parents=True, exist_ok=True)
    write_deltalake(str(physical_path), pa.Table.from_pylist(rows))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bootstrap_export_service_reader_falls_back_to_next_version(
    tmp_path: Path,
) -> None:
    logical_table = "chembl.activity"
    silver_base_path = tmp_path / "output" / "silver"
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="1.0.0",
        rows=[{"id": "legacy", "value": "v1"}],
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
) -> None:
    logical_table = "chembl.activity"
    silver_base_path = tmp_path / "output" / "silver"
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="1.0.0",
        rows=[{"id": "legacy", "value": "v1"}],
    )
    _write_versioned_delta_table(
        silver_base_path,
        logical_table=logical_table,
        contract_version="2.0.0",
        rows=[{"id": "shadow", "value": "v2"}],
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
