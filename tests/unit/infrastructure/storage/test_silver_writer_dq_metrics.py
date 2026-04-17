"""Unit tests for SilverWriter DQ metrics integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from .test_silver_writer import mock_metadata_coordinator, noop_logger, valid_records

# Re-export shared fixtures for pytest discovery in this module.
_FIXTURE_IMPORTS = (noop_logger, valid_records, mock_metadata_coordinator)


@pytest.mark.unit
class TestSilverWriterDQMetrics:
    """Tests for SilverWriter DQ metrics integration (REQ-DQ-001)."""

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_returns_batch_dq_metrics(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics returns BatchDQMetrics."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            assert isinstance(result, BatchDQMetrics)
            assert result.total_records == 2
            assert result.valid_records == 2
            assert result.error_records == 0

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_includes_column_stats(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics computes column statistics."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            # Should have column stats for non-internal fields
            assert "entity_id" in result.column_stats
            assert "value" in result.column_stats
            # Internal fields should be excluded
            assert "_run_id" not in result.column_stats
            assert "_ingestion_ts" not in result.column_stats

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_detects_schema_drift(self, noop_logger):
        """Test _compute_dq_metrics detects schema drift when table exists."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing table has fewer fields
        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [
            {
                "entity_id": "CHEMBL123",
                "new_field": "value",  # New field
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", records)

            assert result.schema_drift is not None
            assert "new_field" in result.schema_drift.new_fields

    @pytest.mark.asyncio
    async def test_compute_dq_metrics_no_drift_for_new_table(
        self, noop_logger, valid_records
    ):
        """Test _compute_dq_metrics returns no drift for new tables."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._compute_dq_metrics("test.table", valid_records)

            assert result.schema_drift is None

    @pytest.mark.asyncio
    async def test_detect_schema_drift_returns_schema_drift_info(self, noop_logger):
        """Test _detect_schema_drift returns SchemaDriftInfo."""
        import pyarrow as pa

        from bioetl.domain.value_objects.dq_metrics import SchemaDriftInfo
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [{"entity_id": "CHEMBL123", "new_field": "value"}]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert isinstance(result, SchemaDriftInfo)
            assert "new_field" in result.new_fields

    @pytest.mark.asyncio
    async def test_detect_schema_drift_critical_for_missing_business_fields(
        self, noop_logger
    ):
        """Test _detect_schema_drift returns critical status for missing business fields."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing schema has business field that's missing in incoming records
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("important_field", pa.string()),  # Business field
                pa.field("_run_id", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # Incoming records missing 'important_field'
        records = [{"entity_id": "CHEMBL123", "_run_id": "uuid-123"}]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert result is not None
            assert result.status == "critical"
            assert "important_field" in result.missing_fields

    @pytest.mark.asyncio
    async def test_detect_schema_drift_warn_for_many_new_fields(self, noop_logger):
        """Test _detect_schema_drift returns warn status for >3 new fields."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # >3 new fields
        records = [
            {
                "entity_id": "CHEMBL123",
                "new_field_1": "a",
                "new_field_2": "b",
                "new_field_3": "c",
                "new_field_4": "d",  # 4th new field
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
            result = await writer._detect_schema_drift("test.table", records)

            assert result is not None
            assert result.status == "warn"

    @pytest.mark.asyncio
    async def test_write_silver_metadata_with_dq_metrics(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata uses DQ metrics when provided."""
        from bioetl.domain.value_objects.dq_metrics import (
            BatchDQMetrics,
            ColumnStats,
            SchemaDriftInfo,
        )
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(
            table_path,
            metadata,
            *,
            table_name=None,
            flat_structure=False,
            provider=None,
            entity=None,
        ):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        # Create DQ metrics with column stats and schema drift
        dq_metrics = BatchDQMetrics(
            total_records=100,
            valid_records=95,
            error_records=5,
            warning_records=2,
            column_stats={
                "entity_id": ColumnStats(null_rate=0.0, unique_count=95),
                "value": ColumnStats(
                    null_rate=0.05, min_value=1.0, max_value=100.0, mean_value=50.5
                ),
            },
            schema_drift=SchemaDriftInfo(
                status="warn", new_fields=("new_col",), missing_fields=()
            ),
        )

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            table_name="test_table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            dq_metrics=dq_metrics,
        )

        # Verify DQ metrics are in metadata
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        dq_summary = metadata.dq_summary

        assert dq_summary.total_records == 100
        assert dq_summary.valid_records == 95
        assert dq_summary.error_records == 5
        assert dq_summary.warning_records == 2
        assert dq_summary.error_rate == 0.05
        assert dq_summary.validation_passed is False

        # Verify column metrics
        assert "entity_id" in dq_summary.column_metrics
        assert "value" in dq_summary.column_metrics
        assert dq_summary.column_metrics["value"].null_rate == 0.05
        assert dq_summary.column_metrics["value"].min == 1.0
        assert dq_summary.column_metrics["value"].max == 100.0

        # Verify schema drift
        assert dq_summary.schema_drift is not None
        assert dq_summary.schema_drift.status == "warn"
        assert "new_col" in dq_summary.schema_drift.new_fields

    @pytest.mark.asyncio
    async def test_write_silver_metadata_fallback_without_dq_metrics(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata uses fallback when dq_metrics is None."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(
            table_path,
            metadata,
            *,
            table_name=None,
            flat_structure=False,
            provider=None,
            entity=None,
        ):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        await writer._write_silver_metadata(
            table_path="/tmp/silver/test/table",
            table_name="test_table",
            records=valid_records,
            primary_keys=["entity_id"],
            mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            dq_metrics=None,  # No DQ metrics
        )

        # Verify fallback DQ summary
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        dq_summary = metadata.dq_summary

        assert dq_summary.total_records == 2  # len(valid_records)
        assert dq_summary.valid_records == 2
        assert dq_summary.error_records == 0
        assert dq_summary.column_metrics == {}  # Empty column metrics
        assert dq_summary.schema_drift is None

    @pytest.mark.asyncio
    async def test_write_silver_computes_and_passes_dq_metrics(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test write_silver computes DQ metrics and passes to metadata."""
        import pyarrow as pa
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

        mock_metadata_writer = MagicMock()
        write_calls = []

        async def capture_write(
            table_path,
            metadata,
            *,
            table_name=None,
            flat_structure=False,
            provider=None,
            entity=None,
        ):
            write_calls.append({"table_path": table_path, "metadata": metadata})

        mock_metadata_writer.write_silver_metadata = capture_write

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                metadata_writer=mock_metadata_writer,
                metadata_coordinator=mock_metadata_coordinator,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            # Verify DQ metrics were computed and passed
            assert len(write_calls) == 1
            metadata = write_calls[0]["metadata"]
            dq_summary = metadata.dq_summary

            # Should have computed column metrics
            assert "entity_id" in dq_summary.column_metrics
            assert "value" in dq_summary.column_metrics

            # value column should have numeric stats
            value_metrics = dq_summary.column_metrics["value"]
            assert value_metrics.min is not None
            assert value_metrics.max is not None
            assert value_metrics.mean is not None

    @pytest.mark.asyncio
    async def test_finalize_silver_write_result_reuses_delta_version(
        self, noop_logger, valid_records
    ):
        """Finalize path should read Delta version once and pass it to metadata."""
        from datetime import UTC, datetime

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        writer._compute_dq_metrics = AsyncMock(
            return_value=BatchDQMetrics(
                total_records=2,
                valid_records=2,
                error_records=0,
                warning_records=0,
            )
        )
        writer._get_delta_version = AsyncMock(return_value=7)
        writer._write_silver_metadata = AsyncMock()

        result = await writer._finalize_silver_write_result(
            table_name="test.table",
            records=valid_records,
            table_path="/tmp/silver/test/table",
            primary_keys=["entity_id"],
            validated_mode=SilverWriteMode.MERGE,
            bronze_refs=None,
            partition_cols=None,
            source_batch_id=None,
            started_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
            start_perf=0.0,
        )

        assert result is not None
        assert result.delta_version == 7
        assert writer._get_delta_version.await_count == 1
        writer._write_silver_metadata.assert_awaited_once()
        assert writer._write_silver_metadata.await_args.kwargs["version_after"] == 7

    @pytest.mark.asyncio
    async def test_prepare_silver_write_finalization_context_returns_named_context(
        self, noop_logger, valid_records
    ):
        """Finalization helper should resolve DQ/version/timing as one context."""
        from datetime import UTC, datetime, timedelta
        from bioetl.domain.medallion import SilverWriteMode

        from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        dq_metrics = BatchDQMetrics(
            total_records=2,
            valid_records=2,
            error_records=0,
            warning_records=0,
        )
        writer._compute_dq_metrics = AsyncMock(return_value=dq_metrics)
        writer._get_delta_version = AsyncMock(return_value=11)
        started_at = datetime(2026, 3, 11, 12, 0, tzinfo=UTC)

        with patch(
            "bioetl.infrastructure.storage.silver.metadata_mixin.time.perf_counter",
            return_value=5.5,
        ):
            context = await writer._prepare_silver_write_finalization_context(
                table_name="test.table",
                records=valid_records,
                table_path="/tmp/silver/test/table",
                started_at=started_at,
                start_perf=4.0,
            )

        assert context.dq_metrics is dq_metrics
        assert context.version_after == 11
        assert context.completed_at == started_at + timedelta(seconds=1.5)

    def test_build_silver_write_result_uses_version_after(self):
        """Final result helper should return None or a SilverWriteResult by version."""
        from bioetl.infrastructure.storage.silver.metadata_mixin import (
            _build_silver_write_result,
        )

        assert (
            _build_silver_write_result(
                table_name="test.table",
                table_path="/tmp/silver/test/table",
                version_after=None,
                records_count=2,
            )
            is None
        )
        result = _build_silver_write_result(
            table_name="test.table",
            table_path="/tmp/silver/test/table",
            version_after=7,
            records_count=2,
        )
        assert result is not None
        assert result.delta_version == 7
