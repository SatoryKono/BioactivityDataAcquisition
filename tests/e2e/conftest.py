"""Fixtures for E2E tests with Local-Only architecture.

E2E тесты используют локальное файловое хранилище и in-memory инфраструктуру:
- LocalCheckpointAdapter (файловая система)
- MemoryLock (in-process)
- SilverWriter (локальный Delta Lake)
- VCR cassettes для HTTP-запросов

Запуск:
    make test-e2e       # Все E2E тесты
    uv run python -m pytest tests/e2e/ -v -m e2e --vcr-record=none
    uv run python -m pytest tests/e2e/test_pubchem_compound_e2e.py -v -m e2e --vcr-record=new_episodes
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

import pytest

if TYPE_CHECKING:
    import httpx

    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.exceptions.network import ExternalServiceError
    from bioetl.domain.resilience import RetryConfig
    from bioetl.domain.types import RunID, RunType

# Default timeout for E2E tests (seconds)
# E2E tests run full pipelines with HTTP calls, Delta Lake operations,
# and PyArrow imports which can be slow, especially on Python 3.14
E2E_DEFAULT_TIMEOUT = 120
_TRANSIENT_EXTERNAL_ERROR_MARKERS: tuple[str, ...] = (
    "429",
    "500",
    "502",
    "503",
    "504",
    "timeout",
)
_TRANSIENT_HTTP_STATUS_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_E2E_SKIP_PREFIX = "E2E_SKIP"
_E2E_HEALTHCHECK_PLAYBACK_FAILURE_MARKERS: tuple[str, ...] = (
    "health check failed for: data_source",
)

_E2E_VCR_CASSETTE_DIR_BY_TEST: dict[str, str] = {
    "test_pubchem_compound_pipeline": "pubchem",
    "test_health_check": "pubmed",
    "test_chembl_and_uniprot_sequential_run": "multi_provider",
}

_E2E_VCR_CASSETTE_NAME_OVERRIDES: dict[str, str] = {
    "TestChEMBLPipelineE2E.test_chembl_activity_full_run": (
        "test_chembl_activity_full_run"
    ),
}


@cache
def _get_retry_config() -> RetryConfig:
    """Build retry config lazily so collection avoids heavy domain imports."""
    from bioetl.domain.resilience import RetryConfig

    return RetryConfig(
        max_attempts=3,
        multiplier=2.0,
        base_delay=0.25,
        max_delay=1.0,
        jitter_range=(0.0, 0.0),
        retryable_statuses=_TRANSIENT_HTTP_STATUS_CODES,
        jitter_seed=20260304,
    )


@cache
def _load_delta_table() -> type[Any]:
    """Import DeltaTable lazily to keep collect-only runs lighter."""
    from deltalake import DeltaTable

    return DeltaTable


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Automatically apply default timeout to all E2E tests.

    This hook runs after test collection and adds a timeout marker
    to E2E tests that don't already have one. This ensures pipeline
    tests have enough time to complete without timing out during
    Delta Lake/PyArrow operations.
    """
    for item in items:
        # Only apply to tests in this directory (e2e)
        if "e2e" in str(item.fspath):
            # Check if test already has a timeout marker
            existing_timeout = item.get_closest_marker("timeout")
            if existing_timeout is None:
                # Add default E2E timeout
                item.add_marker(pytest.mark.timeout(E2E_DEFAULT_TIMEOUT))


@pytest.fixture(scope="module")
def vcr_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """Return provider-specific cassette directory for E2E tests."""
    test_name = request.node.name
    provider_dir = _E2E_VCR_CASSETTE_DIR_BY_TEST.get(test_name, "chembl")
    cassette_dir = (
        Path(__file__).resolve().parents[1] / "fixtures" / "vcr" / provider_dir
    )
    cassette_dir.mkdir(parents=True, exist_ok=True)
    return cassette_dir


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Return normalized cassette file name in snake_case format."""
    node_name = request.node.name
    if node_name is None:
        msg = "pytest node name must be defined for VCR cassette resolution"
        raise RuntimeError(msg)
    qualified_name = (
        f"{request.node.cls.__name__}.{node_name}" if request.node.cls else node_name
    )
    qualified_override = _E2E_VCR_CASSETTE_NAME_OVERRIDES.get(qualified_name)
    if qualified_override is not None:
        return qualified_override
    if node_name in _E2E_VCR_CASSETTE_NAME_OVERRIDES:
        return _E2E_VCR_CASSETTE_NAME_OVERRIDES[node_name]
    return node_name


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Настройка окружения для E2E тестов (Local-Only)."""
    os.environ.setdefault("BIOETL_ENV", "dev")
    os.environ.setdefault("BIOETL_TEST_MODE", "true")
    os.environ.setdefault("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    # Keep the legacy flag for test callers, but populate the canonical nested
    # setting that ``Settings.pipeline.relaxed_dq`` actually reads.
    os.environ.setdefault("BIOETL_TEST_RELAXED_DQ", "1")
    os.environ.setdefault("BIOETL_PIPELINE__RELAXED_DQ", "1")
    os.environ.setdefault("BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PROFILE", "e2e")
    # Prevent shutil.get_terminal_size hangs in CI/Test environments
    os.environ["COLUMNS"] = "80"
    os.environ["LINES"] = "24"

    # Configure pandas to avoid terminal size detection
    import pandas as pd

    pd.set_option("display.width", 80)
    pd.set_option("display.max_columns", 20)

    # Pre-import pandera engines to avoid import contention in thread pool executors.
    # On Windows, pandera's is_geopandas_dtype() check can hang when importing
    # during schema validation in concurrent threads. Pre-importing warms up
    # the import cache and prevents filesystem stat hangs.
    try:
        import pandera.engines.pandas_engine  # noqa: F401
    except ImportError:
        pass  # Pandera may not have this submodule in all versions

    # Register all pipelines (required for bootstrap_pipeline_runner to work)
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines()

    yield

    try:
        from bioetl.infrastructure.config import get_settings

        get_settings.cache_clear()
    except ImportError:
        pass


@contextmanager
def managed_e2e_data_dir(data_dir: Path) -> Generator[Path, None, None]:
    """Configure one temporary BIOETL_DATA_DIR with cache-safe lifecycle.

    Supports both function-scoped and module-scoped test setups so expensive
    E2E suites can share one data directory when they intentionally reuse the
    same pipeline run output across multiple assertions.
    """
    from bioetl.infrastructure.config import get_pipeline_config, get_settings

    data_dir.mkdir(parents=True, exist_ok=True)

    # Create Medallion subdirectories
    for subdir in ("bronze", "silver", "gold", "checkpoints", "quarantine"):
        (data_dir / subdir).mkdir(exist_ok=True)

    previous_data_dir = os.environ.get("BIOETL_DATA_DIR")
    os.environ["BIOETL_DATA_DIR"] = str(data_dir)

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    settings = get_settings()
    assert str(data_dir) in str(settings.bronze_path), (
        f"Settings not using test data dir. Expected {data_dir} in {settings.bronze_path}"
    )

    try:
        yield data_dir
    finally:
        if previous_data_dir is None:
            os.environ.pop("BIOETL_DATA_DIR", None)
        else:
            os.environ["BIOETL_DATA_DIR"] = previous_data_dir
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()


def clone_e2e_data_dir_snapshot(snapshot_dir: Path, target_dir: Path) -> None:
    """Clone prepared E2E data into a fresh temp directory for isolated reuse."""
    shutil.copytree(snapshot_dir, target_dir)


@pytest.fixture
def e2e_data_dir(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """Создание временной директории данных с настройкой окружения.

    Создаёт структуру директорий Medallion Architecture:
    - bronze/
    - silver/
    - gold/
    - checkpoints/
    - quarantine/
    """
    del monkeypatch  # kept for backward-compatible fixture signature
    data_dir = tmp_path / "bioetl_data"
    with managed_e2e_data_dir(data_dir) as prepared_dir:
        yield prepared_dir


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
        await asyncio.sleep(0)
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
    run_type: RunType | None = None,
    resume: bool = False,
    query: str | None = None,
    filter_ids: tuple[str, ...] | None = None,
    filter_field: str | None = None,
) -> PipelineRunContext:
    """Создание контекста для E2E теста.

    Args:
        pipeline_name: Имя пайплайна (например, 'chembl_activity')
        limit: Лимит записей для извлечения
        run_type: Тип запуска (INCREMENTAL, BACKFILL, REBUILD)
        resume: Возобновление с чекпоинта
        query: Поисковый запрос (для PubChem)
        filter_ids: IDs для фильтрации (если указаны, используется вместо YAML filter)
        filter_field: Поле для фильтрации (обязательно если указаны filter_ids)

    Returns:
        PipelineRunContext для передачи в bootstrap_pipeline_runner
    """
    from bioetl.domain.context import InputFilterContext
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.context import current_utc_time
    from bioetl.domain.types import RunID, RunType

    if filter_ids is not None and filter_field is not None:
        input_filter = InputFilterContext.from_ids(filter_ids, filter_field)
    else:
        input_filter = InputFilterContext.disabled()

    resolved_run_type = run_type or RunType.INCREMENTAL
    return PipelineRunContext(
        pipeline_name=pipeline_name,
        run_id=RunID(uuid4()),
        run_type=resolved_run_type,
        started_at=current_utc_time(),
        resume=resume,
        limit=limit,
        query=query,
        input_filter=input_filter,
    )


def _is_transient_external_error(exc: ExternalServiceError) -> bool:
    """Return True when ExternalServiceError is likely upstream/transient."""
    if exc.status_code in _TRANSIENT_HTTP_STATUS_CODES:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_EXTERNAL_ERROR_MARKERS)


def _is_transient_http_status_error(exc: httpx.HTTPStatusError) -> bool:
    """Return True when HTTPStatusError is likely upstream/transient."""
    return exc.response.status_code in _TRANSIENT_HTTP_STATUS_CODES


def is_external_healthcheck_playback_failure(exc: Exception) -> bool:
    """Return True when playback fails due to external health-check mismatch."""
    from bioetl.domain.exceptions.infrastructure import InfrastructureError

    if not isinstance(exc, InfrastructureError):
        return False
    message = str(exc).lower()
    return any(
        marker in message for marker in _E2E_HEALTHCHECK_PLAYBACK_FAILURE_MARKERS
    )


def build_e2e_skip_reason(
    reason_code: str,
    *,
    pipeline_name: str,
    detail: str,
) -> str:
    """Build deterministic skip reason message for CI classification."""
    return f"{_E2E_SKIP_PREFIX}[{reason_code}] pipeline={pipeline_name}; {detail}"


def _create_retry_run_context(
    context: PipelineRunContext, attempt: int
) -> PipelineRunContext:
    """Return stable retry context, replacing run_id only after first attempt."""
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.types import RunID

    if attempt == 0:
        return context
    return cast(PipelineRunContext, replace(context, run_id=RunID(uuid4())))


def _get_transient_reason_code(exc: Exception | None) -> str:
    """Map transient exception to deterministic CI skip code."""
    import httpx
    from bioetl.domain.exceptions.network import ExternalServiceError

    if isinstance(exc, ExternalServiceError) and exc.status_code == 429:
        return "INFRA_FLAKY_429"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return "INFRA_FLAKY_429"
    return "INFRA_FLAKY_UPSTREAM"


def _skip_transient_pipeline_run(
    context: PipelineRunContext, transient_exc: Exception | None
) -> None:
    """Skip test with deterministic message after transient retry exhaustion."""
    retry_config = _get_retry_config()
    pytest.skip(
        build_e2e_skip_reason(
            _get_transient_reason_code(transient_exc),
            pipeline_name=context.pipeline_name,
            detail=(
                f"transient upstream error after "
                f"{retry_config.max_attempts} attempts: {transient_exc}"
            ),
        )
    )


async def run_pipeline_or_skip_transient(context: PipelineRunContext) -> Any:
    """Run pipeline with deterministic retries; skip on transient exhaustion."""
    import httpx
    from bioetl.domain.exceptions.network import ExternalServiceError

    from bioetl.composition.bootstrap import bootstrap_pipeline_runner

    retry_config = _get_retry_config()
    transient_exc: Exception | None = None
    for attempt in range(retry_config.max_attempts):
        run_context = _create_retry_run_context(context, attempt)
        runner = bootstrap_pipeline_runner(run_context)
        try:
            await runner.run()
            return runner
        except ExternalServiceError as exc:
            if not _is_transient_external_error(exc):
                raise
            transient_exc = exc
        except httpx.HTTPStatusError as exc:
            if not _is_transient_http_status_error(exc):
                raise
            transient_exc = exc

        if retry_config.is_last_attempt(attempt):
            _skip_transient_pipeline_run(context, transient_exc)

        delay = retry_config.calculate_delay(attempt, url=context.pipeline_name)
        await asyncio.sleep(delay)

    msg = "run_pipeline_or_skip_transient exhausted without terminal decision"
    raise RuntimeError(msg)


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
        Список найденных Bronze-артефактов

    Raises:
        AssertionError: Если файлы не найдены

    Note:
        Handles both standard and flat_structure layouts. Prefers real Bronze
        data files, but falls back to Bronze metadata sidecars when the runtime
        path only materializes metadata for the current execution mode.
    """

    def _find_artifacts(root: Path) -> list[Path]:
        files = list(root.rglob("*.jsonl.zst"))
        if files:
            return files
        files = list(root.rglob("*.jsonl"))
        if files:
            return files
        return list(root.rglob("*_metadata.yaml"))

    candidate_roots = (
        data_dir / "bronze",
        data_dir / "output" / "bronze",
        Path("data") / "output" / "bronze",
    )
    checked_paths: list[Path] = []

    for root in candidate_roots:
        checked_paths.append(root / provider / entity)
        checked_paths.append(root)

        standard_path = root / provider / entity
        if standard_path.exists():
            files = _find_artifacts(standard_path)
            if files:
                return files

        if root.exists():
            files = _find_artifacts(root)
            if files:
                return files

    checked = "\n".join(f"  - {path}" for path in checked_paths)
    raise AssertionError(f"No Bronze files found. Checked paths:\n{checked}")


def assert_run_manifest_exists(data_dir: Path, run_id: RunID) -> dict[str, Any]:
    """Assert that one control-plane manifest exists for the given run."""
    manifest_base = data_dir / "output" / "control" / "run_manifest"
    run_index_path = manifest_base / "_by_run_id" / f"{run_id}.txt"
    assert run_index_path.exists(), f"Run-manifest index missing for run_id={run_id}"

    manifest_id = run_index_path.read_text(encoding="utf-8").strip()
    assert manifest_id, f"Run-manifest index empty for run_id={run_id}"

    manifest_path = manifest_base / f"{manifest_id}.json"
    assert manifest_path.exists(), f"Run-manifest payload missing: {manifest_path}"

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "Run-manifest payload must be a JSON object"
    assert payload.get("run_id") == str(run_id)
    assert payload.get("manifest_id") == manifest_id
    assert payload.get("execution_fingerprint")
    return payload


def assert_run_ledger_has_events(
    data_dir: Path,
    run_id: RunID,
    expected_events: tuple[str, ...],
) -> list[dict[str, Any]]:
    """Assert that one control-plane ledger exists and contains expected events."""
    ledger_base = data_dir / "output" / "control" / "run_ledger"
    run_index_path = ledger_base / "_by_run_id" / f"{run_id}.txt"
    assert run_index_path.exists(), f"Run-ledger index missing for run_id={run_id}"

    manifest_id = run_index_path.read_text(encoding="utf-8").strip()
    assert manifest_id, f"Run-ledger index empty for run_id={run_id}"

    ledger_path = ledger_base / f"{manifest_id}.jsonl"
    assert ledger_path.exists(), f"Run-ledger payload missing: {ledger_path}"

    entries = [
        json.loads(line)
        for line in ledger_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert entries, f"Run-ledger is empty: {ledger_path}"

    observed_event_types = {
        str(entry.get("event_type")) for entry in entries if isinstance(entry, dict)
    }
    missing = sorted(set(expected_events) - observed_event_types)
    assert not missing, (
        f"Run-ledger missing expected events for run_id={run_id}: {missing}; "
        f"observed={sorted(observed_event_types)}"
    )
    return entries


def _build_table_name_variants(table_name: str) -> list[str]:
    """Build deterministic logical-name variants for table path resolution."""
    normalized = table_name.replace("\\", "/").strip("/")
    variants = {
        normalized,
        normalized.replace(".", "/"),
        normalized.replace("/", "."),
        normalized.replace("/", "_"),
        normalized.replace(".", "_"),
    }
    if "_" in normalized:
        variants.add(normalized.replace("_", "/", 1))
        variants.add(normalized.replace("_", ".", 1))
    return sorted(variant for variant in variants if variant)


def _resolve_silver_table_path(data_dir: Path, table_name: str) -> Path:
    """Resolve Silver Delta table path across naming/layout variants."""
    silver_base = data_dir / "output" / "silver"
    variants = _build_table_name_variants(table_name)

    # Prefer explicit logical-name candidates first.
    for variant in variants:
        candidate = silver_base / variant.replace(".", "/")
        if candidate.exists() and (candidate / "_delta_log").exists():
            return candidate

    # Flat-structure Delta table at layer root.
    if silver_base.exists() and (silver_base / "_delta_log").exists():
        return silver_base

    # Fallback: discover existing delta tables and match by relative path variants.
    if silver_base.exists():
        discovered = sorted({p.parent for p in silver_base.rglob("_delta_log")})
        variant_set = set(variants)
        for candidate in discovered:
            rel = candidate.relative_to(silver_base).as_posix()
            candidate_variants = {
                rel,
                rel.replace("/", "."),
                rel.replace("/", "_"),
            }
            if candidate_variants & variant_set:
                return candidate

    checked = [str(silver_base / variant.replace(".", "/")) for variant in variants]
    raise AssertionError(
        "Silver table does not exist. "
        f"table_name={table_name}, checked={checked}, flat={silver_base}"
    )


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

    Note:
        Handles both standard layout (data_dir/output/silver/{table_name}/)
        and flat_structure layout (data_dir/output/silver/) for pipelines
        with flat_structure: true in their config.
    """
    table_path = _resolve_silver_table_path(data_dir, table_name)

    dt = _load_delta_table()(str(table_path))
    df = dt.to_pyarrow_table()
    count = len(df)

    if count < expected_min:
        raise AssertionError(
            f"Silver table {table_name} has {count} records, expected >= {expected_min}"
        )

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

    Note:
        Handles both standard and flat_structure layouts.
    """
    # Standard path: data_dir/output/gold/{table_name}/
    table_path = data_dir / "output" / "gold" / table_name

    # Flat structure path: data_dir/output/gold/ (Delta table at root)
    flat_path = data_dir / "output" / "gold"

    # Check both locations - standard path first, then flat structure
    if not table_path.exists():
        # Try flat_structure path (check for _delta_log at root)
        if flat_path.exists() and (flat_path / "_delta_log").exists():
            table_path = flat_path
        else:
            raise AssertionError(f"Gold table does not exist: {table_path}")

    dt = _load_delta_table()(str(table_path))
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

    Note:
        Handles both standard and flat_structure layouts.
    """
    table_path = _resolve_silver_table_path(data_dir, table_name)

    dt = _load_delta_table()(str(table_path))
    records = dt.to_pyarrow_table().to_pylist()

    # Validate that records are dictionaries
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Expected record at index {i} to be a dict, got {type(record).__name__}. "
                f"Table: {table_name}, Record: {record}"
            )

    return records


def get_gold_records(data_dir: Path, table_name: str) -> list[dict]:
    """Получить все записи из Gold таблицы.

    Args:
        data_dir: Корневая директория данных
        table_name: Имя таблицы

    Returns:
        Список словарей с записями

    Note:
        Handles both standard and flat_structure layouts.
    """
    # Standard path: data_dir/output/gold/{table_name}/
    table_path = data_dir / "output" / "gold" / table_name

    # Try flat_structure path if standard doesn't exist
    if not table_path.exists():
        flat_path = data_dir / "output" / "gold"
        if flat_path.exists() and (flat_path / "_delta_log").exists():
            table_path = flat_path

    dt = _load_delta_table()(str(table_path))
    records = dt.to_pyarrow_table().to_pylist()

    # Validate that records are dictionaries
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Expected record at index {i} to be a dict, got {type(record).__name__}. "
                f"Gold table: {table_name}, Record: {record}"
            )

    return records
