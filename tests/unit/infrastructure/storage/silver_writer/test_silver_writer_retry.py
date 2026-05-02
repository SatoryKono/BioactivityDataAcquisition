"""SilverWriter retry/error/maintenance unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pyarrow as pa

from bioetl.domain.exceptions import SchemaViolationError

pytestmark = pytest.mark.unit


class TestSilverWriterVacuum:
    """Tests for SilverWriter vacuum operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_vacuum_returns_deleted_files(self, mock_delta_table, noop_logger):
        """Test vacuum returns list of deleted files."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = [
            "file1.parquet",
            "file2.parquet",
        ]

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.vacuum("test.table", retention_hours=168)

        assert len(result) == 2
        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=168, dry_run=False
        )

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_vacuum_dry_run(self, mock_delta_table, noop_logger):
        """Test vacuum dry run."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.vacuum.return_value = ["file1.parquet"]

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        await writer.vacuum("test.table", retention_hours=24, dry_run=True)

        mock_table_instance.vacuum.assert_called_once_with(
            retention_hours=24, dry_run=True
        )

    @pytest.mark.asyncio
    async def test_vacuum_table_not_found(self, noop_logger):
        """Test vacuum raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.support.retention.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.vacuum("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterOptimize:
    """Tests for SilverWriter optimize operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_optimize_returns_metrics(self, mock_delta_table, noop_logger):
        """Test optimize returns compaction metrics."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {
            "numFilesAdded": 1,
            "numFilesRemoved": 5,
        }

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.optimize("test.table")

        assert result["numFilesRemoved"] == 5
        mock_optimize.compact.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_optimize_with_partition_filters(self, mock_delta_table, noop_logger):
        """Test optimize with partition filters."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_optimize = MagicMock()
        mock_table_instance.optimize = mock_optimize
        mock_optimize.compact.return_value = {}

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        await writer.optimize("test.table", partition_filters=[("year", "=", 2025)])

        mock_optimize.compact.assert_called_once_with(
            partition_filters=[("year", "=", 2025)]
        )

    @pytest.mark.asyncio
    async def test_optimize_table_not_found(self, noop_logger):
        """Test optimize raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.support.retention.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.optimize("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterSchemaEvolutionRetry:
    """Tests for schema evolution retry quirks in merge mode."""

    @pytest.mark.asyncio
    async def test_merge_pre_evolves_existing_table_before_first_merge(
        self,
    ) -> None:
        """Existing tables should be schema-evolved before the first merge call."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.delta.resilience import (
            DEFAULT_SILVER_MERGE_POLICY,
        )
        from bioetl.infrastructure.storage.silver.delta_helpers import (
            _DeltaWriteRequest,
        )
        from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
            _execute_merge_write_request,
        )

        table = MagicMock()
        delta_table_factory = MagicMock(side_effect=[table, table])
        write_deltalake = MagicMock()
        load_module = MagicMock(
            return_value=SimpleNamespace(
                DeltaTable=delta_table_factory,
                write_deltalake=write_deltalake,
            )
        )
        merge_records = AsyncMock(return_value=None)
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="s3://bucket/silver/test.table",
            arrow_data=pa.table({"entity_id": ["v1"], "new_field": ["x"]}),
            primary_keys=["entity_id"],
            partition_cols=None,
            schema_mode=None,
            merge_schema=True,
        )

        await _execute_merge_write_request(
            request=request,
            policy=DEFAULT_SILVER_MERGE_POLICY,
            load_module=load_module,
            write_append=AsyncMock(),
            merge_records=merge_records,
            emit_final=MagicMock(),
            emit_retry=MagicMock(),
            logger=MagicMock(),
        )

        assert write_deltalake.call_count == 1
        assert delta_table_factory.call_count == 2
        assert merge_records.await_count == 1
        assert merge_records.await_args.kwargs["merge_schema"] is False

    @pytest.mark.asyncio
    async def test_merge_raises_when_duplicate_field_is_generic_exception_after_pre_evolution(
        self,
    ) -> None:
        """Generic duplicate-field exceptions still surface after eager pre-evolution."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.delta.resilience import (
            DEFAULT_SILVER_MERGE_POLICY,
        )
        from bioetl.infrastructure.storage.silver.delta_helpers import (
            _DeltaWriteRequest,
        )
        from bioetl.infrastructure.storage.silver.merge_resilience_helpers import (
            _execute_merge_write_request,
        )

        table = MagicMock()
        delta_table_factory = MagicMock(side_effect=[table, table])
        write_deltalake = MagicMock()
        load_module = MagicMock(
            return_value=SimpleNamespace(
                DeltaTable=delta_table_factory,
                write_deltalake=write_deltalake,
            )
        )
        merge_records = AsyncMock(
            side_effect=[
                Exception(
                    "External error: Schema error: Duplicate field name: new_field"
                ),
                None,
            ]
        )
        request = _DeltaWriteRequest(
            validated_mode=SilverWriteMode.MERGE,
            table_path="s3://bucket/silver/test.table",
            arrow_data=pa.table({"entity_id": ["v1"], "new_field": ["x"]}),
            primary_keys=["entity_id"],
            partition_cols=None,
            schema_mode=None,
            merge_schema=True,
        )

        with pytest.raises(
            Exception,
            match="Duplicate field name: new_field",
        ):
            await _execute_merge_write_request(
                request=request,
                policy=DEFAULT_SILVER_MERGE_POLICY,
                load_module=load_module,
                write_append=AsyncMock(),
                merge_records=merge_records,
                emit_final=MagicMock(),
                emit_retry=MagicMock(),
                logger=MagicMock(),
            )

        assert write_deltalake.call_count == 1
        assert merge_records.await_count == 1
        assert merge_records.await_args.kwargs["merge_schema"] is False


@pytest.mark.unit
class TestSilverWriterGetTableInfo:
    """Tests for SilverWriter get_table_info operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_get_table_info_returns_metadata(self, mock_delta_table, noop_logger):
        """Test get_table_info returns table metadata."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance
        mock_table_instance.version.return_value = 10
        mock_table_instance.file_uris.return_value = ["file1.parquet", "file2.parquet"]
        mock_schema = MagicMock()
        mock_schema.to_arrow.return_value = {"fields": []}
        mock_table_instance.schema.return_value = mock_schema
        mock_table_instance.metadata.return_value = {"id": "test-table"}

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.get_table_info("test.table")

        assert result["version"] == 10
        assert result["num_files"] == 2

    @pytest.mark.asyncio
    async def test_get_table_info_table_not_found(self, noop_logger):
        """Test get_table_info raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.support.retention.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.get_table_info("nonexistent.table")


@pytest.mark.unit
class TestSilverWriterTimeTravel:
    """Tests for SilverWriter time_travel operation."""

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_time_travel_by_version(self, mock_delta_table, noop_logger):
        """Test time_travel by version number."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        result = await writer.time_travel("test.table", version=5)

        assert result == mock_table_instance
        mock_delta_table.assert_called_once()

    @pytest.mark.asyncio
    @patch("bioetl.infrastructure.storage.support.retention.DeltaTable")
    async def test_time_travel_by_timestamp(self, mock_delta_table, noop_logger):
        """Test time_travel by timestamp."""
        from datetime import datetime

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_table_instance = MagicMock()
        mock_delta_table.return_value = mock_table_instance

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)
        ts = datetime(2025, 1, 1, 12, 0, 0)
        result = await writer.time_travel("test.table", timestamp=ts)

        assert result == mock_table_instance

    @pytest.mark.asyncio
    async def test_time_travel_both_version_and_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when both version and timestamp given."""
        from datetime import datetime

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        with pytest.raises(ValueError, match="Specify either version or timestamp"):
            await writer.time_travel(
                "test.table", version=5, timestamp=datetime(2025, 1, 1)
            )

    @pytest.mark.asyncio
    async def test_time_travel_neither_version_nor_timestamp_raises(self, noop_logger):
        """Test time_travel raises ValueError when neither version nor timestamp given."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        with pytest.raises(
            ValueError, match="Must specify either version or timestamp"
        ):
            await writer.time_travel("test.table")

    @pytest.mark.asyncio
    async def test_time_travel_table_not_found(self, noop_logger):
        """Test time_travel raises TableNotFoundError for missing table."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import TableNotFoundError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.support.retention.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(TableNotFoundError):
                await writer.time_travel("nonexistent.table", version=1)


@pytest.mark.unit
class TestSilverWriterErrorHandling:
    """Tests for error handling in SilverWriter."""

    @pytest.mark.asyncio
    async def test_write_silver_schema_mismatch_error(self, valid_records, noop_logger):
        """Test write_silver raises SchemaViolationError for schema mismatch."""
        from unittest.mock import patch

        import pyarrow as pa
        from deltalake.exceptions import SchemaMismatchError
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # First call (schema check) returns TableNotFoundError (new table)
        # Second call (write) raises SchemaMismatchError
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),  # Schema check
                SchemaMismatchError("Schema mismatch"),  # Write attempt
            ]
        )

        # Patch both modules: base_delta_writer for _get_table_schema, silver_writer for _write_merge
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(SchemaViolationError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

    @pytest.mark.asyncio
    async def test_write_silver_merge_conflict_error(self, valid_records, noop_logger):
        """Test write_silver raises MergeConflictError for merge conflicts."""
        from unittest.mock import MagicMock, patch

        import pyarrow as pa
        from deltalake.exceptions import DeltaError
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import MergeConflictError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_table = MagicMock()
        mock_merge = MagicMock()
        mock_table.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        mock_merge.execute.side_effect = DeltaError("Merge-conflict detected")

        # First call (schema check) returns TableNotFoundError (new table)
        # Second call (write merge) returns mock_table
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),  # Schema check
                mock_table,  # Write attempt
            ]
        )
        # Patch both modules: base_delta_writer for _get_table_schema, silver_writer for _write_merge
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(MergeConflictError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

    @pytest.mark.asyncio
    async def test_write_silver_merge_timeout_raises_delta_transaction_error(
        self, valid_records, noop_logger
    ):
        """Test merge timeout is surfaced as DeltaTransactionError."""
        import asyncio
        from unittest.mock import MagicMock, patch

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import DeltaTransactionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_table = MagicMock()
        mock_merge = MagicMock()
        mock_table.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge

        # First call (schema check) -> table absent
        # Second call (merge path) -> existing table object
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),
                mock_table,
                mock_table,
            ]
        )
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.delta_helpers.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.merge_resilience_helpers.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

            with pytest.raises(DeltaTransactionError, match="timed out"):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

    @pytest.mark.asyncio
    async def test_write_silver_merge_timeout_logs_final_reason(
        self, valid_records
    ) -> None:
        """Final merge timeout should emit final_reason telemetry."""
        import asyncio

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.exceptions import DeltaTransactionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter
        from bioetl.infrastructure.storage.delta.resilience import (
            AdaptiveRetryPolicy,
            SilverMergeResiliencePolicy,
        )

        logger = MagicMock()
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_table = MagicMock()
        mock_merge = MagicMock()
        mock_table.merge.return_value = mock_merge
        mock_merge.when_matched_update_all.return_value = mock_merge
        mock_merge.when_not_matched_insert_all.return_value = mock_merge
        delta_table_mock = MagicMock(
            side_effect=[
                DeltaTableNotFoundError("Not found"),
                mock_table,
            ]
        )
        policy = SilverMergeResiliencePolicy(
            execution_timeout_seconds=1.0,
            commit_retry=AdaptiveRetryPolicy(
                enabled=True,
                max_retries=0,
                base_delay_seconds=0.0,
                max_delay_seconds=0.0,
                jitter_seconds=0.0,
                adaptive=False,
            ),
            timeout_retry=AdaptiveRetryPolicy(
                enabled=True,
                max_retries=0,
                base_delay_seconds=0.0,
                max_delay_seconds=0.0,
                jitter_seconds=0.0,
                adaptive=False,
            ),
        )
        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                delta_table_mock,
            ),
            patch(
                "bioetl.infrastructure.storage.silver.delta_helpers.asyncio.wait_for",
                side_effect=asyncio.TimeoutError,
            ),
        ):
            writer = SilverWriter(
                base_path="s3://bucket/silver",
                logger=logger,
                merge_resilience_policy=policy,
            )

            with pytest.raises(DeltaTransactionError):
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=schema,
                )

        logger.error.assert_any_call(
            "silver_merge_failed",
            table_path="s3://bucket/silver/test/table",
            final_reason="timeout_retries_exhausted",
        )


@pytest.mark.unit
class TestSilverWriterClear:
    """Tests for SilverWriter clear operation."""

    def test_clear_nonexistent_base_path_returns_zero(self, noop_logger, tmp_path):
        """Test clear returns 0 when base_path doesn't exist."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        nonexistent = tmp_path / "nonexistent"
        writer = SilverWriter(base_path=str(nonexistent), logger=noop_logger)

        result = writer.clear()
        assert result == 0

    def test_get_table_path(self, noop_logger, tmp_path):
        """Test get_table_path returns correct path."""
        from pathlib import Path

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path=str(tmp_path), logger=noop_logger)
        result = writer.get_table_path("chembl.activity")

        assert result == Path(tmp_path) / "chembl" / "activity"
