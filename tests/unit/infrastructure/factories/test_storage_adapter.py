"""Unit tests for StorageAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.composition.factories.storage_adapter import StorageAdapter
from bioetl.domain.ports import StoragePort
from bioetl.domain.types import RunType


@pytest.fixture
def mock_bronze_writer() -> MagicMock:
    """Create mock bronze writer."""
    writer = MagicMock()
    writer.write_bronze = AsyncMock()
    writer.cleanup_old_files = AsyncMock()
    return writer


@pytest.fixture
def mock_silver_writer() -> MagicMock:
    """Create mock silver writer."""
    writer = MagicMock()
    writer.write_silver = AsyncMock()
    writer.vacuum = AsyncMock()
    return writer


@pytest.fixture
def mock_gold_writer() -> MagicMock:
    """Create mock gold writer."""
    writer = MagicMock()
    writer.write_gold = AsyncMock()
    writer.write_gold_merged = AsyncMock()
    return writer


@pytest.fixture
def storage_adapter(
    mock_bronze_writer: MagicMock,
    mock_silver_writer: MagicMock,
    mock_gold_writer: MagicMock,
) -> StorageAdapter:
    """Create StorageAdapter with mocked writers."""
    return StorageAdapter(
        bronze_writer=mock_bronze_writer,
        silver_writer=mock_silver_writer,
        gold_writer=mock_gold_writer,
    )


@pytest.mark.unit
class TestStorageAdapterInit:
    """Tests for StorageAdapter initialization."""

    def test_init(
        self,
        mock_bronze_writer: MagicMock,
        mock_silver_writer: MagicMock,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test adapter initialization."""
        adapter = StorageAdapter(
            bronze_writer=mock_bronze_writer,
            silver_writer=mock_silver_writer,
            gold_writer=mock_gold_writer,
        )

        assert adapter.bronze is mock_bronze_writer
        assert adapter.silver is mock_silver_writer
        assert adapter.gold is mock_gold_writer

    def test_implements_storage_port(self, storage_adapter: StorageAdapter) -> None:
        """Test that StorageAdapter implements StoragePort protocol."""
        assert isinstance(storage_adapter, StoragePort)

    def test_requires_silver_schema_marker(
        self, storage_adapter: StorageAdapter
    ) -> None:
        """Test that REQUIRES_SILVER_SCHEMA is set."""
        assert storage_adapter.REQUIRES_SILVER_SCHEMA is True


@pytest.mark.unit
class TestStorageAdapterWriteBronze:
    """Tests for write_bronze method."""

    @pytest.mark.asyncio
    async def test_write_bronze_delegates(
        self,
        storage_adapter: StorageAdapter,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that write_bronze delegates to bronze writer."""
        records = iter([b'{"id": 1}\n', b'{"id": 2}\n'])
        date = datetime(2024, 1, 15)
        batch_id = uuid4()
        run_id = uuid4()
        run_type = RunType.INCREMENTAL
        # Fixed timestamp for deterministic tests (ADR-014)
        ingestion_ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)

        await storage_adapter.write_bronze(
            records=records,
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
            ingestion_ts=ingestion_ts,
        )

        mock_bronze_writer.write_bronze.assert_called_once()
        call_kwargs = mock_bronze_writer.write_bronze.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity"] == "activity"
        assert call_kwargs["date"] == date
        assert call_kwargs["batch_id"] == batch_id
        assert call_kwargs["run_id"] == run_id
        assert call_kwargs["run_type"] == run_type
        assert call_kwargs["ingestion_ts"] == ingestion_ts


@pytest.mark.unit
class TestStorageAdapterWriteSilver:
    """Tests for write_silver method."""

    @pytest.mark.asyncio
    async def test_write_silver_delegates(
        self,
        storage_adapter: StorageAdapter,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test that write_silver delegates to silver writer."""
        records = [{"id": 1, "name": "test"}]
        schema = MagicMock()

        await storage_adapter.write_silver(
            table_name="test_table",
            records=records,
            primary_keys=["id"],
            schema=schema,
            mode="merge",
        )

        mock_silver_writer.write_silver.assert_called_once()
        call_kwargs = mock_silver_writer.write_silver.call_args[1]
        assert call_kwargs["table_name"] == "test_table"
        assert call_kwargs["records"] == records
        assert call_kwargs["primary_keys"] == ["id"]
        assert call_kwargs["schema"] is schema

    @pytest.mark.asyncio
    async def test_write_silver_default_mode(
        self,
        storage_adapter: StorageAdapter,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test write_silver uses default merge mode."""
        await storage_adapter.write_silver(
            table_name="test",
            records=[],
            primary_keys=["id"],
            schema=MagicMock(),
        )

        mock_silver_writer.write_silver.assert_called_once()


@pytest.mark.unit
class TestStorageAdapterWriteGold:
    """Tests for write_gold method."""

    @pytest.mark.asyncio
    async def test_write_gold_delegates(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test that write_gold delegates to gold writer."""
        records = [{"id": 1, "aggregated_value": 100}]
        mock_schema = MagicMock()

        await storage_adapter.write_gold(
            table_name="gold_table",
            records=records,
            schema=mock_schema,
            mode="overwrite",
        )

        mock_gold_writer.write_gold.assert_called_once()
        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["table_name"] == "gold_table"
        assert call_kwargs["records"] == records
        assert call_kwargs["schema"] == mock_schema
        assert call_kwargs["mode"] == "overwrite"

    @pytest.mark.asyncio
    async def test_write_gold_append_mode(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test write_gold with append mode."""
        mock_schema = MagicMock()
        await storage_adapter.write_gold(
            table_name="gold_table",
            records=[{"id": 1}],
            schema=mock_schema,
            mode="append",
        )

        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["mode"] == "append"

    @pytest.mark.asyncio
    async def test_write_gold_default_mode(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test write_gold uses default overwrite mode."""
        mock_schema = MagicMock()
        await storage_adapter.write_gold(
            table_name="test",
            records=[],
            schema=mock_schema,
        )

        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["mode"] == "overwrite"


@pytest.mark.unit
class TestStorageAdapterClose:
    """Tests for aclose method."""

    @pytest.mark.asyncio
    async def test_aclose(self, storage_adapter: StorageAdapter) -> None:
        """Test aclose completes without error."""
        # Should not raise
        await storage_adapter.aclose()

    @pytest.mark.asyncio
    async def test_aclose_is_noop(self, storage_adapter: StorageAdapter) -> None:
        """Test aclose is a no-op (writers don't need cleanup)."""
        # Can be called multiple times
        await storage_adapter.aclose()
        await storage_adapter.aclose()


@pytest.mark.unit
class TestStorageAdapterOptimize:
    """Tests for optimize method."""

    @pytest.mark.asyncio
    async def test_optimize_delegates_to_vacuum(
        self,
        storage_adapter: StorageAdapter,
        mock_silver_writer: MagicMock,
    ) -> None:
        """Test that optimize calls vacuum."""
        # Mock vacuum method on adapter since it calls self.vacuum
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="chembl.activity", retention_hours=168, dry_run=True
        )

        storage_adapter.vacuum.assert_called_once_with("chembl.activity", 168, True)

    @pytest.mark.asyncio
    async def test_optimize_calls_bronze_cleanup(
        self,
        storage_adapter: StorageAdapter,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that optimize calls bronze cleanup for valid table names."""
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="chembl.activity", retention_hours=168, dry_run=False
        )

        mock_bronze_writer.cleanup_old_files.assert_called_once()
        call_kwargs = mock_bronze_writer.cleanup_old_files.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity"] == "activity"
        assert "cutoff_date" in call_kwargs
        assert call_kwargs["dry_run"] is False

    @pytest.mark.asyncio
    async def test_optimize_skips_bronze_cleanup_for_no_dot(
        self,
        storage_adapter: StorageAdapter,
        mock_bronze_writer: MagicMock,
    ) -> None:
        """Test that optimize skips bronze cleanup if table name has no dot."""
        storage_adapter.vacuum = AsyncMock()  # type: ignore

        await storage_adapter.optimize(
            table_name="invalid_table_name",
            retention_hours=168,
        )

        mock_bronze_writer.cleanup_old_files.assert_not_called()


@pytest.mark.unit
class TestStorageAdapterWriteGoldMerged:
    """Tests for composite Gold schema binding in write_gold_merged."""

    @pytest.mark.asyncio
    async def test_write_gold_merged_binds_composite_publication_schema(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Composite publication table should pass bound schema to GoldWriter."""
        await storage_adapter.write_gold_merged(
            table_name="composite/publication",
            records=[{"entity_id": "pub:1", "content_hash": "h1"}],
        )

        call_kwargs = mock_gold_writer.write_gold_merged.call_args[1]
        assert call_kwargs["schema"].__name__ == "CompositePublicationGoldSchema"

    @pytest.mark.asyncio
    async def test_write_gold_merged_unknown_table_uses_no_schema(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Unknown merged table keeps backward-compatible schema=None behavior."""
        await storage_adapter.write_gold_merged(
            table_name="custom/merged",
            records=[{"entity_id": "x", "content_hash": "y"}],
        )

        call_kwargs = mock_gold_writer.write_gold_merged.call_args[1]
        assert call_kwargs["schema"] is None
