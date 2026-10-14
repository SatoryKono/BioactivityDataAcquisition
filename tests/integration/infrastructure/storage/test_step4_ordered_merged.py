"""Ordered merged Silver validation on synthetic temporary Delta tables."""

from __future__ import annotations

import pandera.pandas as pa
import pytest
from deltalake import DeltaTable
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.silver_writer import SilverWriter

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_merged_silver_wrong_order_does_not_change_existing_delta(tmp_path):
    writer = SilverWriter(tmp_path, NoOpLogger())
    schema = pa.DataFrameSchema(
        {c: pa.Column(int) for c in ("a", "b", "c")}, ordered=True, strict=True
    )
    original = [{"a": 1, "b": 2, "c": 3}]
    await writer.write_silver_merged(
        "synthetic", original, schema=schema, preserve_column_order=True
    )
    table = DeltaTable(str(tmp_path / "synthetic"))
    version = table.version()
    before = table.to_pyarrow_table().to_pylist()
    with pytest.raises(SchemaViolationError):
        await writer.write_silver_merged(
            "synthetic",
            [{"c": 3, "a": 1, "b": 2, "extra": 9}],
            schema=schema,
            preserve_column_order=True,
        )
    after = DeltaTable(str(tmp_path / "synthetic"))
    assert after.version() == version
    assert after.to_pyarrow_table().to_pylist() == before == original
