"""Unit tests for SilverWriterMergedMixin helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pandera.pandas as pa
import pytest

from bioetl.domain.schemas.column_order import canonical_column_order
from bioetl.domain.exceptions import SchemaViolationError
from bioetl.infrastructure.storage.delta.arrow_converter import ArrowDataConverter
from bioetl.infrastructure.storage.silver.merged_mixin import (
    _MergedSilverWriteRequest,
    SilverWriterMergedMixin,
)

TEST_SILVER_ROOT = "test-output/silver"


class _MergedHost(SilverWriterMergedMixin):
    """Minimal host exposing the merged Silver helper surface for unit tests."""

    def __init__(self) -> None:
        self._arrow_converter = ArrowDataConverter()
        self.logger = MagicMock()
        self.csv_exporter = None
        self._write_silver_merged_metadata = AsyncMock()

    def _resolve_table_path(self, table_name: str) -> str:
        return f"{TEST_SILVER_ROOT}/{table_name.replace('.', '/')}"


@pytest.mark.unit
class TestSilverWriterMergedMixin:
    """Regression coverage for merged Silver Arrow preparation."""

    def test_prepare_merged_silver_write_applies_canonical_order_by_default(
        self,
    ) -> None:
        """Merged write prep should use canonical order unless preservation is requested."""
        host = _MergedHost()
        records = [
            {
                "name": "Alice",
                "_run_id": "run-1",
                "_run_type": "backfill",
                "id": 1,
            }
        ]

        prepared = host._prepare_merged_silver_write(
            request=_MergedSilverWriteRequest(
                table_name="test.table",
                records=records,
                primary_keys=["id"],
            )
        )

        assert prepared.table_path == f"{TEST_SILVER_ROOT}/test/table"
        assert prepared.arrow_table.column_names == canonical_column_order(
            ["name", "id"]
        )
        assert "_run_id" not in prepared.arrow_table.column_names
        assert "_run_type" not in prepared.arrow_table.column_names

    def test_prepare_merged_silver_write_preserves_input_order_when_requested(
        self,
    ) -> None:
        """Merged write prep should preserve input order when explicitly requested."""
        host = _MergedHost()
        records = [{"name": "Alice", "_run_id": "run-1", "id": 1}]

        prepared = host._prepare_merged_silver_write(
            request=_MergedSilverWriteRequest(
                table_name="test.table",
                records=records,
                primary_keys=["id"],
                preserve_column_order=True,
            )
        )

        assert prepared.arrow_table.column_names == ["name", "id"]

    def test_prepare_merged_silver_write_sorts_by_primary_keys(self) -> None:
        """Merged write prep should preserve deterministic primary-key sorting."""
        host = _MergedHost()
        records = [
            {"id": 3, "name": "c"},
            {"id": 1, "name": "a"},
            {"id": 2, "name": "b"},
        ]

        prepared = host._prepare_merged_silver_write(
            request=_MergedSilverWriteRequest(
                table_name="test.table",
                records=records,
                primary_keys=["id"],
            )
        )

        assert prepared.arrow_table.column("id").to_pylist() == [1, 2, 3]

    def test_prepare_merged_silver_write_is_stable_for_reordered_inputs(self) -> None:
        """Merged write prep should produce identical Arrow rows for input reorderings."""
        host = _MergedHost()
        records = [
            {"source": "chembl", "id": 2, "name": "b"},
            {"source": "chembl", "id": 1, "name": "a"},
            {"source": "pubchem", "id": 1, "name": "c"},
        ]

        first = host._prepare_merged_silver_write(
            request=_MergedSilverWriteRequest(
                table_name="test.table",
                records=records,
                primary_keys=["source", "id"],
            )
        )
        second = host._prepare_merged_silver_write(
            request=_MergedSilverWriteRequest(
                table_name="test.table",
                records=list(reversed(records)),
                primary_keys=["source", "id"],
            )
        )

        assert first.arrow_table.to_pylist() == second.arrow_table.to_pylist()

    def test_prepare_merged_silver_write_validates_against_schema_when_provided(
        self,
    ) -> None:
        """Merged Silver prep should reject rows that violate registered core schema."""
        host = _MergedHost()
        schema = pa.DataFrameSchema(
            {
                "id": pa.Column(int),
                "name": pa.Column(str),
            }
        )

        with pytest.raises(SchemaViolationError, match=r"test\.table"):
            host._prepare_merged_silver_write(
                request=_MergedSilverWriteRequest(
                    table_name="test.table",
                    records=[{"id": "not-int", "name": "Alice"}],
                    primary_keys=["id"],
                    schema=schema,
                )
            )
