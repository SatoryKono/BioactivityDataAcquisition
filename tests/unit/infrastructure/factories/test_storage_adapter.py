"""Unit tests for StorageAdapter."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.composition.factories.storage_factory import StorageAdapter
from bioetl.domain.ports import StoragePort
from bioetl.domain.types import RunType


@pytest.fixture
def mock_bronze_writer() -> MagicMock:
    """Create mock bronze writer."""
    writer = MagicMock()
    writer.write_bronze = AsyncMock()
    return writer


@pytest.fixture
def mock_silver_writer() -> MagicMock:
    """Create mock silver writer."""
    writer = MagicMock()
    writer.write_silver = AsyncMock()
    return writer


@pytest.fixture
def mock_gold_writer() -> MagicMock:
    """Create mock gold writer."""
    writer = MagicMock()
    writer.write_gold = AsyncMock()
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

        await storage_adapter.write_bronze(
            records=records,
            provider="chembl",
            entity="activity",
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        mock_bronze_writer.write_bronze.assert_called_once()
        call_kwargs = mock_bronze_writer.write_bronze.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity"] == "activity"
        assert call_kwargs["date"] == date
        assert call_kwargs["batch_id"] == batch_id
        assert call_kwargs["run_id"] == run_id
        assert call_kwargs["run_type"] == run_type


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

        await storage_adapter.write_gold(
            table_name="gold_table",
            records=records,
            mode="overwrite",
        )

        mock_gold_writer.write_gold.assert_called_once()
        call_kwargs = mock_gold_writer.write_gold.call_args[1]
        assert call_kwargs["table_name"] == "gold_table"
        assert call_kwargs["records"] == records
        assert call_kwargs["mode"] == "overwrite"

    @pytest.mark.asyncio
    async def test_write_gold_append_mode(
        self,
        storage_adapter: StorageAdapter,
        mock_gold_writer: MagicMock,
    ) -> None:
        """Test write_gold with append mode."""
        await storage_adapter.write_gold(
            table_name="gold_table",
            records=[{"id": 1}],
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
        await storage_adapter.write_gold(
            table_name="test",
            records=[],
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
