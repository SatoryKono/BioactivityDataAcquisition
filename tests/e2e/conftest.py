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

from __future__ import annotations

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

    # Register all pipelines (required for bootstrap_pipeline to work)
    from bioetl.composition.factories.pipeline_factories import register_all_pipelines

    register_all_pipelines()

    yield

    try:
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@pytest.fixture
def e2e_data_dir(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """Создание временной директории данных с настройкой окружения.

    Создаёт структуру директорий Medallion Architecture:
    - bronze/
    - silver/
    - gold/
    - checkpoints/
    - quarantine/

    IMPORTANT: Order matters:
    1. Set env var first
    2. Clear caches to ensure new value is picked up
    3. Verify settings use correct path
    """
    from bioetl.infrastructure.config import get_pipeline_config, get_settings

    data_dir = tmp_path / "bioetl_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # Create Medallion subdirectories
    for subdir in ("bronze", "silver", "gold", "checkpoints", "quarantine"):
        (data_dir / subdir).mkdir()

    # 1. Set environment variable FIRST
    monkeypatch.setenv("BIOETL_DATA_DIR", str(data_dir))

    # 2. Clear caches to pick up new env var
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    # 3. Verify settings use correct path
    settings = get_settings()
    assert str(data_dir) in str(settings.bronze_path), (
        f"Settings not using test data dir. Expected {data_dir} in {settings.bronze_path}"
    )

    yield data_dir

    # Cleanup: clear caches
    get_settings.cache_clear()
    get_pipeline_config.cache_clear()


@pytest.fixture
def e2e_pipeline_limit() -> int:
    """Лимит записей для E2E тестов (минимальный для скорости)."""
    return 10


@pytest.fixture
def e2e_temp_storage(tmp_path: Path) -> dict[str, Path]:
    """Temporary storage paths for E2E tests.

    Returns dict with bronze, silver, gold, and checkpoints paths.
    """
    paths = {
        "bronze": tmp_path / "bronze",
        "silver": tmp_path / "silver",
        "gold": tmp_path / "gold",
        "checkpoints": tmp_path / "checkpoints",
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


class MockRedisClient:
    """Mock Redis client for Local-Only architecture (no real Redis)."""

    async def keys(self, pattern: str) -> list:
        """Return empty list - no locks in Local-Only mode."""
        return []


@pytest.fixture
def e2e_redis_client() -> MockRedisClient:
    """Mock Redis client for E2E tests (Local-Only architecture)."""
    return MockRedisClient()


class MockMinioClient:
    """Mock MinIO client for Local-Only architecture (no real MinIO)."""

    pass


@pytest.fixture
def e2e_minio_client() -> MockMinioClient:
    """Mock MinIO client for E2E tests (Local-Only architecture)."""
    return MockMinioClient()


def create_test_context(
    pipeline_name: str,
    limit: int | None = 10,
    run_type: RunType = RunType.INCREMENTAL,
    resume: bool = False,
    query: str | None = None,
) -> PipelineRunContext:
    """Создание контекста для E2E теста.

    Args:
        pipeline_name: Имя пайплайна (например, 'chembl_activity')
        limit: Лимит записей для извлечения
        run_type: Тип запуска (INCREMENTAL, BACKFILL, REBUILD)
        resume: Возобновление с чекпоинта
        query: Поисковый запрос (для PubChem)

    Returns:
        PipelineRunContext для передачи в bootstrap_pipeline
    """
    return PipelineRunContext(
        pipeline_name=pipeline_name,
        run_id=uuid4(),
        run_type=run_type,
        resume=resume,
        limit=limit,
        query=query,
    )


# ============================================================================
# Assertion Helpers
# ============================================================================


def assert_bronze_files_exist(data_dir: Path, provider: str, entity: str) -> list[Path]:
    """Проверка существования Bronze-файлов.

    Args:
        data_dir: Корневая директория данных
        provider: Имя провайдера (chembl, pubchem, etc.)
        entity: Тип сущности (activity, molecule, etc.)

    Returns:
        Список найденных Bronze-файлов

    Raises:
        AssertionError: Если файлы не найдены

    Note:
        Path structure is: data_dir/bronze/bronze/v1/{provider}/{entity}/
        (double 'bronze' due to BronzeWriter appending 'bronze/v1/...' to base_path)
    """
    # Note: BronzeWriter uses base_path + "bronze/v1/..." so there's a double bronze
    bronze_path = data_dir / "bronze" / "bronze" / "v1" / provider / entity
    if not bronze_path.exists():
        raise AssertionError(f"Bronze path does not exist: {bronze_path}")

    files = list(bronze_path.rglob("*.jsonl.zst"))
    if not files:
        raise AssertionError(f"No Bronze files found in {bronze_path}")

    return files


def assert_silver_table_has_records(
    data_dir: Path, table_name: str, expected_min: int = 1
) -> int:
    """Проверка наличия записей в Silver Delta таблице.

    Args:
        data_dir: Корневая директория данных
        table_name: Имя таблицы (например, 'chembl_activity')
        expected_min: Минимальное ожидаемое количество записей

    Returns:
        Количество записей в таблице

    Raises:
        AssertionError: Если таблица пуста или записей меньше expected_min
    """
    from deltalake import DeltaTable

    table_path = data_dir / "silver" / table_name
    if not table_path.exists():
        raise AssertionError(f"Silver table does not exist: {table_path}")

    dt = DeltaTable(str(table_path))
    df = dt.to_pyarrow_table()
    count = len(df)

    if count < expected_min:
        raise AssertionError(
            f"Silver table {table_name} has {count} records, expected >= {expected_min}"
        )

    # Verify lineage fields
    assert "_run_id" in df.column_names
    assert "_run_type" in df.column_names
    assert "_ingestion_ts" in df.column_names

    return count


def assert_gold_table_has_records(
    data_dir: Path, table_name: str, expected_min: int = 1
) -> int:
    """Проверка наличия записей в Gold Delta таблице.

    Args:
        data_dir: Корневая директория данных
        table_name: Имя таблицы (например, 'chembl.activity')
        expected_min: Минимальное ожидаемое количество записей

    Returns:
        Количество записей в таблице

    Raises:
        AssertionError: Если таблица пуста или записей меньше expected_min
    """
    from deltalake import DeltaTable

    table_path = data_dir / "gold" / table_name
    if not table_path.exists():
        raise AssertionError(f"Gold table does not exist: {table_path}")

    dt = DeltaTable(str(table_path))
    count = len(dt.to_pyarrow_table())

    if count < expected_min:
        raise AssertionError(
            f"Gold table {table_name} has {count} records, expected >= {expected_min}"
        )

    return count


def get_silver_records(data_dir: Path, table_name: str) -> list[dict]:
    """Получить все записи из Silver таблицы.

    Args:
        data_dir: Корневая директория данных
        table_name: Имя таблицы

    Returns:
        Список словарей с записями
    """
    from deltalake import DeltaTable

    table_path = data_dir / "silver" / table_name
    dt = DeltaTable(str(table_path))
    return dt.to_pyarrow_table().to_pylist()


def get_gold_records(data_dir: Path, table_name: str) -> list[dict]:
    """Получить все записи из Gold таблицы.

    Args:
        data_dir: Корневая директория данных
        table_name: Имя таблицы

    Returns:
        Список словарей с записями
    """
    from deltalake import DeltaTable

    table_path = data_dir / "gold" / table_name
    dt = DeltaTable(str(table_path))
    return dt.to_pyarrow_table().to_pylist()
