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
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Callable, Generator, Mapping
from contextlib import contextmanager
from dataclasses import replace
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import unquote, urlparse
from uuid import UUID, uuid5
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest
from tests.helpers.clock import FIXED_TEST_TIME
from tests.helpers.vcr_config import (
    build_cassette_dir,
    infer_provider_cassette_dir,
    is_git_lfs_pointer,
    resolve_cassette_name,
    resolve_requested_cassette_path,
)

if TYPE_CHECKING:
    import httpx

    from bioetl.domain.control_plane import RunInputSnapshotRef
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.exceptions.network import ExternalServiceError
    from bioetl.domain.resilience import RetryConfig
    from bioetl.domain.types import RunID, RunType


def _resolve_e2e_default_timeout(*, platform: str = sys.platform) -> int:
    """Return the platform-aware pytest timeout budget for one E2E test.

    Windows runs need materially more headroom than the inner Silver Delta
    timeout because pipeline bootstrap and Bronze staging can consume tens of
    seconds before the bounded Delta write starts. The pytest timeout must stay
    above the internal Delta budget so E2E failures surface as governed storage
    errors instead of outer watchdog aborts.
    """
    if platform == "win32":
        return 420
    return 120


def _resolve_e2e_merge_execution_timeout_seconds(
    *,
    platform: str = sys.platform,
) -> int:
    """Return the platform-aware inner Silver merge timeout for E2E runs."""
    if platform == "win32":
        return 300
    return 90


def _resolve_e2e_pipeline_matrix_execution_timeout_seconds(
    *,
    platform: str = sys.platform,
    env: Mapping[str, str] = os.environ,
) -> float:
    """Return the bounded per-pipeline matrix execution timeout."""
    override = env.get("BIOETL_E2E_PIPELINE_MATRIX_EXECUTION_TIMEOUT_SECONDS")
    if override is not None:
        return float(override)
    if platform == "win32":
        return 360.0
    return 105.0


def _resolve_e2e_plain_write_process_isolation(
    *,
    platform: str = sys.platform,
) -> bool:
    """Return whether E2E should isolate plain Delta writes in a child process."""
    return platform == "win32"


def _resolve_e2e_sequential_pipeline_timeout_seconds(
    *,
    pipeline_count: int,
    platform: str = sys.platform,
) -> int:
    """Return the pytest timeout budget for tests that run pipelines sequentially.

    Each sequential run may consume bootstrap/bronze staging time plus the full
    inner Silver Delta budget. The outer pytest timeout must stay above that
    per-run envelope so Windows E2E failures surface as governed storage errors
    instead of watchdog aborts during a child-process Delta write.
    """
    if pipeline_count < 1:
        msg = "pipeline_count must be >= 1"
        raise ValueError(msg)

    default_timeout = _resolve_e2e_default_timeout(platform=platform)
    inner_merge_timeout = _resolve_e2e_merge_execution_timeout_seconds(
        platform=platform
    )
    # Bootstrap, Bronze staging, and metadata finalization can consume tens of
    # seconds before the bounded Silver write starts.
    per_pipeline_overhead_seconds = 90
    sequential_budget = pipeline_count * (
        inner_merge_timeout + per_pipeline_overhead_seconds
    )
    single_pipeline_floor = max(default_timeout, inner_merge_timeout + 30)
    return max(sequential_budget, single_pipeline_floor)


# Default timeout for E2E tests (seconds).
# E2E tests run full pipelines with HTTP calls, Delta Lake operations, and
# PyArrow imports. Keep the outer pytest budget above the inner bounded Delta
# timeout so storage failures raise deterministic domain errors before the test
# watchdog interrupts the event loop.
E2E_DEFAULT_TIMEOUT = _resolve_e2e_default_timeout()
E2E_TWO_SEQUENTIAL_PIPELINE_TIMEOUT = _resolve_e2e_sequential_pipeline_timeout_seconds(
    pipeline_count=2
)
E2E_THREE_SEQUENTIAL_PIPELINE_TIMEOUT = (
    _resolve_e2e_sequential_pipeline_timeout_seconds(pipeline_count=3)
)
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
_RETRY_EXHAUSTED_HTTP_STATUS_RE = re.compile(r"\b(429|500|502|503|504)\b")

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
_E2E_RUN_ID_NAMESPACE = UUID("f42c4f5c-1b2c-4db0-8f58-bc97f92a5f2f")
E2E_FIXED_RUN_ID = UUID("81acb12e-f7f9-4d27-9d2d-d5f541c8ee88")
E2E_FIXED_STARTED_AT = FIXED_TEST_TIME


def _clear_runtime_config_caches() -> None:
    """Clear runtime settings/config caches after environment mutations."""
    from bioetl.infrastructure.config._base import get_pipeline_config, get_settings
    from bioetl.infrastructure.config.pipeline_config_api import load_pipeline_config
    from bioetl.infrastructure.config.source_config_loader import load_source_config

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()
    load_pipeline_config.cache_clear()
    load_source_config.cache_clear()


@cache
def _get_retry_config() -> RetryConfig:
    """Build retry config lazily so collection avoids heavy domain imports."""
    from bioetl.domain.resilience import RetryConfig

    return RetryConfig(
        max_attempts=3,
        multiplier=2.0,
        base_delay=0.0,
        max_delay=0.0,
        jitter_range=(0.0, 0.0),
        retryable_statuses=_TRANSIENT_HTTP_STATUS_CODES,
        jitter_seed=20260304,
    )


@cache
def _load_delta_table() -> type[Any]:
    """Import DeltaTable lazily to keep collect-only runs lighter."""
    from deltalake import DeltaTable

    return DeltaTable


@cache
def _load_delta_record_reader() -> Callable[
    [Any, list[str] | None], list[dict[str, Any]]
]:
    """Import the shared Delta read helper lazily for E2E assertions."""
    from bioetl.infrastructure.storage.delta.table_ops import read_delta_records

    return read_delta_records


@cache
def _load_pyarrow_parquet() -> Any:
    """Import pyarrow.parquet lazily for the Windows E2E fallback reader."""
    import pyarrow.parquet as pq

    return pq


class E2EDeltaTableCorruptionError(RuntimeError):
    """Raised when the E2E harness cannot trust the local Delta log state."""


def _prefer_active_parquet_delta_reads(*, platform: str = sys.platform) -> bool:
    """Return whether E2E assertions should bypass DeltaTable Arrow scans."""
    if platform == "win32":
        return True
    if platform != "linux":
        return False
    try:
        return "microsoft" in Path("/proc/version").read_text(
            encoding="utf-8"
        ).lower()
    except OSError:
        return False


def _resolve_parquet_file_uri(file_uri: str) -> str:
    """Resolve a Delta file URI to a local path string when needed."""
    if not file_uri.startswith("file://"):
        return file_uri
    parsed_path = unquote(urlparse(file_uri).path)
    if re.match(r"^/[A-Za-z]:/", parsed_path):
        return parsed_path[1:]
    return parsed_path


def _read_active_parquet_records(
    table: Any,
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Read Delta rows from active parquet files without using Arrow dataset scans."""
    file_uris = list(table.file_uris())
    if not file_uris:
        return []

    pq = _load_pyarrow_parquet()
    tables = [
        pq.read_table(_resolve_parquet_file_uri(file_uri), columns=columns)
        for file_uri in file_uris
    ]
    if len(tables) == 1:
        return cast(list[dict[str, Any]], tables[0].to_pylist())

    import pyarrow as pa

    return cast(list[dict[str, Any]], pa.concat_tables(tables).to_pylist())


def _read_active_parquet_records_from_delta_log(
    table_path: Path,
    columns: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Read active parquet rows without invoking the native Delta scanner."""
    try:
        active_paths: dict[str, Path] = {}
        commit_paths = sorted((table_path / "_delta_log").glob("*.json"))
        if not commit_paths:
            raise ValueError("Delta log has no JSON commits")

        for commit_path in commit_paths:
            for line in commit_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                action = json.loads(line)
                add = action.get("add")
                if isinstance(add, dict) and isinstance(add.get("path"), str):
                    relative_path = unquote(add["path"])
                    active_paths[relative_path] = table_path / relative_path
                remove = action.get("remove")
                if isinstance(remove, dict) and isinstance(remove.get("path"), str):
                    active_paths.pop(unquote(remove["path"]), None)

        parquet_paths = [active_paths[key] for key in sorted(active_paths)]
        if not parquet_paths:
            return []
        pq = _load_pyarrow_parquet()
        tables = [pq.read_table(path, columns=columns) for path in parquet_paths]
        if len(tables) == 1:
            return cast(list[dict[str, Any]], tables[0].to_pylist())

        import pyarrow as pa

        return cast(list[dict[str, Any]], pa.concat_tables(tables).to_pylist())
    except (KeyboardInterrupt, SystemExit):
        raise
    except BaseException as exc:
        raise E2EDeltaTableCorruptionError(
            "E2E Delta log fallback could not read active parquet files: "
            f"path={table_path}; fallback_status=corrupt_delta_log"
        ) from exc


async def _read_delta_records(table_path: Path) -> list[dict[str, Any]]:
    """Read active Delta rows via the shared Delta scanner helper with timeout protection."""
    if _prefer_active_parquet_delta_reads():
        # The fallback only parses the local Delta JSON log and reads the
        # resulting bounded parquet files. Running it directly avoids a WSL
        # executor-completion hang observed after a full pipeline shutdown.
        return _read_active_parquet_records_from_delta_log(table_path)

    loop = asyncio.get_running_loop()

    # Use a shorter timeout for delta reads to prevent indefinite hangs
    # The default E2E timeout (120s) is for the whole test, but individual reads should be faster
    DELTA_READ_TIMEOUT = 30

    def _read_records_with_primary_strategy() -> list[dict[str, Any]]:
        table = _load_delta_table()(str(table_path))
        return _load_delta_record_reader()(table)

    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _read_records_with_primary_strategy),
            timeout=DELTA_READ_TIMEOUT,
        )
    except TimeoutError as exc:
        delta_log_present = (table_path / "_delta_log").exists()
        fallback_records = await loop.run_in_executor(
            None,
            lambda: _read_active_parquet_records_from_delta_log(table_path),
        )
        if fallback_records:
            return fallback_records

        raise TimeoutError(
            f"Delta table read timed out after {DELTA_READ_TIMEOUT}s at {table_path}. "
            "This is a bounded local Delta-read timeout, not an empty-table "
            "assertion. "
            f"delta_log_present={delta_log_present}; "
            f"prefer_active_parquet={_prefer_active_parquet_delta_reads()}. "
            "fallback_status=delta_log_parquet_empty. "
            "Higher-level E2E helpers may recover via Bronze-backed fallback."
        ) from exc


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


def _build_vcr_cassette_input_snapshot_refs(
    request: pytest.FixtureRequest,
) -> tuple[RunInputSnapshotRef, ...]:
    """Return one deterministic immutable snapshot ref derived from VCR playback."""
    from bioetl.domain.control_plane import RunInputSnapshotRef

    cassette_path = resolve_requested_cassette_path(request)
    if cassette_path is None or not cassette_path.exists():
        return ()
    if is_git_lfs_pointer(cassette_path):
        return ()

    payload = cassette_path.read_bytes()
    content_hash = hashlib.sha256(payload).hexdigest()
    snapshot_id = f"sha256:{content_hash}"
    fixtures_root = Path(__file__).resolve().parents[1]
    try:
        cassette_locator = cassette_path.relative_to(fixtures_root).as_posix()
    except ValueError:
        cassette_locator = cassette_path.as_posix()
    immutable_uri = f"vcr://{cassette_locator}"
    return (
        RunInputSnapshotRef(
            snapshot_id=snapshot_id,
            content_hash=content_hash,
            immutable_uri=immutable_uri,
        ),
    )


def _resolve_e2e_provider_cassette_dir(
    *, node_name: str, module_path: str | None
) -> str:
    """Resolve one per-test E2E cassette provider directory."""
    return infer_provider_cassette_dir(
        node_name=node_name,
        module_path=module_path,
        overrides=_E2E_VCR_CASSETTE_DIR_BY_TEST,
    )


@pytest.fixture
def vcr_cassette_dir(request: pytest.FixtureRequest) -> Path:
    """Return provider-specific cassette directory for one E2E test."""
    provider_dir = _resolve_e2e_provider_cassette_dir(
        node_name=request.node.name,
        module_path=str(request.node.fspath),
    )
    return build_cassette_dir(
        fixtures_root=Path(__file__).resolve().parents[1] / "fixtures" / "vcr",
        provider_dir=provider_dir,
    )


@pytest.fixture
def vcr_cassette_name(request: pytest.FixtureRequest) -> str:
    """Return normalized cassette file name in snake_case format."""
    return resolve_cassette_name(
        node_name=request.node.name,
        class_name=request.node.cls.__name__ if request.node.cls else None,
        overrides=_E2E_VCR_CASSETTE_NAME_OVERRIDES,
    )


@pytest.fixture(scope="session", autouse=True)
def e2e_environment():
    """Настройка окружения для E2E тестов (Local-Only)."""
    os.environ.setdefault("BIOETL_ENV", "dev")
    os.environ.setdefault("BIOETL_TEST_MODE", "true")
    os.environ.setdefault("BIOETL_PIPELINE__HEALTH_CHECK_MODE", "probe")
    os.environ.setdefault("BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PROFILE", "e2e")
    os.environ.setdefault(
        "BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__E2E_EXECUTION_TIMEOUT_SECONDS",
        str(_resolve_e2e_merge_execution_timeout_seconds()),
    )
    if _resolve_e2e_plain_write_process_isolation():
        os.environ.setdefault(
            "BIOETL_PIPELINE__SILVER_MERGE_TIMEOUT__PLAIN_WRITE_PROCESS_ISOLATION",
            "true",
        )
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

    # Mock geopandas import to prevent pandera from attempting filesystem stat
    # operations during dtype checking in concurrent threads on Windows.
    # This prevents hangs in is_geopandas_dtype() when validating schemas.
    import sys

    if "geopandas" not in sys.modules:
        sys.modules["geopandas"] = None  # type: ignore[assignment]

    # Register all pipelines (required for bootstrap_pipeline_runner to work)
    # Note: This import is session-scoped (once per E2E test session) to avoid timeout
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    _clear_runtime_config_caches()
    register_all_pipelines()

    yield

    try:
        _clear_runtime_config_caches()
    except ImportError:
        pass


@pytest.fixture(autouse=True)
def preserve_bronze_payloads_for_e2e() -> Generator[None, None, None]:
    """Keep Bronze payloads available for post-run E2E assertions.

    E2E suites validate raw Bronze artifacts after a full pipeline run. The
    production postrun path performs Bronze retention cleanup, which can delete
    the only payload before the assertion executes. Mirror the integration-test
    behavior and disable cleanup within E2E only.
    """
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

    original_cleanup = BronzeWriter.cleanup_old_files

    async def _noop_cleanup(
        self: BronzeWriter,  # pragma: no cover - exercised through pipeline runs
        cutoff_date,
        provider: str,
        entity: str,
        dry_run: bool = False,
        **kwargs: object,
    ) -> dict[str, int]:
        del self, cutoff_date, provider, entity, dry_run, kwargs
        return {"files_removed": 0, "bytes_freed": 0, "dirs_removed": 0}

    BronzeWriter.cleanup_old_files = _noop_cleanup
    try:
        yield
    finally:
        BronzeWriter.cleanup_old_files = original_cleanup


@pytest.fixture(autouse=True)
def skip_silver_compaction_for_e2e() -> Generator[None, None, None]:
    """Skip postrun Silver compaction in E2E to avoid Delta maintenance hangs.

    E2E scenarios validate end-to-end extraction and persisted artifacts, not
    retention/maintenance behavior. On Windows, delta-rs deduplication may keep
    a background executor thread alive after timeout, which can block the next
    test assertion when it opens the same Silver table. Keep maintenance
    coverage in its dedicated unit/integration suites and make E2E deterministic.
    """
    from bioetl.application.core.postrun.compact_orchestrator import (
        CompactionResult,
        PostrunCompactService,
    )

    original_run_if_needed = PostrunCompactService.run_if_needed

    async def _skip_compaction(
        self: PostrunCompactService,  # pragma: no cover - exercised through E2E runs
    ) -> CompactionResult:
        self._logger.info("silver_compact_skipped_in_e2e")
        return CompactionResult(status="skipped")

    PostrunCompactService.run_if_needed = _skip_compaction
    try:
        yield
    finally:
        PostrunCompactService.run_if_needed = original_run_if_needed


@pytest.fixture
def relaxed_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Enable relaxed DQ thresholds explicitly for replay-heavy E2E tests."""
    del monkeypatch  # fixture signature retained for compatibility
    _ = (
        os.environ.get("BIOETL_TEST_RELAXED_DQ"),
        os.environ.get("BIOETL_PIPELINE__RELAXED_DQ"),
    )
    with relaxed_dq_environment():
        yield


@contextmanager
def relaxed_dq_environment() -> Generator[None, None, None]:
    """Temporarily force relaxed DQ mode across arbitrary fixture scopes."""
    previous_test_relaxed = os.environ.get("BIOETL_TEST_RELAXED_DQ")
    previous_pipeline_relaxed = os.environ.get("BIOETL_PIPELINE__RELAXED_DQ")

    _clear_runtime_config_caches()
    os.environ["BIOETL_TEST_RELAXED_DQ"] = "1"
    os.environ["BIOETL_PIPELINE__RELAXED_DQ"] = "1"
    _clear_runtime_config_caches()
    try:
        yield
    finally:
        if previous_test_relaxed is None:
            os.environ.pop("BIOETL_TEST_RELAXED_DQ", None)
        else:
            os.environ["BIOETL_TEST_RELAXED_DQ"] = previous_test_relaxed
        if previous_pipeline_relaxed is None:
            os.environ.pop("BIOETL_PIPELINE__RELAXED_DQ", None)
        else:
            os.environ["BIOETL_PIPELINE__RELAXED_DQ"] = previous_pipeline_relaxed
        _clear_runtime_config_caches()


@pytest.fixture
def strict_dq_env(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Force strict DQ mode for E2E tests that validate helper/policy behavior."""
    _clear_runtime_config_caches()
    monkeypatch.delenv("BIOETL_TEST_RELAXED_DQ", raising=False)
    monkeypatch.setenv("BIOETL_PIPELINE__RELAXED_DQ", "0")
    _clear_runtime_config_caches()
    yield
    _clear_runtime_config_caches()


@contextmanager
def managed_e2e_data_dir(data_dir: Path) -> Generator[Path, None, None]:
    """Configure one temporary BIOETL_DATA_DIR with cache-safe lifecycle.

    Supports both function-scoped and module-scoped test setups so expensive
    E2E suites can share one data directory when they intentionally reuse the
    same pipeline run output across multiple assertions.
    """
    from bioetl.infrastructure.config._base import (
        get_pipeline_config,
        get_settings,
    )

    data_dir.mkdir(parents=True, exist_ok=True)

    # Create Medallion subdirectories
    for subdir in ("bronze", "silver", "gold", "checkpoints", "quarantine", "output"):
        (data_dir / subdir).mkdir(exist_ok=True)
    for subdir in ("bronze", "silver", "gold"):
        (data_dir / "output" / subdir).mkdir(parents=True, exist_ok=True)

    previous_data_dir = os.environ.get("BIOETL_DATA_DIR")
    previous_required_profile = os.environ.get(
        "BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE"
    )
    os.environ["BIOETL_DATA_DIR"] = str(data_dir)
    os.environ["BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE"] = (
        "degraded_observable"
    )

    get_settings.cache_clear()
    get_pipeline_config.cache_clear()

    try:
        # StoragePathSettingsMixin derives the medallion paths from data_dir;
        # BIOETL_DATA_DIR therefore provides the required output/* isolation.
        yield data_dir
    finally:
        if previous_data_dir is None:
            os.environ.pop("BIOETL_DATA_DIR", None)
        else:
            os.environ["BIOETL_DATA_DIR"] = previous_data_dir
        if previous_required_profile is None:
            os.environ.pop(
                "BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE",
                None,
            )
        else:
            os.environ[
                "BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE"
            ] = previous_required_profile
        get_settings.cache_clear()
        get_pipeline_config.cache_clear()


def clone_e2e_data_dir_snapshot(snapshot_dir: Path, target_dir: Path) -> None:
    """Clone prepared E2E data into a fresh temp directory for isolated reuse."""
    shutil.copytree(snapshot_dir, target_dir)


def _resolve_e2e_temp_root(
    *,
    platform: str = sys.platform,
    posix_tmp: Path = Path("/tmp"),
    fallback_tmp: str | None = None,
    env: Mapping[str, str] = os.environ,
) -> Path:
    """Resolve a fast local temp root for E2E sandboxes.

    On Windows, ``tempfile.gettempdir()`` can resolve to a user-customized
    ``TEMP/TMP`` directory on a mounted or cloud-synced drive. Delta Lake writes
    become materially slower there, so prefer an explicit local-app-data temp
    root when available unless the operator set an explicit override.
    """
    fallback = Path(fallback_tmp or tempfile.gettempdir())
    if platform == "win32":
        override = env.get("BIOETL_E2E_TEMP_ROOT")
        if override:
            return Path(override).expanduser()

        local_appdata = env.get("LOCALAPPDATA")
        if local_appdata:
            local_temp = Path(local_appdata) / "Temp"
            if local_temp.exists():
                return local_temp
        return fallback
    if posix_tmp.exists():
        return posix_tmp
    return fallback


@pytest.fixture
def e2e_data_dir(tmp_path: Path, monkeypatch) -> Generator[Path, None, None]:
    """Создание временной директории данных с настройкой окружения.

    Предпочитает локальный temp-root, чтобы Delta Lake не упирался в mounted
    pytest tmp-path на Windows/network storage.
    """
    del tmp_path  # mounted pytest temp may point to a slow Windows/network drive
    del monkeypatch  # kept for backward-compatible fixture signature

    temp_root = _resolve_e2e_temp_root()
    sandbox_dir = Path(tempfile.mkdtemp(prefix="bioetl-e2e-", dir=str(temp_root)))
    data_dir = sandbox_dir / "bioetl_data"
    try:
        with managed_e2e_data_dir(data_dir) as prepared_dir:
            yield prepared_dir
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


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
    """Create an occurrence-safe E2E context for one pipeline run."""
    return build_e2e_run_context(
        pipeline_name=pipeline_name,
        limit=limit,
        run_type=run_type,
        resume=resume,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    )


def create_deterministic_test_context(
    pipeline_name: str,
    limit: int | None = 10,
    run_type: RunType | None = None,
    resume: bool = False,
    query: str | None = None,
    filter_ids: tuple[str, ...] | None = None,
    filter_field: str | None = None,
) -> PipelineRunContext:
    """Create a stable E2E context for replay/control-plane identity assertions."""
    return build_e2e_run_context(
        pipeline_name=pipeline_name,
        limit=limit,
        run_type=run_type,
        resume=resume,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
        run_id_seed=str(E2E_FIXED_RUN_ID),
    )


def _build_e2e_run_id(seed: str) -> UUID:
    """Return deterministic UUID for E2E contexts and retries."""
    return uuid5(_E2E_RUN_ID_NAMESPACE, seed)


def _build_e2e_context_seed(
    *,
    pipeline_name: str,
    run_type: str,
    limit: int | None,
    resume: bool,
    query: str | None,
    filter_ids: tuple[str, ...] | None,
    filter_field: str | None,
) -> str:
    """Serialize E2E context inputs into a stable seed string."""
    normalized_filter_ids = ",".join(filter_ids or ())
    return (
        f"pipeline={pipeline_name}|run_type={run_type}|limit={limit}|resume={resume}|"
        f"query={query or ''}|filter_field={filter_field or ''}|filter_ids={normalized_filter_ids}"
    )


def _resolve_e2e_run_id(
    *,
    run_id_seed: str | None,
    pipeline_name: str,
    run_type: str,
    limit: int | None,
    resume: bool,
    query: str | None,
    filter_ids: tuple[str, ...] | None,
    filter_field: str | None,
) -> UUID:
    """Return explicit deterministic IDs only when a test opts into a seed."""
    if run_id_seed is not None:
        seed = _build_e2e_context_seed(
            pipeline_name=pipeline_name,
            run_type=run_type,
            limit=limit,
            resume=resume,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        return _build_e2e_run_id(f"{run_id_seed}|{seed}")
    return deterministic_uuid_from_callsite("e2e.conftest")


def build_e2e_run_context(
    pipeline_name: str,
    limit: int | None = 10,
    run_type: RunType | None = None,
    resume: bool = False,
    query: str | None = None,
    filter_ids: tuple[str, ...] | None = None,
    filter_field: str | None = None,
    run_id_seed: str | None = None,
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
    from bioetl.domain.types import RunID, RunType

    if filter_ids is not None and filter_field is not None:
        input_filter = InputFilterContext.from_ids(filter_ids, filter_field)
    else:
        input_filter = InputFilterContext.disabled()

    resolved_run_type = run_type or RunType.INCREMENTAL
    run_id = _resolve_e2e_run_id(
        run_id_seed=run_id_seed,
        pipeline_name=pipeline_name,
        run_type=resolved_run_type.value,
        limit=limit,
        resume=resume,
        query=query,
        filter_ids=filter_ids,
        filter_field=filter_field,
    )
    return PipelineRunContext(
        pipeline_name=pipeline_name,
        run_id=RunID(run_id),
        run_type=resolved_run_type,
        started_at=E2E_FIXED_STARTED_AT,
        resume=resume,
        limit=limit,
        query=query,
        input_filter=input_filter,
    )


def build_e2e_replay_context(
    context: PipelineRunContext,
    *,
    replay_of_run_id: str | None = None,
    replay_of_manifest_id: str | None = None,
) -> PipelineRunContext:
    """Return deterministic replay context linked to a parent run/manifest."""
    from bioetl.domain.context import PipelineRunContext
    from bioetl.domain.types import RunID

    parent_run_id = replay_of_run_id or str(context.run_id)
    replay_seed = (
        f"replay|pipeline={context.pipeline_name}|parent_run_id={parent_run_id}|"
        f"parent_manifest_id={replay_of_manifest_id or ''}|limit={context.limit}|"
        f"resume={context.resume}|query={context.query or ''}"
    )
    return cast(
        PipelineRunContext,
        replace(
            context,
            run_id=RunID(_build_e2e_run_id(replay_seed)),
            started_at=E2E_FIXED_STARTED_AT,
            replay_of_run_id=parent_run_id,
            replay_of_manifest_id=replay_of_manifest_id,
        ),
    )


def _is_transient_external_error(exc: ExternalServiceError) -> bool:
    """Return True when ExternalServiceError is likely upstream/transient."""
    if exc.status_code in _TRANSIENT_HTTP_STATUS_CODES:
        return True
    message = str(exc).lower()
    return any(marker in message for marker in _TRANSIENT_EXTERNAL_ERROR_MARKERS)


def _iter_exception_chain(exc: Exception | BaseException | None) -> list[BaseException]:
    """Return a bounded chain of cause/context exceptions for deep inspection."""
    from bioetl.domain.exceptions.network import RetryExhaustedError

    if exc is None:
        return []

    chain: list[BaseException] = []
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None:
        identity = id(current)
        if identity in seen:
            break
        seen.add(identity)
        chain.append(current)

        if isinstance(current, RetryExhaustedError) and current.last_error is not None:
            current = current.last_error
            continue

        next_exc = current.__cause__ or current.__context__
        if next_exc is current:
            break
        current = next_exc

    return chain


def _contains_transient_marker(message: str) -> bool:
    """Return True if error text looks like transient transport upstream."""
    lowered = str(message).lower()
    return any(marker in lowered for marker in _TRANSIENT_EXTERNAL_ERROR_MARKERS)


def _is_transient_upstream_error(exc: BaseException | None) -> bool:
    """Return True if any exception in chain indicates a transient upstream failure."""
    import httpx
    from bioetl.domain.exceptions.network import ExternalServiceError

    for candidate in _iter_exception_chain(exc):
        if isinstance(candidate, ExternalServiceError):
            if _is_transient_external_error(candidate):
                return True
            continue
        if isinstance(candidate, httpx.HTTPStatusError):
            if _is_transient_http_status_error(candidate):
                return True
            continue
        if _contains_transient_marker(str(candidate)):
            return True
    return False


def _is_transient_http_status_error(exc: httpx.HTTPStatusError) -> bool:
    """Return True when HTTPStatusError is likely upstream/transient."""
    return exc.response.status_code in _TRANSIENT_HTTP_STATUS_CODES


def _is_transient_retry_exhausted_error(exc: Exception) -> bool:
    """Return True when a terminal retry wrapper still points to transient upstream."""
    from bioetl.domain.exceptions.network import RetryExhaustedError

    if not isinstance(exc, RetryExhaustedError):
        return False
    if _is_transient_upstream_error(exc):
        return True
    if _RETRY_EXHAUSTED_HTTP_STATUS_RE.search(str(exc)) is not None:
        return True
    if exc.last_error is not None:
        return _RETRY_EXHAUSTED_HTTP_STATUS_RE.search(str(exc.last_error)) is not None
    return False


def is_external_healthcheck_playback_failure(exc: Exception) -> bool:
    """Return True when playback fails due to external health-check mismatch."""
    from bioetl.domain.exceptions.infrastructure import InfrastructureError

    if not isinstance(exc, InfrastructureError):
        return False
    message = str(exc).lower()
    return any(
        marker in message for marker in _E2E_HEALTHCHECK_PLAYBACK_FAILURE_MARKERS
    )


def is_strict_persistence_snapshot_gap(exc: Exception) -> bool:
    """Return True when strict persistence fails closed on missing snapshots."""
    if not isinstance(exc, RuntimeError):
        return False
    message = " ".join(str(exc).lower().split())
    if "immutable input snapshots" not in message:
        return False
    return any(
        marker in message
        for marker in (
            "strict persistence profiles require immutable input snapshots",
            "cannot satisfy required persistence profile",
            "no snapshot-backed source refs were resolved",
        )
    )


def _skip_strict_persistence_snapshot_gap(
    context: PipelineRunContext,
    exc: Exception,
) -> None:
    """Skip one E2E run when cassette playback cannot satisfy strict replay policy."""
    pytest.skip(
        build_e2e_skip_reason(
            "PERSISTENCE_SNAPSHOT_GAP",
            pipeline_name=context.pipeline_name,
            detail=(f"strict snapshot policy blocked cassette-backed playback: {exc}"),
        )
    )


def wrap_bootstrap_pipeline_runner_for_e2e(
    bootstrap_fn: Callable[..., Any],
) -> Callable[..., Any]:
    """Guard one bootstrap entrypoint with deterministic strict-policy skips."""

    def _wrapped(context: PipelineRunContext, *args: object, **kwargs: object) -> Any:
        try:
            return bootstrap_fn(context, *args, **kwargs)
        except RuntimeError as exc:
            if is_strict_persistence_snapshot_gap(exc):
                _skip_strict_persistence_snapshot_gap(context, exc)
            raise

    return _wrapped


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
    retry_seed = f"retry|pipeline={context.pipeline_name}|run_id={context.run_id}|attempt={attempt}"
    return cast(
        PipelineRunContext,
        replace(
            context,
            run_id=RunID(_build_e2e_run_id(retry_seed)),
            started_at=FIXED_TEST_TIME,
        ),
    )


def _get_transient_reason_code(exc: Exception | None) -> str:
    """Map transient exception to deterministic CI skip code."""
    import httpx
    from bioetl.domain.exceptions.network import (
        ExternalServiceError,
        RetryExhaustedError,
    )

    if isinstance(exc, ExternalServiceError) and exc.status_code == 429:
        return "INFRA_FLAKY_429"
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429:
        return "INFRA_FLAKY_429"
    if isinstance(exc, RetryExhaustedError):
        last_error = exc.last_error
        if _get_transient_reason_code(last_error) == "INFRA_FLAKY_429":
            return "INFRA_FLAKY_429"
        if _RETRY_EXHAUSTED_HTTP_STATUS_RE.search(str(last_error or exc)) is not None:
            if "429" in str(last_error or exc):
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


@pytest.fixture(autouse=True)
def guard_bootstrap_pipeline_runner_for_e2e(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    """Patch direct bootstrap imports so legacy E2E modules honor policy skips."""
    import bioetl.composition.bootstrap as bootstrap_package
    from bioetl.composition.bootstrap.runtime import pipeline as runtime_pipeline
    from bioetl.composition.runtime_builders import (
        input_snapshot_resolution,
        run_manifest_support,
    )

    # Register before monkeypatch so teardown runs after monkeypatch undo (LIFO).
    request.addfinalizer(
        lambda: bootstrap_package.__dict__.pop("bootstrap_pipeline_runner", None)
    )

    guarded_bootstrap = wrap_bootstrap_pipeline_runner_for_e2e(
        runtime_pipeline.bootstrap_pipeline_runner
    )
    monkeypatch.setattr(
        runtime_pipeline,
        "bootstrap_pipeline_runner",
        guarded_bootstrap,
    )
    monkeypatch.setattr(
        bootstrap_package,
        "bootstrap_pipeline_runner",
        guarded_bootstrap,
    )

    module = getattr(request.node, "module", None)
    if module is not None and hasattr(module, "bootstrap_pipeline_runner"):
        monkeypatch.setattr(module, "bootstrap_pipeline_runner", guarded_bootstrap)

    original_resolve_input_snapshots = (
        run_manifest_support.resolve_pipeline_input_snapshot_refs
    )
    has_vcr_marker = request.node.get_closest_marker("vcr") is not None
    fallback_snapshot_refs = (
        () if not has_vcr_marker else _build_vcr_cassette_input_snapshot_refs(request)
    )

    def _resolve_pipeline_input_snapshot_refs_with_vcr_fallback(**kwargs: object):
        refs = original_resolve_input_snapshots(**kwargs)
        if refs:
            return refs
        if not has_vcr_marker:
            return refs
        return fallback_snapshot_refs

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.run_manifest_support.resolve_pipeline_input_snapshot_refs",
        _resolve_pipeline_input_snapshot_refs_with_vcr_fallback,
    )
    monkeypatch.setattr(
        input_snapshot_resolution,
        "resolve_pipeline_input_snapshot_refs",
        _resolve_pipeline_input_snapshot_refs_with_vcr_fallback,
    )

    yield


async def run_pipeline_or_skip_transient(context: PipelineRunContext) -> Any:
    """Run pipeline with deterministic retries; skip on transient exhaustion."""
    import httpx
    from bioetl.domain.exceptions.network import (
        ExternalServiceError,
        RetryExhaustedError,
    )

    from bioetl.composition.bootstrap import bootstrap_pipeline_runner

    retry_config = _get_retry_config()
    transient_exc: Exception | None = None
    for attempt in range(retry_config.max_attempts):
        run_context = _create_retry_run_context(context, attempt)
        try:
            runner = bootstrap_pipeline_runner(run_context)
            await runner.run()
            return runner
        except RuntimeError as exc:
            if is_strict_persistence_snapshot_gap(exc):
                _skip_strict_persistence_snapshot_gap(run_context, exc)
            raise
        except ExternalServiceError as exc:
            if not _is_transient_external_error(exc):
                raise
            transient_exc = exc
        except RetryExhaustedError as exc:
            if not _is_transient_retry_exhausted_error(exc):
                raise
            # Inner HTTP/client retries already spent the transient retry budget.
            # Re-running the full pipeline here only burns more wall-clock time.
            _skip_transient_pipeline_run(context, exc)
        except httpx.HTTPStatusError as exc:
            if not _is_transient_http_status_error(exc):
                raise
            transient_exc = exc

        if retry_config.is_last_attempt(attempt):
            _skip_transient_pipeline_run(context, transient_exc)

        delay = retry_config.calculate_delay(attempt, url=context.pipeline_name)
        assert delay == 0.0, "E2E retry helper must not add wall-clock sleeps"
        await asyncio.sleep(0)

    msg = "run_pipeline_or_skip_transient exhausted without terminal decision"
    raise RuntimeError(msg)


# ============================================================================
# Assertion Helpers
# ============================================================================


def _bronze_candidate_roots(data_dir: Path) -> tuple[Path, ...]:
    return (
        data_dir / "output" / "bronze",
        data_dir / "bronze",
    )


def _bronze_search_paths(data_dir: Path, provider: str, entity: str) -> list[Path]:
    paths: list[Path] = []
    for root in _bronze_candidate_roots(data_dir):
        paths.append(root / provider / entity)
        paths.append(root)
    return paths


def _find_bronze_payload_files(root: Path) -> list[Path]:
    files = list(root.rglob("*.jsonl.zst"))
    if files:
        return files
    return list(root.rglob("*.jsonl"))


def _find_bronze_metadata_files(root: Path) -> list[Path]:
    return list(root.rglob("*_metadata.yaml"))


def _find_bronze_artifacts(
    *,
    data_dir: Path,
    provider: str,
    entity: str,
    finder: Callable[[Path], list[Path]],
) -> list[Path]:
    for root in _bronze_candidate_roots(data_dir):
        standard_path = root / provider / entity
        if standard_path.exists():
            files = finder(standard_path)
            if files:
                return files

        if root.exists():
            files = finder(root)
            if files:
                return files
    return []


def assert_bronze_payload_files_exist(
    data_dir: Path,
    provider: str,
    entity: str,
) -> list[Path]:
    """Assert immutable raw Bronze payload files were materialized.

    Args:
        data_dir: Корневая директория данных
        provider: Имя провайдера (chembl, pubchem, etc.)
        entity: Тип сущности (activity, molecule, etc.)

    Returns:
        Список найденных Bronze-артефактов

    Raises:
        AssertionError: Если файлы не найдены

    Note:
        Handles both standard and flat_structure layouts. Metadata sidecars are
        intentionally not accepted as raw Bronze payload evidence.
    """
    files = _find_bronze_artifacts(
        data_dir=data_dir,
        provider=provider,
        entity=entity,
        finder=_find_bronze_payload_files,
    )
    if files:
        return files

    checked_payload_paths = "\n".join(
        f"  - {path}" for path in _bronze_search_paths(data_dir, provider, entity)
    )
    checked_metadata_paths = "\n".join(
        f"  - {path}" for path in _bronze_search_paths(data_dir, provider, entity)
    )
    raise AssertionError(
        "No raw Bronze payload files found (*.jsonl.zst or *.jsonl).\n"
        f"Checked payload paths:\n{checked_payload_paths}\n"
        "Metadata sidecars are not accepted as payload evidence.\n"
        f"Metadata search paths, for separate assertion only:\n{checked_metadata_paths}"
    )


def assert_bronze_metadata_files_exist(
    data_dir: Path,
    provider: str,
    entity: str,
) -> list[Path]:
    """Assert Bronze metadata sidecars were materialized."""
    files = _find_bronze_artifacts(
        data_dir=data_dir,
        provider=provider,
        entity=entity,
        finder=_find_bronze_metadata_files,
    )
    if files:
        return files

    checked = "\n".join(
        f"  - {path}" for path in _bronze_search_paths(data_dir, provider, entity)
    )
    raise AssertionError(
        f"No Bronze metadata sidecars found. Checked paths:\n{checked}"
    )


def assert_bronze_files_exist(data_dir: Path, provider: str, entity: str) -> list[Path]:
    """Compatibility wrapper for raw Bronze payload assertions."""
    return assert_bronze_payload_files_exist(data_dir, provider, entity)


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
    variants = _build_table_name_variants(table_name)
    silver_bases = [
        data_dir / "output" / "silver",
        data_dir / "silver",
    ]

    for silver_base in silver_bases:
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

    checked = [
        str(silver_base / variant.replace(".", "/"))
        for silver_base in silver_bases
        for variant in variants
    ]
    raise AssertionError(
        "Silver table does not exist. "
        f"table_name={table_name}, checked={checked}, "
        f"flat={', '.join(str(base) for base in silver_bases)}"
    )


async def assert_silver_table_has_records(
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
        Handles both current layout
        (data_dir/output/silver/{table_name}/) and legacy root layout
        (data_dir/silver/{table_name}/), plus flat_structure tables at either
        silver layer root for pipelines with flat_structure: true in config.
    """
    table_path = _resolve_silver_table_path(data_dir, table_name)

    count = len(await _read_delta_records(table_path))

    if count < expected_min:
        raise AssertionError(
            f"Silver table {table_name} has {count} records, expected >= {expected_min}"
        )

    return count


async def assert_gold_table_has_records(
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
        Handles both current output-root layout and legacy root layout, plus
        flat_structure tables at either gold layer root.
    """
    gold_bases = [
        data_dir / "output" / "gold",
        data_dir / "gold",
    ]
    table_path: Path | None = None

    for gold_base in gold_bases:
        standard_path = gold_base / table_name
        flat_path = gold_base
        if standard_path.exists():
            table_path = standard_path
            break
        if flat_path.exists() and (flat_path / "_delta_log").exists():
            table_path = flat_path
            break

    if table_path is None:
        checked = [str(gold_base / table_name) for gold_base in gold_bases]
        raise AssertionError(
            "Gold table does not exist: "
            f"table_name={table_name}, checked={checked}, "
            f"flat={', '.join(str(base) for base in gold_bases)}"
        )

    count = len(await _read_delta_records(table_path))

    if count < expected_min:
        raise AssertionError(
            f"Gold table {table_name} has {count} records, expected >= {expected_min}"
        )

    return count


async def get_silver_records(data_dir: Path, table_name: str) -> list[dict]:
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

    records = await _read_delta_records(table_path)

    # Validate that records are dictionaries
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Expected record at index {i} to be a dict, got {type(record).__name__}. "
                f"Table: {table_name}, Record: {record}"
            )

    return records


async def get_gold_records(data_dir: Path, table_name: str) -> list[dict]:
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

    records = await _read_delta_records(table_path)

    # Validate that records are dictionaries
    for i, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"Expected record at index {i} to be a dict, got {type(record).__name__}. "
                f"Gold table: {table_name}, Record: {record}"
            )

    return records
