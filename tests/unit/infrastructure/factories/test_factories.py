"""Unit tests for infrastructure factories."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

import pyarrow as pa
import pytest

from bioetl.domain.types import RunType


@pytest.mark.unit
class TestStorageBundle:
    """Tests for StorageBundle class."""

    @pytest.fixture
    def mock_bronze_writer(self):
        """Create mock bronze writer."""
        writer = AsyncMock()
        writer.write_bronze = AsyncMock()
        return writer

    @pytest.fixture
    def mock_silver_writer(self):
        """Create mock silver writer."""
        writer = AsyncMock()
        writer.write_silver = AsyncMock()
        return writer

    @pytest.fixture
    def mock_gold_writer(self):
        """Create mock gold writer."""
        writer = AsyncMock()
        writer.write_gold = AsyncMock()
        return writer

    @pytest.fixture
    def storage_adapter(self, mock_bronze_writer, mock_silver_writer, mock_gold_writer):
        """Create StorageBundle instance."""
        from bioetl.composition.factories.storage import StorageBundle

        return StorageBundle(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

    def test_init_stores_writers(
        self,
        storage_adapter,
        mock_bronze_writer,
        mock_silver_writer,
        mock_gold_writer,
    ):
        """Test that initialization stores writers correctly."""
        assert storage_adapter.bronze == mock_bronze_writer
        assert storage_adapter.silver == mock_silver_writer
        assert storage_adapter.gold == mock_gold_writer

    async def test_storage_bundle__bronze_delegates__39d27287(
        self, storage_adapter, mock_bronze_writer
    ):
        """Test write_bronze delegates to bronze writer."""
        batch_id = deterministic_uuid_from_callsite("test_factories")
        run_id = deterministic_uuid_from_callsite("test_factories")
        run_type = RunType.INCREMENTAL
        records = iter([b"record1", b"record2"])
        # Fixed timestamp for deterministic tests (ADR-014)
        ingestion_ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        await storage_adapter.write_bronze(
            records=records,
            provider="chembl",
            entity="activity",
            date=datetime(2024, 1, 15),
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        mock_bronze_writer.write_bronze.assert_called_once()

    async def test_storage_bundle__silver_delegates__8ab8c449(
        self, storage_adapter, mock_silver_writer
    ):
        """Test write_silver delegates to silver writer."""
        run_id = deterministic_uuid_from_callsite("test_factories")
        batch_id = deterministic_batch_uuid_from_callsite("test_factories")
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        records = [
            {
                "id": 1,
                "value": "test",
                "_run_id": str(run_id),
                "_run_type": RunType.INCREMENTAL.value,
                "_source_batch_id": str(batch_id),
                "_ingestion_ts": ts,
            }
        ]
        schema = pa.schema(
            [
                pa.field("id", pa.int64()),
                pa.field("value", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.timestamp("us", tz="UTC")),
            ]
        )

        await storage_adapter.write_silver(
            table_name="test.table",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="merge",
        )

        mock_silver_writer.write_silver.assert_called_once_with(
            table_name="test.table",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="merge",
            column_order=None,
            partition_cols=None,
            on_schema_mismatch="error",
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )

    async def test_storage_bundle__write_gold_delegates__d9b86e8f(
        self, storage_adapter, mock_gold_writer
    ):
        """Test write_gold delegates to gold writer."""
        from unittest.mock import MagicMock

        records = [{"metric": "count", "value": 100}]
        mock_schema = MagicMock()

        await storage_adapter.write_gold(
            table_name="gold.metrics",
            records=records,
            schema=mock_schema,
            mode="overwrite",
        )

        mock_gold_writer.write_gold.assert_called_once_with(
            table_name="gold.metrics",
            records=records,
            schema=mock_schema,
            primary_keys=None,
            mode="overwrite",
            scd_config=None,
            column_order=None,
            ingestion_ts=None,
            run_id=None,
            silver_refs=None,
        )

    async def test_aclose_completes(self, storage_adapter):
        """Test aclose completes without error."""
        await storage_adapter.aclose()
        # Should not raise
