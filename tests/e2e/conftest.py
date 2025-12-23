"""Fixtures for E2E tests with real Docker infrastructure.

E2E тесты предполагают, что Docker-сервисы УЖЕ запущены через:
    docker compose -f docker-compose.test.yml up -d

Или через Makefile:
    make test-e2e       # Запускает Docker, тесты, останавливает Docker
    make test-e2e-local # Использует уже запущенные сервисы
"""

import os
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import boto3
    import redis.asyncio as aioredis


# Конфигурация E2E сервисов
E2E_MINIO_ENDPOINT = os.environ.get("BIOETL_S3_ENDPOINT", "http://localhost:9000")
E2E_MINIO_ACCESS_KEY = os.environ.get("BIOETL_S3_ACCESS_KEY", "minioadmin")
E2E_MINIO_SECRET_KEY = os.environ.get("BIOETL_S3_SECRET_KEY", "minioadmin")
E2E_REDIS_URL = os.environ.get("BIOETL_REDIS_URL", "redis://localhost:16379")


def _wait_for_service(check_fn: callable, timeout: float = 30.0, pause: float = 0.5):
    """Ожидание готовности сервиса."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            if check_fn():
                return True
        except Exception:
            pass
        time.sleep(pause)
    return False


def _is_minio_ready() -> bool:
    """Проверка доступности MinIO."""
    try:
        urllib.request.urlopen(f"{E2E_MINIO_ENDPOINT}/minio/health/live", timeout=2)
        return True
    except (urllib.error.URLError, ConnectionError, OSError):
        return False


def _is_redis_ready() -> bool:
    """Проверка доступности Redis."""
    try:
        host = "localhost"
        port = 16379
        if "://" in E2E_REDIS_URL:
            url_part = E2E_REDIS_URL.split("://")[1]
            if ":" in url_part:
                host, port_str = url_part.split(":")
                port = int(port_str)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        sock.connect((host, port))
        sock.close()
        return True
    except (OSError, ConnectionError):
        return False


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Настройка окружения для E2E тестов."""
    os.environ["BIOETL_ENV"] = "dev"
    os.environ["BIOETL_TEST_MODE"] = "true"
    os.environ["BIOETL_S3_ENDPOINT"] = E2E_MINIO_ENDPOINT
    os.environ["BIOETL_S3_ACCESS_KEY"] = E2E_MINIO_ACCESS_KEY
    os.environ["BIOETL_S3_SECRET_KEY"] = E2E_MINIO_SECRET_KEY
    os.environ["BIOETL_REDIS_URL"] = E2E_REDIS_URL

    if not _wait_for_service(_is_minio_ready, timeout=30.0):
        pytest.skip(
            "MinIO недоступен. Запустите: docker compose -f docker-compose.test.yml up -d"
        )

    if not _wait_for_service(_is_redis_ready, timeout=30.0):
        pytest.skip(
            "Redis недоступен. Запустите: docker compose -f docker-compose.test.yml up -d"
        )

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

    bronze_path.mkdir()
    silver_path.mkdir()
    gold_path.mkdir()
    checkpoints_path.mkdir()

    return {
        "bronze": bronze_path,
        "silver": silver_path,
        "gold": gold_path,
        "checkpoints": checkpoints_path,
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
