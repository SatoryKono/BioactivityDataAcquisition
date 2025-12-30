"""Unit tests for the storage exception hierarchy."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from deltalake.exceptions import DeltaError, SchemaMismatchError, TableNotFoundError
from pyarrow import ArrowTypeError

from bioetl.domain.exceptions import (
    MergeConflictError,
    SchemaViolationError,
)
from bioetl.domain.exceptions import TableNotFoundError as CustomTableNotFoundError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.delta_writer import DeltaWriter


def make_sync_executor(loop: asyncio.AbstractEventLoop):
    """Create a run_in_executor replacement that returns awaitable sync results."""

    async def sync_executor(_, fn, *args):
        return fn(*args)

    return sync_executor


@pytest.fixture
def noop_logger():
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


@pytest.fixture
def delta_writer(noop_logger):
    """Fixture for a DeltaWriter."""
    return DeltaWriter(base_path="/fake/path", logger=noop_logger)


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


class TestDeltaWriterExceptions:
    """Tests for exception handling in DeltaWriter."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_write_silver_raises_schema_violation_error_on_merge(
        self, mock_delta_table, valid_record, noop_logger
    ):
        """Test that SchemaViolationError is raised on merge."""
        # First call (schema check) raises TableNotFoundError, second call raises
        # SchemaMismatchError
        mock_delta_table.side_effect = [
            TableNotFoundError("Not found"),  # Schema check
            SchemaMismatchError("Invalid schema"),  # Write attempt
        ]
        writer = DeltaWriter(
            base_path="/fake/path", logger=noop_logger
        )
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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
        with pytest.raises(SchemaViolationError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.DeltaTable")
    async def test_write_silver_raises_merge_conflict_error(
        self, mock_delta_table, valid_record, noop_logger
    ):
        """Test that MergeConflictError is raised."""
        mock_table_instance = MagicMock()
        mock_merge = MagicMock()
        mock_table_instance.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict")

        # First call (schema check) raises TableNotFoundError, second call returns mock
        mock_delta_table.side_effect = [
            TableNotFoundError("Not found"),  # Schema check
            mock_table_instance,  # Write attempt
        ]

        writer = DeltaWriter(
            base_path="/fake/path", logger=noop_logger
        )
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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
        with pytest.raises(MergeConflictError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.delta_writer.write_deltalake")
    @patch(
        "bioetl.infrastructure.storage.delta_writer.DeltaTable",
        side_effect=TableNotFoundError,
    )
    async def test_write_silver_raises_schema_error_on_create(
        self, _mock_delta_table, mock_write_deltalake, valid_record, noop_logger
    ):
        """Test SchemaViolationError on table creation."""
        mock_write_deltalake.side_effect = ArrowTypeError("Arrow type error")
        writer = DeltaWriter(
            base_path="/fake/path", logger=noop_logger
        )
        # Make run_in_executor execute synchronously for testing
        writer.loop = asyncio.get_event_loop()
        writer.loop.run_in_executor = make_sync_executor(writer.loop)

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
        with pytest.raises(SchemaViolationError):
            await writer.write_silver(
                "test.table", [valid_record], ["id"], schema=schema
            )

    @pytest.mark.asyncio
    async def test_vacuum_raises_table_not_found(self, noop_logger):
        """Test that vacuum raises CustomTableNotFoundError."""
        with patch(
            "bioetl.infrastructure.storage.delta_writer.DeltaTable",
            side_effect=TableNotFoundError,
        ):
            writer = DeltaWriter(
                base_path="/fake/path", logger=noop_logger
            )
            # Make run_in_executor execute synchronously for testing
            writer.loop = asyncio.get_event_loop()
            writer.loop.run_in_executor = make_sync_executor(writer.loop)

            with pytest.raises(CustomTableNotFoundError):
                await writer.vacuum("test.table")
