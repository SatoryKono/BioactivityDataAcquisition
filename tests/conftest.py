import asyncio
import contextlib
import enum
import gc
import inspect
import os
import pathlib
import random
import sys
import threading
import traceback
from collections.abc import Callable, Generator
from functools import cache
from importlib.metadata import PackageNotFoundError, version
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
import yaml
from tests.helpers.vcr_config import (
    build_cassette_dir,
    build_base_vcr_config,
    ensure_default_vcr_record_mode,
    infer_provider_cassette_dir,
    is_vcr_recording_mode,
    is_git_lfs_pointer,
    is_strict_lfs_pointer_blocked_cassette,
    query_ignore_email,
    resolve_requested_cassette_path,
)

_ORIGINAL_OS_NAME = os.name
_ORIGINAL_SYS_PLATFORM = sys.platform
_ORIGINAL_PATH = pathlib.Path
_ASYNC_TIMEOUT_DIAGNOSTIC_MARGIN_SECONDS = 5.0
_DISABLED_ENV_VALUES = frozenset({"0", "false", "no", "off"})
_WINDOWS_XDIST_WORKER_CAP_ENV = "BIOETL_PYTEST_WINDOWS_XDIST_WORKERS"
_DEFAULT_WINDOWS_XDIST_WORKER_CAP = 1
_WINDOWS_PYCHARM_VCR_TIMEOUT_SECONDS = 180
_RUNTIME_BOOTSTRAP_PIPELINE_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "bioetl"
    / "composition"
    / "bootstrap"
    / "runtime"
    / "pipeline.py"
)
_TEST_MATRIX_PATH = (
    Path(__file__).resolve().parents[1] / "configs/quality/test_matrix.yaml"
)


@cache
def _filesystem_contract_modules() -> frozenset[str]:
    """Load explicitly reviewed filesystem-contract module ownership."""
    payload = yaml.safe_load(_TEST_MATRIX_PATH.read_text(encoding="utf-8"))
    modules = payload["test_lanes"]["lanes"]["unit-filesystem-contracts"][
        "classified_modules"
    ]
    return frozenset(str(module).replace("\\", "/") for module in modules)


def _disable_unused_geopandas_backend_on_windows() -> None:
    """Prevent Pandera from probing an unused backend on Windows test lanes."""
    # Pandera probes its optional GeoPandas backend during every dtype check.
    # Resolving it from a cloud-synced virtualenv can trip the per-test timeout.
    if sys.platform.startswith("win") and "geopandas" not in sys.modules:
        sys.modules["geopandas"] = cast(ModuleType, cast(object, None))


_disable_unused_geopandas_backend_on_windows()


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Apply governed lane markers and optional deterministic randomization."""
    fs_contract_modules = _filesystem_contract_modules()
    for item in items:
        module_path = Path(str(item.path)).resolve()
        try:
            relative_path = module_path.relative_to(_TEST_MATRIX_PATH.parents[2])
        except ValueError:
            continue
        if relative_path.as_posix() in fs_contract_modules:
            item.add_marker(pytest.mark.fs_contract)

    raw_seed = os.environ.get("BIOETL_RANDOM_ORDER_SEED")
    if raw_seed is None:
        return
    seed = int(raw_seed)
    random.Random(seed).shuffle(items)


def _async_timeout_diagnostics_enabled() -> bool:
    """Return whether async timeout diagnostics should run for this pytest process."""
    configured = os.environ.get("BIOETL_ASYNC_TEST_TIMEOUT_DIAGNOSTICS")
    if configured is not None:
        return configured.strip().lower() not in _DISABLED_ENV_VALUES
    return sys.platform.startswith("win") and _is_pycharm_pytest_runner()


def _is_async_test_item(item: pytest.Item) -> bool:
    """Return True when pytest will execute the item through an asyncio loop."""
    test_object = getattr(item, "obj", None)
    return inspect.iscoroutinefunction(test_object) or (
        item.get_closest_marker("asyncio") is not None
    )


def _coerce_timeout_seconds(raw_value: object) -> float | None:
    """Convert pytest-timeout marker/config values to seconds."""
    if raw_value in (None, ""):
        return None
    try:
        timeout_seconds = float(str(raw_value))
    except (TypeError, ValueError):
        return None
    return timeout_seconds if timeout_seconds > 0 else None


def _timeout_seconds_for_item(item: pytest.Item) -> float | None:
    """Resolve the effective pytest-timeout budget for one item."""
    timeout_marker = item.get_closest_marker("timeout")
    if timeout_marker is not None:
        marker_value = (
            timeout_marker.args[0]
            if timeout_marker.args
            else timeout_marker.kwargs.get("timeout")
        )
        marker_timeout = _coerce_timeout_seconds(marker_value)
        if marker_timeout is not None:
            return marker_timeout
        if marker_value in {0, "0"}:
            return None

    option_timeout = _coerce_timeout_seconds(
        getattr(getattr(item.config, "option", None), "timeout", None)
    )
    if option_timeout is not None:
        return option_timeout

    try:
        return _coerce_timeout_seconds(item.config.getini("timeout"))
    except (ValueError, TypeError):
        return None


def _format_async_task_stack(task: asyncio.Task[object]) -> list[str]:
    """Return a compact stack dump for one pending asyncio task."""
    lines = [
        f"  task={task.get_name()!r} state={getattr(task, '_state', 'unknown')!r} "
        f"coro={task.get_coro()!r}"
    ]
    stack = task.get_stack(limit=12)
    if not stack:
        lines.append("    <no Python stack available>")
        return lines

    for frame in stack:
        formatted = traceback.format_stack(frame, limit=1)
        lines.extend(f"    {line.rstrip()}" for line in formatted)
    return lines


def _dump_async_timeout_diagnostics(nodeid: str, timeout_seconds: float) -> None:
    """Print pending asyncio task stacks before pytest-timeout aborts the test."""
    pending_tasks = [
        task
        for task in gc.get_objects()
        if isinstance(task, asyncio.Task) and not task.done()
    ]
    sys.stderr.write(
        "\n[BIOETL_ASYNC_TIMEOUT_DIAGNOSTIC] "
        f"nodeid={nodeid} timeout_seconds={timeout_seconds:g} "
        f"pending_tasks={len(pending_tasks)}\n"
    )
    sys.stderr.flush()
    for task in pending_tasks:
        for line in _format_async_task_stack(task):
            sys.stderr.write(f"{line}\n")
            sys.stderr.flush()


def _start_async_timeout_diagnostics(item: pytest.Item) -> threading.Event | None:
    """Start a watchdog that dumps asyncio task stacks shortly before timeout."""
    if not _async_timeout_diagnostics_enabled() or not _is_async_test_item(item):
        return None
    timeout_seconds = _timeout_seconds_for_item(item)
    if timeout_seconds is None:
        return None

    delay = timeout_seconds - _ASYNC_TIMEOUT_DIAGNOSTIC_MARGIN_SECONDS
    if delay <= 0:
        return None

    stop_event = threading.Event()

    def _watchdog() -> None:
        if stop_event.wait(delay):
            return
        _dump_async_timeout_diagnostics(item.nodeid, timeout_seconds)

    thread = threading.Thread(
        target=_watchdog,
        name="bioetl-async-timeout-diagnostics",
        daemon=True,
    )
    thread.start()
    return stop_event


@pytest.fixture(autouse=True)
def _guard_global_pathlib_state() -> Generator[None, None, None]:
    """Автоматически восстанавливает глобальное состояние pathlib и OS после грязных тестов."""
    yield
    if os.name != _ORIGINAL_OS_NAME:
        os.name = _ORIGINAL_OS_NAME
    if sys.platform != _ORIGINAL_SYS_PLATFORM:
        sys.platform = _ORIGINAL_SYS_PLATFORM
    if pathlib.Path is not _ORIGINAL_PATH:
        pathlib.Path = _ORIGINAL_PATH


@pytest.fixture(autouse=True)
def _restore_runtime_bootstrap_pipeline_after_repo_backed_tests(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Keep repo-backed tests from leaking source-file mutations across the suite."""
    if request.node.get_closest_marker("repo_backed") is None:
        yield
        return

    path = _RUNTIME_BOOTSTRAP_PIPELINE_PATH
    try:
        original = path.read_text(encoding="utf-8")
    except OSError:
        yield
        return

    yield

    try:
        current = path.read_text(encoding="utf-8")
    except OSError:
        return
    if current != original:
        path.write_text(original, encoding="utf-8")


# Keep root conftest importable even when optional/shared fixture modules drift.
# `metadata_fixtures` currently depends on storage modules that are absent in this
# checkout, so loading it eagerly would break unrelated suites at startup.
pytest_plugins = ("tests.integration.chembl.extraction_params_support",)


def _pytest_option_names(option: object) -> tuple[str, ...]:
    """Return option spellings across callable and iterable pytest APIs."""
    names: object = getattr(option, "names", ())
    if callable(names):
        names = names()
    if isinstance(names, str):
        return (names,)
    if isinstance(names, (list, tuple)):
        return tuple(str(item) for item in names)
    return ()


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register global test options."""
    parser.addoption(
        "--network",
        action="store_true",
        default=False,
        help="Enable tests that require outbound network connectivity.",
    )
    parser.addoption(
        "--live-api",
        action="store_true",
        default=False,
        help="Enable live API contract tests (equivalent to BIOETL_LIVE_API_TESTS=true).",
    )
    parser.addoption(
        "--pilot-soak",
        action="store_true",
        default=False,
        help="Enable richer pilot-only live contract suites (equivalent to BIOETL_PILOT_SOAK_TESTS=true).",
    )
    # Workflows may pass --vcr-record=... Prefer VCR_RECORD_MODE when possible.
    # Skip registration when pytest-vcr (or another plugin) already owns the flag.
    if find_spec("pytest_vcr") is None:
        with contextlib.suppress(ValueError):
            parser.addoption(
                "--vcr-record",
                action="store",
                default=None,
                help=(
                    "VCR record mode compatibility option "
                    "(none|once|new_episodes|all). Prefer VCR_RECORD_MODE env."
                ),
            )


def pytest_cmdline_main(config):
    # Workaround for xdist serialization error with enum-valued options
    # (historically syrupy's diff_mode). Avoid scanning every option attribute
    # because collection startup cost compounds across large suites.
    if hasattr(config, "option"):
        _normalize_enum_option(config.option, "diff_mode")


def pytest_configure(config):
    # Keep it here as well just in case
    _normalize_enum_option(config.option, "diff_mode")
    _reset_last_failed_collection_state(config)
    _auto_enable_benchmark_selection_for_explicit_benchmark_runs(config)
    _configure_windows_xdist(config)
    _configure_windows_asyncio(config)
    _configure_windows_pycharm_traceback_style(config)
    _configure_wsl_timeout(config)
    _configure_windows_local_basetemp(config)
    _configure_windows_test_mode_for_control_plane_durability()
    _configure_isolated_run_report_root(config)
    if _selected_paths_need_hypothesis(config):
        _configure_hypothesis_profiles()


def pytest_itemcollected(item: pytest.Item) -> None:
    """Track pre-deselection collection volume for `--last-failed` runs."""
    config = item.config
    config.__dict__["_bioetl_last_failed_collected_count"] = (
        _last_failed_collected_count(config) + 1
    )
    _extend_windows_pycharm_vcr_timeout(item)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    """Attach async task diagnostics before pytest-timeout interrupts a test."""
    timeout_diagnostic_stop = _start_async_timeout_diagnostics(item)
    try:
        yield
    finally:
        if timeout_diagnostic_stop is not None:
            timeout_diagnostic_stop.set()


def _configured_asyncio_mode(config: pytest.Config) -> str | None:
    try:
        return str(config.getini("asyncio_mode")).lower()
    except (ValueError, TypeError):
        return None


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    """Run coroutine tests if pytest-asyncio auto mode was not applied."""
    if _configured_asyncio_mode(pyfuncitem.config) == "auto":
        return None
    if pyfuncitem.get_closest_marker("asyncio") is not None:
        return None
    if pyfuncitem.get_closest_marker("anyio") is not None:
        return None

    test_object = getattr(pyfuncitem, "obj", None)
    if not inspect.iscoroutinefunction(test_object):
        return None

    testargs = {
        argname: pyfuncitem.funcargs[argname]
        for argname in pyfuncitem._fixtureinfo.argnames
    }
    asyncio.run(test_object(**testargs))
    return True


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Treat `--last-failed` empty selections as a successful no-op run.

    Pytest returns `NO_TESTS_COLLECTED` when the last-failed cache does not
    intersect the currently selected path set, even if the path itself contains
    collected tests. IDE runners surface that as a hard failure/empty suite.
    Keep genuine "no tests here" failures intact by only normalizing runs that
    collected tests before the `--last-failed` deselection step.
    """
    if _should_treat_last_failed_empty_suite_as_success(
        config=session.config,
        collected_count=_last_failed_collected_count(session.config),
        exitstatus=exitstatus,
    ):
        session.exitstatus = 0


def _configure_windows_test_mode_for_control_plane_durability() -> None:
    """Relax control-plane fsync on Windows test runs (cloud-synced worktrees).

    FileLineageStore / ledger writers call ``os.fsync``. On Google Drive / OneDrive
    checkouts that can hang long enough for pytest-timeout to kill reproducibility
    contract tests. Production keeps fsync; Windows pytest explicitly enables
    test mode even when the parent IDE environment supplied ``false``.
    """
    if not sys.platform.startswith("win"):
        return
    os.environ["BIOETL_TEST_MODE"] = "true"
    try:
        from bioetl.infrastructure.config._base import get_settings

        get_settings.cache_clear()
    except Exception:
        # Settings may not be importable during early plugin bootstrap; durability
        # will read the updated environment when Settings is first constructed.
        pass


def _windows_local_temp_root() -> Path | None:
    """Return a local (non-cloud) temp root for Windows pytest I/O.

    ``TEMP``/``TMP`` may point at a volume shared with a cloud-synced worktree
    (for example ``E:\\Temp`` next to ``E:\\g-drive\\...``). Long suites then
    hang on trivial ``mkdir``/write under the 60s pytest-timeout budget.
    Prefer ``%LOCALAPPDATA%\\Temp`` when present.
    """
    if not sys.platform.startswith("win"):
        return None
    override = os.environ.get("BIOETL_PYTEST_TEMP_ROOT", "").strip()
    if override:
        root = Path(override).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        return root
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if not local_appdata:
        return None
    root = Path(local_appdata) / "Temp" / "bioetl-pytest"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _configure_windows_local_basetemp(config: pytest.Config) -> None:
    """Force pytest basetemp onto a local disk on Windows when unset."""
    if not sys.platform.startswith("win"):
        return
    # Honour explicit operator override (CLI ``--basetemp`` / env).
    existing = getattr(config.option, "basetemp", None)
    if existing:
        return
    root = _windows_local_temp_root()
    if root is None:
        return
    basetemp = root / f"basetemp-{os.getpid()}"
    basetemp.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = basetemp


def _configure_isolated_run_report_root(config: pytest.Config) -> None:
    """Redirect incidental run-report writes away from the workspace tree.

    ``PipelineRunnerService`` / workflow runners persist pipeline_run_report_v1
    artifacts under ``reports/run-reports`` by default. Unit tests that only
    exercise orchestration still hit that path, and on cloud-synced Windows
    worktrees the atomic write + fsync path has timed out under the 60s budget.
    Keep explicit ``root=`` / ``directory=`` callers (writer unit tests) intact.
    """
    import tempfile

    try:
        from bioetl.application.services.run_reports import writer as run_report_writer
    except Exception:
        # Application package may be unavailable during partial collection setups.
        return

    local_root = _windows_local_temp_root()
    isolated_root = Path(
        tempfile.mkdtemp(
            prefix="bioetl-pytest-run-reports-",
            dir=str(local_root) if local_root is not None else None,
        )
    )
    config.__dict__["_bioetl_run_report_root"] = isolated_root
    config.__dict__["_bioetl_run_report_root_previous"] = (
        run_report_writer.DEFAULT_REPORT_ROOT
    )
    run_report_writer.DEFAULT_REPORT_ROOT = isolated_root


def _configure_windows_asyncio(config: pytest.Config) -> None:
    """Tune pytest-asyncio defaults for Windows socket pressure."""
    if not sys.platform.startswith("win"):
        return

    # On Windows/Python 3.13, function-scoped loop creation across thousands of
    # async tests can exhaust socket buffers during socketpair() setup.
    config.inicfg["asyncio_default_test_loop_scope"] = "module"
    config.inicfg["asyncio_default_fixture_loop_scope"] = "module"


def _windows_xdist_worker_cap() -> int:
    """Return the safe Windows xdist worker cap for local pytest runs."""
    raw_value = os.environ.get(_WINDOWS_XDIST_WORKER_CAP_ENV)
    if raw_value is None:
        return _DEFAULT_WINDOWS_XDIST_WORKER_CAP
    try:
        return max(1, int(raw_value))
    except ValueError:
        return _DEFAULT_WINDOWS_XDIST_WORKER_CAP


def _configure_windows_xdist(config: pytest.Config) -> None:
    """Cap Windows xdist workers even when tests bypass repo wrapper scripts."""
    if not sys.platform.startswith("win"):
        return

    option_namespace = getattr(config, "option", None)
    if option_namespace is None or not hasattr(option_namespace, "numprocesses"):
        return

    requested = getattr(option_namespace, "numprocesses", None)
    if requested in (None, 0):
        return

    cap = _windows_xdist_worker_cap()
    if isinstance(requested, str):
        normalized = requested.strip().lower()
        if normalized == "auto":
            option_namespace.numprocesses = cap
            return
        try:
            requested_count = int(normalized)
        except ValueError:
            return
    elif isinstance(requested, bool):
        return
    else:
        try:
            requested_count = int(requested)
        except (TypeError, ValueError):
            return

    if requested_count > cap:
        option_namespace.numprocesses = cap


def _configure_windows_pycharm_traceback_style(config: pytest.Config) -> None:
    """Avoid Windows/PyCharm hangs while pytest formats failing tracebacks."""
    if not sys.platform.startswith("win") or not _is_pycharm_pytest_runner():
        return

    option_namespace = getattr(config, "option", None)
    if option_namespace is None:
        return

    tbstyle = getattr(option_namespace, "tbstyle", None)
    if tbstyle not in {"line", "no"}:
        option_namespace.tbstyle = "line"


def _extend_windows_pycharm_vcr_timeout(item: pytest.Item) -> None:
    """Give Windows/PyCharm VCR replays a bounded collection-time timeout."""
    if not sys.platform.startswith("win") or not _is_pycharm_pytest_runner():
        return
    if item.get_closest_marker("vcr") is None:
        return
    if item.get_closest_marker("timeout") is not None:
        return

    raw_cli_timeout = getattr(getattr(item.config, "option", None), "timeout", None)
    cli_timeout = _coerce_timeout_seconds(raw_cli_timeout)
    if raw_cli_timeout in {0, "0"} or (
        cli_timeout is not None and cli_timeout >= _WINDOWS_PYCHARM_VCR_TIMEOUT_SECONDS
    ):
        return

    item.add_marker(pytest.mark.timeout(_WINDOWS_PYCHARM_VCR_TIMEOUT_SECONDS))


def _is_wsl() -> bool:
    """Detect if running under WSL (Windows Subsystem for Linux)."""
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def _configure_wsl_timeout(config: pytest.Config) -> None:
    """Apply WSL-specific safeguards for the cloud-mounted test runtime."""
    if not _is_wsl():
        return

    async def _run_inline[ResultT](
        func: Callable[..., ResultT],
        /,
        *args: object,
        **kwargs: object,
    ) -> ResultT:
        return func(*args, **kwargs)

    # Python 3.13 on the WSL cloud-mounted checkout can lose the event-loop
    # completion callback after a default-executor worker has already finished.
    # Tests then hang indefinitely in otherwise completed local filesystem I/O.
    asyncio.to_thread = _run_inline

    # Increase timeout from default 60s to 180s on WSL
    try:
        current_timeout = config.getini("timeout")
        if current_timeout and float(current_timeout) < 180:
            config.inicfg["timeout"] = "180"
    except (ValueError, TypeError, AttributeError):
        config.inicfg["timeout"] = "180"


def _is_pycharm_pytest_runner() -> bool:
    if os.environ.get("PYCHARM_HOSTED") == "1":
        return True
    return any("_jb_pytest_runner.py" in arg.replace("\\", "/") for arg in sys.argv)


def _should_treat_last_failed_empty_suite_as_success(
    *,
    config: pytest.Config,
    collected_count: int,
    exitstatus: int,
) -> bool:
    """Return True when `--last-failed` produced an empty selected suite."""
    return (
        exitstatus == pytest.ExitCode.NO_TESTS_COLLECTED
        and collected_count > 0
        and _is_last_failed_run(config)
    )


def _is_last_failed_run(config: pytest.Config) -> bool:
    """Detect either `--last-failed` spellings used by pytest/config wrappers."""
    option_namespace = getattr(config, "option", None)
    if option_namespace is not None and getattr(option_namespace, "lf", False):
        return True
    try:
        return bool(config.getoption("lf"))
    except (AttributeError, TypeError, ValueError):
        return False


def _reset_last_failed_collection_state(config: pytest.Config) -> None:
    """Initialize per-session collection state used by last-failed policy."""
    config.__dict__["_bioetl_last_failed_collected_count"] = 0


def _last_failed_collected_count(config: pytest.Config) -> int:
    """Return the tracked pre-deselection item count for the current run."""
    return int(getattr(config, "_bioetl_last_failed_collected_count", 0))


def _windows_selector_loop_factory() -> asyncio.AbstractEventLoop:
    """Create Windows selector loops without overriding pytest-asyncio policy fixture."""
    return asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()


def _supports_pytest_asyncio_loop_factories_hook() -> bool:
    """Return whether the installed pytest-asyncio exposes the loop-factories hook."""
    if not sys.platform.startswith("win"):
        return False
    try:
        raw_version = version("pytest-asyncio")
    except PackageNotFoundError:
        return False

    major_minor: list[int] = []
    for part in raw_version.split("."):
        digits = "".join(ch for ch in part if ch.isdigit())
        if not digits:
            break
        major_minor.append(int(digits))
        if len(major_minor) == 2:
            break

    while len(major_minor) < 2:
        major_minor.append(0)
    return tuple(major_minor) >= (1, 4)


# pytest-asyncio < 1.4 rejects unknown hook implementations during collection.
if _supports_pytest_asyncio_loop_factories_hook():

    def pytest_asyncio_loop_factories(
        config: pytest.Config,
        item: pytest.Item,
    ) -> dict[str, Any]:
        """Provide a selector-loop factory on Windows for pytest-asyncio >= 1.4."""
        del config, item
        return {"windows_selector": _windows_selector_loop_factory}


def _normalize_enum_option(option_namespace: object, option_name: str) -> None:
    """Convert a known enum option to its primitive value for xdist safety."""
    if not hasattr(option_namespace, option_name):
        return
    try:
        value = getattr(option_namespace, option_name)
        if isinstance(value, enum.Enum):
            setattr(option_namespace, option_name, value.value)
    except (AttributeError, TypeError, ValueError):
        return


_PUBLICATION_CLASSIFICATION_TEST_PREFIXES = (
    "tests/integration/test_cross_provider_doi_normalization.py",
    "tests/integration/pipelines/test_crossref_date_normalization.py",
    "tests/integration/pipelines/test_pubmed_date_normalization.py",
    "tests/e2e/test_chembl_publication_e2e.py",
    "tests/e2e/test_chembl_publication_term_e2e.py",
    "tests/e2e/test_crossref_publication_e2e.py",
    "tests/e2e/test_openalex_publication_e2e.py",
    "tests/e2e/test_pubmed_publication_e2e.py",
    "tests/e2e/test_semanticscholar_publication_e2e.py",
)

_HYPOTHESIS_TEST_PREFIXES = (
    "tests/unit/domain/",
    "tests/architecture/",
    "tests/unit/application/composite/test_join_key_resolution_property.py",
)
_BENCHMARK_TEST_PREFIXES = (
    "tests/benchmarks/",
    "tests/performance/",
)
_DEFAULT_MARK_EXPR = "not benchmark and not slow"


def _selected_test_paths(config: pytest.Config) -> tuple[str, ...]:
    """Return normalized explicit pytest selection paths."""
    selected_args = getattr(config, "args", ())
    normalized_args: list[str] = []
    for arg in selected_args:
        if arg.startswith("-"):
            continue
        normalized = arg.split("::", 1)[0].replace("\\", "/")
        if normalized in {"tests", "tests/", "."}:
            return ("tests/",)
        normalized_args.append(normalized)
    return tuple(normalized_args)


def _selected_paths_need_hypothesis(config: pytest.Config) -> bool:
    """Load Hypothesis profiles only when the selected paths can execute them."""
    selected_paths = _selected_test_paths(config)
    if not selected_paths:
        return True

    if selected_paths == ("tests/",):
        return True

    return any(
        any(path.startswith(prefix) for prefix in _HYPOTHESIS_TEST_PREFIXES)
        for path in selected_paths
    )


def _selected_paths_are_benchmark_only(config: pytest.Config) -> bool:
    """Return True when the explicit selection targets only benchmark suites."""
    selected_paths = _selected_test_paths(config)
    if not selected_paths or selected_paths == ("tests/",):
        return False
    return all(
        any(
            path == prefix.removesuffix("/") or path.startswith(prefix)
            for prefix in _BENCHMARK_TEST_PREFIXES
        )
        for path in selected_paths
    )


def _auto_enable_benchmark_selection_for_explicit_benchmark_runs(
    config: pytest.Config,
) -> None:
    """Replace the repo default markexpr for explicit benchmark-only runs."""
    markexpr = getattr(config.option, "markexpr", "")
    if (
        isinstance(markexpr, str)
        and markexpr.strip() == _DEFAULT_MARK_EXPR
        and _selected_paths_are_benchmark_only(config)
    ):
        config.option.markexpr = "benchmark"


def _configure_hypothesis_profiles() -> None:
    """Register project Hypothesis profiles lazily during pytest startup."""
    try:
        from hypothesis import settings as _hyp_settings
    except ImportError:  # pragma: no cover
        return

    _hyp_settings.register_profile("ci", max_examples=10)
    _hyp_settings.register_profile("fast", max_examples=5)
    _hyp_settings.register_profile("dev", max_examples=50)
    _hyp_settings.register_profile("thorough", max_examples=200)
    _hyp_settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fast"))


@cache
def _load_vcrpy() -> Any:
    """Import vcr lazily so collect-only runs skip this dependency cost."""
    try:
        import vcr as vcrpy
    except ImportError:  # pragma: no cover
        return None
    return vcrpy


def _selected_tests_need_publication_type_classification(
    request: pytest.FixtureRequest,
) -> bool:
    """Return True when the current selection needs classification bootstrap."""
    items = getattr(request.session, "items", ())
    if not items:
        # Collect-only and nested collection runs do not execute publication
        # transformers and should avoid the global bootstrap cost.
        return False
    return any(
        item.nodeid.startswith(_PUBLICATION_CLASSIFICATION_TEST_PREFIXES)
        for item in items
    )


@pytest.fixture(scope="session", autouse=True)
def _init_publication_type_classification(request: pytest.FixtureRequest) -> None:
    """Initialize publication type classification data only for non-unit suites."""
    if not _selected_tests_need_publication_type_classification(request):
        return

    from bioetl.composition.bootstrap.runtime.classification_init import (
        initialize_publication_type_classification,
    )

    initialize_publication_type_classification(Path("configs"))


@pytest.fixture(scope="session", autouse=True)
def _sanitize_bioetl_env_vars() -> None:
    """Strip inline comments from BIOETL_ env vars.

    Some CI environments load .env.example with inline comments
    (e.g. ``100  # 1-10000``), which Pydantic interprets as invalid
    string values. This fixture strips everything after ``#`` for
    all BIOETL_ variables so Settings() can parse them correctly.
    """
    for key in tuple(os.environ):
        if key.startswith("BIOETL_"):
            val = os.environ[key]
            cleaned = _strip_inline_env_comment(val)
            if cleaned != val:
                os.environ[key] = cleaned


def _strip_inline_env_comment(value: str) -> str:
    hash_index = value.find("#")
    if hash_index == -1:
        return value
    prefix = value[:hash_index]
    stripped = prefix.rstrip()
    return stripped if stripped != value else value


@pytest.fixture(scope="session", autouse=True)
def default_vcr_record_mode() -> None:
    """Set deterministic default VCR mode for local runs.

    - CI remains strict (`none`) to prevent silent cassette rewrites.
    - Local runs also default to strict replay (`none`).
    - Explicit VCR_RECORD_MODE always has priority.
    """
    if "VCR_RECORD_MODE" not in os.environ:
        os.environ["VCR_RECORD_MODE"] = "none"
    ensure_default_vcr_record_mode()


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return repository root for path-based architecture checks."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def _pin_test_cwd_to_project_root(project_root: Path) -> Generator[None, None, None]:
    """Run the test session from repo root even when wrappers launch pytest elsewhere."""
    previous_cwd = Path.cwd()
    os.chdir(project_root)
    try:
        yield
    finally:
        os.chdir(previous_cwd)


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    """Return the `src` directory used by architecture tests."""
    src_path = project_root / "src"
    if not src_path.exists():
        pytest.skip("Source directory not found: src")
    return src_path


@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    """Return path to pyproject.toml."""
    return project_root / "pyproject.toml"


@pytest.fixture
def isolated_registry() -> Any:
    """Return a fresh pipeline registry instance for test isolation."""
    from bioetl.composition.registry_api import create_registry

    return create_registry()


@pytest.fixture
def populated_isolated_registry(isolated_registry: Any) -> Any:
    """Return isolated registry pre-populated with all pipelines."""
    # Lazy import to avoid timeout on Windows during test collection
    # Only import when this fixture is actually used
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines(registry=isolated_registry)
    return isolated_registry


@pytest.fixture(scope="session")
def cached_bootstrap_metadata(project_root: Path) -> Any:
    """Cache immutable catalog metadata for repo-backed bootstrap tests."""
    from tests.helpers.bootstrap_cache import BootstrapMetadataCache

    return BootstrapMetadataCache().get_or_build(configs_root=project_root / "configs")


@pytest.fixture
def cached_populated_isolated_registry(cached_bootstrap_metadata: Any) -> Any:
    """Return a per-test clone of the cached populated pipeline registry."""
    from tests.helpers.bootstrap_cache import clone_pipeline_registry

    return clone_pipeline_registry(cached_bootstrap_metadata)


@pytest.fixture
def cached_provider_registry(cached_bootstrap_metadata: Any) -> Any:
    """Return a per-test clone of the cached populated provider registry."""
    from tests.helpers.bootstrap_cache import clone_provider_registry

    return clone_provider_registry(cached_bootstrap_metadata)


@pytest.fixture(autouse=True)
def _vcr_marker(request: pytest.FixtureRequest) -> None:
    """Handle VCR cassettes with Git LFS pointer checking for pytest-recording."""
    marker = request.node.get_closest_marker("vcr")
    if marker is None:
        return

    cassette_path = resolve_requested_cassette_path(request)
    if cassette_path is not None and is_git_lfs_pointer(cassette_path):
        if is_vcr_recording_mode():
            cassette_path.unlink(missing_ok=True)
        elif is_strict_lfs_pointer_blocked_cassette(cassette_path):
            pytest.fail(
                "Replay-critical VCR cassette is an unresolved Git LFS pointer; "
                f"run git lfs pull before replaying this cassette: {cassette_path}",
                pytrace=False,
            )
        else:
            pytest.skip(
                "VCR cassette is a Git LFS pointer; run git lfs pull before replaying "
                f"this cassette: {cassette_path}"
            )
    elif (
        cassette_path is not None
        and not cassette_path.exists()
        and not is_vcr_recording_mode()
    ):
        pytest.skip(
            f"VCR cassette not found: {cassette_path}. "
            f"Run with VCR_RECORD_MODE=new_episodes to record cassettes."
        )


@pytest.fixture(scope="session")
def disable_recording() -> bool:
    """Disable pytest-recording autouse VCR; BioETL replays committed cassettes locally."""
    return True


@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """VCR configuration for integration tests."""
    return build_base_vcr_config(
        filter_headers=["authorization", "x-api-key", "cookie"],
        filter_query_parameters=["api_key", "key"],
        ignore_localhost=True,
    )


def _resolve_vcr_cassette_name(
    *,
    request: pytest.FixtureRequest,
    cassette_dir: Path,
) -> str:
    """Prefer committed class-qualified cassette names when they exist."""
    node_name = request.node.name
    nodeid_parts = request.node.nodeid.split("::")
    class_name = nodeid_parts[-2] if len(nodeid_parts) >= 3 else None
    candidate_names = []
    if class_name is not None:
        candidate_names.append(f"{class_name}.{node_name}")
    candidate_names.append(node_name)

    for candidate in candidate_names:
        if (cassette_dir / f"{candidate}.yaml").exists():
            return candidate
    return candidate_names[0]


@pytest.fixture
def vcr_cassette_name(
    request: pytest.FixtureRequest,
    vcr_cassette_dir: Path,
) -> str:
    """Prefer committed class-qualified cassette names when they exist."""
    return _resolve_vcr_cassette_name(request=request, cassette_dir=vcr_cassette_dir)


@pytest.fixture
def default_cassette_name(
    request: pytest.FixtureRequest,
    vcr_cassette_dir: Path,
) -> str:
    """pytest-recording-compatible alias for committed cassette naming."""
    return _resolve_vcr_cassette_name(request=request, cassette_dir=vcr_cassette_dir)


@pytest.fixture(scope="module")
def vcr_cassette_dir(
    request: pytest.FixtureRequest,
    project_root: Path,
    vcr_config: dict[str, object],
) -> Path:
    """Resolve cassette directories without depending on pytest-recording fixtures."""
    configured_dir = vcr_config.get("cassette_library_dir")
    if isinstance(configured_dir, str) and configured_dir:
        return Path(configured_dir)

    provider_dir = infer_provider_cassette_dir(
        node_name=request.node.name,
        module_path=str(getattr(request.node, "fspath", "")),
        overrides={},
    )
    return build_cassette_dir(
        fixtures_root=project_root / "tests" / "fixtures" / "vcr",
        provider_dir=provider_dir,
    )


@cache
def _load_pandas() -> Any:
    """Import pandas lazily so pytest collection stays lightweight."""
    try:
        import pandas as pd
    except ImportError:  # pragma: no cover
        return None
    return pd


@pytest.fixture
def vcr(  # type: ignore[override]
    vcr_config: dict[str, object],
    vcr_cassette_dir: Path | str,
) -> Any:
    """Configure VCR instance with custom matchers."""
    vcrpy = _load_vcrpy()
    if vcrpy is None:
        pytest.skip("vcrpy not installed")
    kwargs: dict[str, object] = {
        "cassette_library_dir": str(vcr_cassette_dir),
        "path_transformer": vcrpy.VCR.ensure_suffix(".yaml"),
    }
    kwargs.update(vcr_config)
    vcr_instance = vcrpy.VCR(**kwargs)
    vcr_instance.register_matcher("query_ignore_email", query_ignore_email)
    return vcr_instance


@pytest.fixture(autouse=True)
def _manual_vcr_marker_runtime(
    request: pytest.FixtureRequest,
) -> Generator[None, None, None]:
    """Replay VCR cassettes from tests/fixtures/vcr via repo-local vcrpy wiring."""
    marker = request.node.get_closest_marker("vcr")
    if marker is None:
        yield
        return

    cassette_path = resolve_requested_cassette_path(request)
    if cassette_path is None:
        yield
        return

    if cassette_path.exists() and is_git_lfs_pointer(cassette_path):
        if is_vcr_recording_mode():
            cassette_path.unlink(missing_ok=True)
        elif is_strict_lfs_pointer_blocked_cassette(cassette_path):
            pytest.fail(
                "Replay-critical VCR cassette is an unresolved Git LFS pointer; "
                f"run git lfs pull before replaying this cassette: {cassette_path}",
                pytrace=False,
            )
        else:
            pytest.skip(
                "VCR cassette is a Git LFS pointer; run git lfs pull before replaying "
                f"this cassette: {cassette_path}"
            )

    vcr = request.getfixturevalue("vcr")
    with vcr.use_cassette(str(cassette_path), **marker.kwargs):
        yield


@pytest.fixture
def noop_logger():
    """Minimal no-op logger for tests."""
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    return NoOpLogger()


# --- Publication Fixtures (Minimal DataFrames for Validation) ---

from tests.helpers.publication_fixtures import (
    CHEMBL_SPECIFIC,
    CROSSREF_SPECIFIC,
    OPENALEX_SPECIFIC,
    PUBMED_SPECIFIC,
    SEMANTIC_SCHOLAR_SPECIFIC,
    create_minimal_df as _create_minimal_df,
)


@pytest.fixture
def minimal_pubmed_publication_df():
    df = _create_minimal_df(
        PUBMED_SPECIFIC, "pubmed", "pubmed_12345678", "pmid", "12345678"
    )
    df["abstract_structured"] = False
    # Fix for TestPublicationTypeValid::test_pub_type_present
    df["publication_type"] = "Journal Article"
    return df


@pytest.fixture
def minimal_chembl_publication_df():
    df = _create_minimal_df(
        CHEMBL_SPECIFIC, "chembl", "CHEMBL123", "publication_id", "CHEMBL123"
    )
    df["publication_type"] = "journal-article"
    return df


@pytest.fixture
def minimal_semanticscholar_publication_df():
    return _create_minimal_df(
        SEMANTIC_SCHOLAR_SPECIFIC,
        "semanticscholar",
        "s2_" + "a" * 40,
        "paper_id",
        "a" * 40,
    )


@pytest.fixture
def minimal_openalex_publication_df():
    df = _create_minimal_df(
        OPENALEX_SPECIFIC, "openalex", "W12345678", "openalex_id", "W12345678"
    )
    df["is_retracted"] = False
    return df


@pytest.fixture
def minimal_crossref_publication_df():
    return _create_minimal_df(
        CROSSREF_SPECIFIC, "crossref", "10.1001/test", "doi", "10.1001/test"
    )
