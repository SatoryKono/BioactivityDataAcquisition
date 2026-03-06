"""SilverWriter lineage/audit/export unit tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


class TestSilverWriterAudit:
    """Tests for SilverWriter audit logging."""

    @pytest.mark.asyncio
    async def test_log_silver_audit_skips_when_no_audit(self, noop_logger):
        """Test _log_silver_audit does nothing when audit is None."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)

        # Should not raise, just return early
        await writer._log_silver_audit(
            table_name="test.table",
            records=[{"_run_id": "uuid", "_ingestion_ts": "2025-01-01T00:00:00Z"}],
            mode=SilverWriteMode.MERGE,
        )

    @pytest.mark.asyncio
    async def test_log_silver_audit_skips_invalid_run_id(self, noop_logger):
        """Test _log_silver_audit skips when run_id is invalid UUID."""
        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        # Invalid UUID should skip audit logging
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {"_run_id": "not-a-uuid", "_ingestion_ts": "2025-01-01T00:00:00Z"}
            ],
            mode=SilverWriteMode.MERGE,
        )

        # Audit should NOT be called due to invalid run_id
        mock_audit.log_write.assert_not_called()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_valid_data(self, noop_logger):
        """Test _log_silver_audit logs correctly with valid data."""
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": "2025-01-01T12:00:00",
                    "_run_type": "incremental",
                    "_source_batch_id": "batch-123",
                }
            ],
            mode=SilverWriteMode.MERGE,
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_with_datetime_ingestion_ts(self, noop_logger):
        """Test _log_silver_audit handles datetime ingestion_ts."""
        from datetime import UTC, datetime
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        ingestion_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)

        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": ingestion_dt,  # datetime object
                    "_run_type": "backfill",
                    "_source_batch_id": "batch-456",
                }
            ],
            mode=SilverWriteMode.APPEND,
        )

        mock_audit.log_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_silver_audit_fallback_timestamp(self, noop_logger):
        """Test _log_silver_audit uses fallback when ingestion_ts is invalid type."""
        from uuid import uuid4

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_audit = MagicMock()
        mock_audit.log_write = AsyncMock()

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger, audit=mock_audit
        )

        valid_uuid = str(uuid4())
        await writer._log_silver_audit(
            table_name="test.table",
            records=[
                {
                    "_run_id": valid_uuid,
                    "_ingestion_ts": 12345,  # Invalid type - will use fallback
                    "_run_type": "rebuild",
                    "_source_batch_id": "batch-789",
                }
            ],
            mode=SilverWriteMode.DELETE,
        )

        mock_audit.log_write.assert_called_once()


@pytest.mark.unit
class TestSilverWriterCsvExport:
    """Tests for SilverWriter CSV export integration."""

    @pytest.mark.asyncio
    async def test_write_silver_with_csv_exporter(self, noop_logger, valid_records):
        """Test write_silver calls CSV exporter when configured."""

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        mock_exporter.export = AsyncMock()

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

        with (
            patch(
                "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch("bioetl.infrastructure.storage.silver_writer.write_deltalake"),
        ):
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
            )

            mock_exporter.export.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_csv_exporter_with_merge_passes_primary_keys(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test CSV exporter receives primary_keys when mode is merge."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        export_calls = []

        async def capture_export(*args, **kwargs):
            export_calls.append(kwargs)

        mock_exporter.export = capture_export

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
                base_path=str(tmp_path / "silver"),
                logger=noop_logger,
                csv_exporter=mock_exporter,
            )

            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            assert len(export_calls) == 1
            assert export_calls[0]["primary_keys"] == ["entity_id"]


@pytest.mark.unit
class TestSilverWriterLineage:
    """Tests for SilverWriter lineage tracking (REQ-LINEAGE-001)."""

    @pytest.mark.asyncio
    async def test_write_silver_without_bronze_refs(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test write_silver works without bronze_refs (backward compatibility)."""
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
                base_path=str(tmp_path / "silver"), logger=noop_logger
            )

            # Should not raise when bronze_refs not provided
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

    @pytest.mark.asyncio
    async def test_write_silver_with_bronze_refs(
        self, noop_logger, valid_records, tmp_path
    ):
        """Test write_silver accepts bronze_refs parameter."""
        from uuid import uuid4

        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
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

        bronze_result = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_123.jsonl.zst",
            record_count=100,
            compressed_size=5000,
            uncompressed_size=20000,
            checksum_blake2="abc123def456",
        )

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
                base_path=str(tmp_path / "silver"), logger=noop_logger
            )

            # Should not raise with bronze_refs
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
                bronze_refs=[bronze_result],
            )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_includes_bronze_paths(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata populates bronze_paths from bronze_refs."""
        from uuid import uuid4

        from bioetl.domain.types import BatchID
        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        bronze_result_1 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_001.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="abc123",
        )

        bronze_result_2 = BronzeWriteResult(
            batch_id=BatchID(uuid4()),
            relative_path="v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            absolute_path="/data/bronze/v1/chembl/activity/2024-01-15/batch_002.jsonl.zst",
            record_count=50,
            compressed_size=2500,
            uncompressed_size=10000,
            checksum_blake2="def456",
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
            bronze_refs=[bronze_result_1, bronze_result_2],
        )

        # Verify metadata writer was called with bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert len(lineage.bronze_paths) == 2
        assert (
            "v1/chembl/activity/2024-01-15/batch_001.jsonl.zst" in lineage.bronze_paths
        )
        assert (
            "v1/chembl/activity/2024-01-15/batch_002.jsonl.zst" in lineage.bronze_paths
        )

    @pytest.mark.asyncio
    async def test_write_silver_metadata_empty_bronze_paths_when_no_refs(
        self, noop_logger, valid_records, mock_metadata_coordinator
    ):
        """Test _write_silver_metadata has empty bronze_paths when bronze_refs=None."""
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
            bronze_refs=None,  # No bronze refs
        )

        # Verify metadata writer was called with empty bronze_paths
        assert len(write_calls) == 1
        metadata = write_calls[0]["metadata"]
        lineage = metadata.lineage
        assert lineage.bronze_paths == []
