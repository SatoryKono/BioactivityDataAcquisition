"""L12 residuals for gold/* modules only. Do not import silver_writer."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.infrastructure.storage.gold import io_delta_runtime as gold_runtime
from bioetl.infrastructure.storage.gold.io_metrics import _split_gold_merged_table_label
from bioetl.infrastructure.storage.gold.io_preparation import _prepare_gold_merged_table
from bioetl.infrastructure.storage.gold.writer_metrics import _split_gold_table_label

pytestmark = pytest.mark.unit


def _patch_gold_writer_module(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.gold.io_preparation._load_gold_writer_module",
        lambda: SimpleNamespace(coerce_null_types_for_delta=lambda table: table),
    )


def test_prepare_gold_merged_table_drops_ingestion_ts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_gold_writer_module(monkeypatch)
    monkeypatch.setattr(
        "bioetl.infrastructure.storage.delta.schema_ops.drop_nondeterministic_persisted_fields",
        lambda table: table,
    )
    table = _prepare_gold_merged_table(
        records=[
            {"id": "b", "value": 2, "_ingestion_ts": "ts"},
            {"id": "a", "value": 1, "_ingestion_ts": "ts"},
        ],
        primary_keys=["id"],
        preserve_column_order=True,
    )
    assert "_ingestion_ts" not in table.column_names
    assert "id" in table.column_names


@pytest.mark.asyncio
async def test_run_gold_write_with_retry_empty_exception_types(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        gold_runtime,
        "_extend_retry_errors_with_arrow",
        lambda _errors: (),
    )
    calls = {"n": 0}

    async def _operation() -> None:
        calls["n"] += 1

    await gold_runtime._run_gold_write_with_retry(
        SimpleNamespace(GOLD_WRITE_RETRY_ERRORS=()),  # type: ignore[arg-type]
        _operation,
    )
    assert calls["n"] == 1


def test_gold_table_label_helpers_unknown_empty() -> None:
    assert _split_gold_merged_table_label("") == ("unknown", "unknown")
    assert _split_gold_table_label("") == ("unknown", "unknown")
    assert _split_gold_merged_table_label("pipeline/table")[0] != "unknown"
    assert _split_gold_table_label("pipeline/table")[0] != "unknown"
