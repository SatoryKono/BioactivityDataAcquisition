"""Unit tests for infrastructure factories."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.domain.types import BatchID, RunID, RunType


@pytest.mark.unit
class TestCreateRedisClient:
    """Tests for create_redis_client function."""

    def test_create_redis_client_with_password(self):
        """Test creating Redis client with password."""
        from bioetl.composition.factories.clients import create_redis_client

        settings = MagicMock()
        settings.redis.host = "localhost"
        settings.redis.port = 6379
        settings.redis.db = 0
        settings.redis.password = MagicMock()
        settings.redis.password.get_secret_value.return_value = "secret"

        with patch("bioetl.composition.factories.clients.aioredis.Redis") as mock_redis:
            create_redis_client(settings)

            mock_redis.assert_called_once_with(
                host="localhost",
                port=6379,
                password="secret",
                db=0,
                decode_responses=True,
            )

    def test_create_redis_client_without_password(self):
        """Test creating Redis client without password."""
        from bioetl.composition.factories.clients import create_redis_client

        settings = MagicMock()
        settings.redis.host = "redis.example.com"
        settings.redis.port = 6380
        settings.redis.db = 1
        settings.redis.password = None

        with patch("bioetl.composition.factories.clients.aioredis.Redis") as mock_redis:
            create_redis_client(settings)

            mock_redis.assert_called_once_with(
                host="redis.example.com",
                port=6380,
                password=None,
                db=1,
                decode_responses=True,
            )


@pytest.mark.unit
class TestGetAwsCredentials:
    """Tests for get_aws_credentials function."""

    def test_get_aws_credentials_with_secret(self):
        """Test extracting AWS credentials with secret key."""
        from bioetl.composition.factories.clients import get_aws_credentials

        settings = MagicMock()
        settings.aws.access_key_id = "AKIAIOSFODNN7EXAMPLE"
        settings.aws.secret_access_key = MagicMock()
        settings.aws.secret_access_key.get_secret_value.return_value = (
            "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )

        access_key, secret_key = get_aws_credentials(settings)

        assert access_key == "AKIAIOSFODNN7EXAMPLE"
        assert secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

    def test_get_aws_credentials_without_secret(self):
        """Test extracting AWS credentials without secret key."""
        from bioetl.composition.factories.clients import get_aws_credentials

        settings = MagicMock()
        settings.aws.access_key_id = "AKIAIOSFODNN7EXAMPLE"
        settings.aws.secret_access_key = None

        access_key, secret_key = get_aws_credentials(settings)

        assert access_key == "AKIAIOSFODNN7EXAMPLE"
        assert secret_key is None

    def test_get_aws_credentials_all_none(self):
        """Test extracting AWS credentials when all None."""
        from bioetl.composition.factories.clients import get_aws_credentials

        settings = MagicMock()
        settings.aws.access_key_id = None
        settings.aws.secret_access_key = None

        access_key, secret_key = get_aws_credentials(settings)

        assert access_key is None
        assert secret_key is None


@pytest.mark.unit
class TestStorageAdapter:
    """Tests for StorageAdapter class."""

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
        """Create StorageAdapter instance."""
        from bioetl.composition.factories.storage_factory import StorageAdapter

        return StorageAdapter(
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

    async def test_write_bronze_delegates(self, storage_adapter, mock_bronze_writer):
        """Test write_bronze delegates to bronze writer."""
        batch_id = BatchID(uuid4())
        run_id = RunID(uuid4())
        run_type = RunType.INCREMENTAL
        records = iter([b"record1", b"record2"])

        await storage_adapter.write_bronze(
            records=records,
            provider="chembl",
            entity="activity",
            date=datetime.now(),
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

        mock_bronze_writer.write_bronze.assert_called_once()

    async def test_write_silver_delegates(self, storage_adapter, mock_silver_writer):
        """Test write_silver delegates to silver writer."""
        run_id = uuid4()
        batch_id = BatchID(uuid4())
        ts = datetime.now(UTC)

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
            partition_cols=None,
        )

    async def test_write_gold_delegates(self, storage_adapter, mock_gold_writer):
        """Test write_gold delegates to gold writer."""
        records = [{"metric": "count", "value": 100}]

        await storage_adapter.write_gold(
            table_name="gold.metrics",
            records=records,
            mode="overwrite",
        )

        mock_gold_writer.write_gold.assert_called_once_with(
            table_name="gold.metrics",
            records=records,
            primary_keys=None,
            mode="overwrite",
        )

    async def test_aclose_completes(self, storage_adapter):
        """Test aclose completes without error."""
        await storage_adapter.aclose()
        # Should not raise
