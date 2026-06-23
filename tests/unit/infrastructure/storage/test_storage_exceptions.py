"""Unit tests for the storage exception hierarchy."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from deltalake.exceptions import DeltaError, SchemaMismatchError, TableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import MergeConflictError, SchemaViolationError
from bioetl.domain.exceptions import TableNotFoundError as CustomTableNotFoundError
from bioetl.infrastructure.storage.silver_writer import SilverWriter


@pytest.fixture
def silver_writer(noop_logger):
    """Fixture for a SilverWriter."""
    return SilverWriter(base_path="/fake/path", logger=noop_logger)


@pytest.fixture
def valid_record():
    """Valid test record with all required metadata fields."""
    return {
        "id": 1,
        "_run_id": "test-run-id",
        "_run_type": "incremental",
        "_source_batch_id": "batch-123",
        "_ingestion_ts": "2024-01-01T00:00:00Z",
    }


class TestSilverWriterExceptions:
    """Tests for exception handling in SilverWriter."""

    @pytest.mark.asyncio
    async def test_write_silver_raises_schema_violation_error_on_merge(
        self, valid_record, noop_logger
    ):
        """Test that SchemaViolationError is raised on merge."""
        import pyarrow as pa

        # First call (schema check) raises TableNotFoundError, second call raises
        # SchemaMismatchError
        mock_delta_table = MagicMock(
            side_effect=[
                TableNotFoundError("Not found"),  # Schema check (base_delta_writer)
                SchemaMismatchError("Invalid schema"),  # Write attempt (silver_writer)
            ]
        )

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # Use same mock for both modules so side_effect list is shared
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                mock_delta_table,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                mock_delta_table,
            ),
        ):
            writer = SilverWriter(base_path="/fake/path", logger=noop_logger)
            with pytest.raises(SchemaViolationError):
                await writer.write_silver(
                    "test.table", [valid_record], ["id"], schema=schema
                )

    @pytest.mark.asyncio
    async def test_write_silver_raises_merge_conflict_error(
        self, valid_record, noop_logger
    ):
        """Test that MergeConflictError is raised."""
        import pyarrow as pa

        mock_table_instance = MagicMock()
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict")

        # First call (schema check) raises TableNotFoundError, second call returns mock
        mock_delta_table = MagicMock(
            side_effect=[
                TableNotFoundError("Not found"),  # Schema check
                mock_table_instance,  # Write attempt
            ]
        )

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # Use same mock for both modules so side_effect list is shared
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                mock_delta_table,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                mock_delta_table,
            ),
        ):
            writer = SilverWriter(base_path="/fake/path", logger=noop_logger)
            with pytest.raises(MergeConflictError):
                await writer.write_silver(
                    "test.table", [valid_record], ["id"], schema=schema
                )

    @pytest.mark.asyncio
    async def test_write_silver_raises_schema_error_on_create(
        self, valid_record, noop_logger
    ):
        """Test SchemaViolationError on table creation."""
        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # Both DeltaTable patches raise TableNotFoundError so it falls back to write_deltalake
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=TableNotFoundError,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=TableNotFoundError,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.write_deltalake",
                side_effect=ArrowTypeError("Arrow type error"),
            ),
        ):
            writer = SilverWriter(base_path="/fake/path", logger=noop_logger)
            with pytest.raises(SchemaViolationError):
                await writer.write_silver(
                    "test.table", [valid_record], ["id"], schema=schema
                )

    @pytest.mark.asyncio
    async def test_vacuum_raises_table_not_found(self, noop_logger):
        """Test that vacuum raises CustomTableNotFoundError."""
        with patch(
            "bioetl.infrastructure.storage.support.retention.DeltaTable",
            side_effect=TableNotFoundError,
        ):
            writer = SilverWriter(base_path="/fake/path", logger=noop_logger)

            with pytest.raises(CustomTableNotFoundError):
                await writer.vacuum("test.table")
