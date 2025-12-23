"""Fixtures for E2E tests with Local-Only architecture.

E2E тесты используют локальное файловое хранилище и in-memory инфраструктуру:
- LocalCheckpoint (файловая система)
- MemoryLock (in-process)
- DeltaWriter (локальный Delta Lake)
- VCR cassettes для HTTP-запросов

Запуск:
    make test-e2e       # Все E2E тесты
    pytest tests/e2e/ -v -m e2e  # Прямой запуск
"""

import os
from collections.abc import Generator
from pathlib import Path
from uuid import uuid4

import pytest

from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import RunType


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Настройка окружения для E2E тестов (Local-Only)."""
    os.environ["BIOETL_ENV"] = "dev"
    os.environ["BIOETL_TEST_MODE"] = "true"

    yield

    try:
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture(scope="session")
def e2e_minio_client(e2e_environment) -> "boto3.client":
    """Создание MinIO клиента и необходимых бакетов для E2E тестов."""
    import boto3
    from botocore.config import Config

    client = boto3.client(
        "s3",
        endpoint_url=E2E_MINIO_ENDPOINT,
        aws_access_key_id=E2E_MINIO_ACCESS_KEY,
        aws_secret_access_key=E2E_MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
    )

    buckets = ["bronze", "silver", "gold", "checkpoints"]
    for bucket in buckets:
        try:
            client.create_bucket(Bucket=bucket)
        except client.exceptions.BucketAlreadyOwnedByYou:
            pass
        except client.exceptions.BucketAlreadyExists:
            pass
        except Exception as e:
            print(f"Warning: Could not create bucket {bucket}: {e}")

    return client


@pytest.fixture
async def e2e_redis_client(e2e_environment) -> "aioredis.Redis":
    """Создание Redis клиента для E2E тестов с очисткой."""
    import redis.asyncio as aioredis

    client = aioredis.from_url(E2E_REDIS_URL)
    await client.flushdb()

    yield client

    await client.flushdb()
    await client.aclose()


@pytest.fixture
def e2e_temp_storage(tmp_path: Path) -> dict[str, Path]:
    """Создание временных директорий для хранилища E2E тестов."""
    bronze_path = tmp_path / "bronze"
    silver_path = tmp_path / "silver"
    gold_path = tmp_path / "gold"
    checkpoints_path = tmp_path / "checkpoints"
    quarantine_path = tmp_path / "quarantine"

    bronze_path.mkdir()
    silver_path.mkdir()
    gold_path.mkdir()
    checkpoints_path.mkdir()
    quarantine_path.mkdir()

    return {
        "bronze": bronze_path,
        "silver": silver_path,
        "gold": gold_path,
        "checkpoints": checkpoints_path,
        "quarantine": quarantine_path,
    }


@pytest.fixture
async def e2e_cleanup_infrastructure(e2e_redis_client):
    """Обеспечение чистого состояния инфраструктуры между E2E тестами."""
    await e2e_redis_client.flushdb()

    yield

    await e2e_redis_client.flushdb()

    try:
        from bioetl.infrastructure.storage.s3_client_pool import S3ClientPool
        S3ClientPool.clear_pool()
    except ImportError:
        pass

    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_data_dir(tmp_path: Path, monkeypatch) -> Path:
    """Создание временной директории данных с настройкой окружения."""
    data_dir = tmp_path / "bioetl_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (data_dir / "bronze").mkdir()
    (data_dir / "silver").mkdir()
    (data_dir / "gold").mkdir()
    (data_dir / "checkpoints").mkdir()
    (data_dir / "quarantine").mkdir()

    # Set environment variable
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))

    # Clear settings cache
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings

        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass

    yield data_dir

    # Cleanup
    try:
        from bioetl.infrastructure.config import get_pipeline_config, get_settings
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_pipeline_limit() -> int:
    """Лимит записей для E2E тестов."""
    return 10


@pytest.fixture
def e2e_vcr_disabled():
    """Маркер отключения VCR для E2E тестов."""
    pass


# Фикстуры для совместимости с pytest-docker API
# Используются тестами, которые ожидают URL сервисов
@pytest.fixture(scope="session")
def minio_service(e2e_environment) -> str:
    """URL MinIO сервиса для E2E тестов (совместимость с pytest-docker)."""
    return E2E_MINIO_ENDPOINT


@pytest.fixture(scope="session")
def redis_service(e2e_environment) -> str:
    """URL Redis сервиса для E2E тестов (совместимость с pytest-docker)."""
    return E2E_REDIS_URL
