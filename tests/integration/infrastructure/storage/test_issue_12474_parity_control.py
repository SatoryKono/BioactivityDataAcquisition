"""Controlled physical/logical mismatch on a real, synthetic temporary Delta table."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from scripts.engineering.ci.physical_schema_parity import NEGATIVE_CONTROL_ENV

pytestmark = pytest.mark.integration


def test_real_delta_schema_matches_logical_contract(tmp_path: Path) -> None:
    """A dispatch-only type mismatch must fail the same CI step and aggregate."""
    schema = pa.schema([pa.field("value", pa.int64(), nullable=False)])
    table_path = tmp_path / "synthetic_parity_control"
    write_deltalake(str(table_path), pa.Table.from_pylist([{"value": 1}], schema))
    actual = DeltaTable(str(table_path)).schema().to_pyarrow()
    expected = schema
    if os.environ.get(NEGATIVE_CONTROL_ENV) == "1":
        expected = pa.schema([pa.field("value", pa.string(), nullable=False)])
    assert actual.equals(expected), (
        f"schema mismatch: expected={expected}; actual={actual}"
    )


def test_prepared_schema_removal_is_not_hidden_by_raw_record() -> None:
    """Keep raw extras visible without masking a prepared-schema missing field."""
    from bioetl.infrastructure.storage.silver.schema_drift_operations import (
        _build_silver_schema_drift_diff,
    )

    diff = _build_silver_schema_drift_diff(
        pa.schema([("entity_id", pa.string()), ("value", pa.int64())]),
        [{"entity_id": "synthetic-1", "value": 1, "extra": "raw-only"}],
        incoming_schema=pa.schema([("entity_id", pa.string())]),
    )
    assert diff is not None
    assert diff.missing_fields == ("value",)
    assert diff.new_fields == ("extra",)


def test_nullable_value_with_present_key_is_not_a_removed_field() -> None:
    """A present null value is distinct from an omitted field in strict drift."""
    from bioetl.infrastructure.storage.silver.schema_drift_operations import (
        _build_silver_schema_drift_diff,
    )

    schema = pa.schema([("entity_id", pa.string()), ("optional", pa.string())])
    assert (
        _build_silver_schema_drift_diff(
            schema,
            [{"entity_id": "synthetic-1", "optional": None}],
            incoming_schema=schema,
        )
        is None
    )


@pytest.mark.parametrize("mode", ["overwrite", "scd2"])
@pytest.mark.asyncio
async def test_gold_logical_required_null_rejected(tmp_path: Path, mode: str) -> None:
    """Physical nullable=true never relaxes the logical Gold required contract."""
    from pandera.pandas import Column, DataFrameSchema

    from bioetl.domain.exceptions.gold_write import GoldWriteFailure
    from bioetl.domain.types import ScdConfig
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.gold_writer import GoldWriter

    writer = GoldWriter(base_path=tmp_path / "gold", logger=NoOpLogger())
    schema = DataFrameSchema({"entity_id": Column(str, nullable=False)}, strict=True)
    options = {}
    if mode == "scd2":
        options["scd_config"] = ScdConfig(business_key="entity_id")
    with pytest.raises(GoldWriteFailure) as outcome:
        await writer.write_gold(
            table_name="synthetic.required",
            records=[{"entity_id": None}],
            schema=schema,
            mode=mode,
            ingestion_ts=datetime(2026, 10, 30, 12, 0, tzinfo=UTC),
            **options,
        )
    assert outcome.value.__cause__ is not None
    assert hasattr(outcome.value.__cause__, "reject_reason"), repr(
        outcome.value.__cause__
    )
    assert (
        outcome.value.__cause__.reject_reason.reason_code
        == "gold_contract_required_failure"
    )
    assert (
        outcome.value.__cause__.reject_reason.rule_id == "gold.contract.required_fields"
    )
    assert "non-nullable series 'entity_id' contains null" in str(
        outcome.value.__cause__
    )
    assert not (tmp_path / "gold" / "synthetic" / "required" / "_delta_log").exists()
