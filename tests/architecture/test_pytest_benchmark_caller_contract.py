# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
"""CF-039: explicit pytest-benchmark caller, VCS-probe absence, provenance."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

import pytest
import yaml

from tests.benchmarks.benchmark_vcs_guard import (
    BenchmarkMeasurementContractError,
    read_source_revision,
    validate_benchmark_measurement_json,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "performance-nightly.yml"
PYPROJECT = ROOT / "pyproject.toml"
GUARD_PLUGIN = "tests.benchmarks.benchmark_vcs_guard"
_SYNTHETIC_TEST = """
def test_synthetic_benchmark(benchmark):
    assert benchmark.pedantic(lambda: 1 + 1, rounds=1, iterations=1, warmup_rounds=0) == 2
"""
_SITECUSTOMIZE = """
import json
import os
import subprocess
from pathlib import Path

_LOG = Path(os.environ["BIOETL_VCS_PROBE_LOG"])
_VCS = {"git", "git.exe", "hg", "hg.exe"}


def _tokens(command):
    if isinstance(command, str):
        return command.split()
    return [str(part) for part in command]


def _is_vcs(command):
    tokens = _tokens(command)
    if not tokens:
        return False
    name = tokens[0].replace("\\\\", "/").rsplit("/", 1)[-1].lower()
    return name in _VCS


def _record(command):
    if not _is_vcs(command):
        return False
    with _LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_tokens(command)) + "\\n")
    raise OSError("instrumented VCS probe")


_REAL_RUN = subprocess.run
_REAL_CHECK_OUTPUT = subprocess.check_output
_REAL_CHECK_CALL = subprocess.check_call
_REAL_CALL = subprocess.call


def _run(command, *args, **kwargs):
    _record(command)
    return _REAL_RUN(command, *args, **kwargs)


def _check_output(command, *args, **kwargs):
    _record(command)
    return _REAL_CHECK_OUTPUT(command, *args, **kwargs)


def _check_call(command, *args, **kwargs):
    _record(command)
    return _REAL_CHECK_CALL(command, *args, **kwargs)


def _call(command, *args, **kwargs):
    _record(command)
    return _REAL_CALL(command, *args, **kwargs)


subprocess.run = _run
subprocess.check_output = _check_output
subprocess.check_call = _check_call
subprocess.call = _call
"""


def _workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _workflow_steps() -> list[dict[str, object]]:
    document = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    job = document["jobs"]["performance-regression-gate"]
    steps = job["steps"]
    assert isinstance(steps, list)
    return steps


def _command_text(script: str) -> str:
    kept: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        kept.append(stripped)
    return "\n".join(kept)


def _step_run(name: str) -> str:
    for step in _workflow_steps():
        if step.get("name") == name:
            run = step.get("run")
            assert isinstance(run, str)
            return run
    raise AssertionError(f"missing workflow step {name}")


def _locked_pytest_benchmark_spec() -> tuple[str, str, str]:
    text = (ROOT / "uv.lock").read_text(encoding="utf-8")
    needle = '[[package]]\nname = "pytest-benchmark"\n'
    start = text.index(needle)
    block = text[start : text.index("[[package]]", start + len(needle))]
    version_match = re.search(r'version = "([^"]+)"', block)
    wheel_match = re.search(
        r'url = "(?P<url>[^"]+\.whl)"[^}]*hash = "sha256:(?P<digest>[0-9a-f]+)"',
        block,
    )
    if version_match is None or wheel_match is None:
        raise AssertionError("uv.lock is missing the pytest-benchmark wheel pin")
    return version_match.group(1), wheel_match.group("url"), wheel_match.group("digest")


def _wheel_cache_dir() -> Path:
    return Path(tempfile.gettempdir()) / "bioetl-locked-pytest-benchmark"


def _matching_cached_wheel() -> tuple[str, Path, str] | None:
    version, _url, digest = _locked_pytest_benchmark_spec()
    wheel_path = _wheel_cache_dir() / f"pytest_benchmark-{version}-py3-none-any.whl"
    if not wheel_path.is_file():
        return None
    if hashlib.sha256(wheel_path.read_bytes()).hexdigest() != digest:
        return None
    return version, wheel_path, digest


def _download_locked_wheel() -> tuple[str, Path, str]:
    version, url, digest = _locked_pytest_benchmark_spec()
    cache = _wheel_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    wheel_path = cache / f"pytest_benchmark-{version}-py3-none-any.whl"
    partial = wheel_path.with_suffix(".whl.partial")
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            partial.write_bytes(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        partial.unlink(missing_ok=True)
        pytest.skip(f"locked pytest-benchmark wheel is unreachable: {exc}")
    actual = hashlib.sha256(partial.read_bytes()).hexdigest()
    if actual != digest:
        partial.unlink(missing_ok=True)
        raise AssertionError(f"downloaded wheel hash mismatch: {actual} != {digest}")
    os.replace(partial, wheel_path)
    return version, wheel_path, digest


def _extracted_locked_src(wheel_path: Path, version: str, digest: str) -> Path:
    extracted = wheel_path.parent / version
    stamp = extracted / ".sha256"
    if not stamp.is_file() or stamp.read_text(encoding="utf-8").strip() != digest:
        extracted.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(wheel_path) as archive:
            archive.extractall(extracted)
        stamp.write_text(digest + "\n", encoding="utf-8")
    return extracted


def _lock_resolved_benchmark_src() -> Path | None:
    """Return an extracted lockfile wheel, or None to use the installed package."""

    cached = _matching_cached_wheel()
    if cached is None and os.environ.get("BIOETL_PYTEST_BENCHMARK_FETCH_LOCK") == "1":
        cached = _download_locked_wheel()
    if cached is not None:
        version, wheel_path, digest = cached
        return _extracted_locked_src(wheel_path, version, digest)
    version, _url, _digest = _locked_pytest_benchmark_spec()
    import importlib.metadata as metadata

    try:
        installed = metadata.version("pytest-benchmark")
    except metadata.PackageNotFoundError:
        pytest.skip(
            "pytest-benchmark is not installed and no lockfile wheel is cached; "
            "set BIOETL_PYTEST_BENCHMARK_FETCH_LOCK=1 to fetch the pinned wheel"
        )
    if installed != version:
        pytest.skip(
            "installed pytest-benchmark "
            f"{installed} != uv.lock {version}; set "
            "BIOETL_PYTEST_BENCHMARK_FETCH_LOCK=1 to fetch the pinned wheel"
        )
    return None


def _benchmark_under_test() -> str:
    return os.environ.get("BIOETL_PYTEST_BENCHMARK_UNDER_TEST", "locked")


def _expected_benchmark_version() -> str:
    if _benchmark_under_test() == "installed":
        import importlib.metadata as metadata

        return metadata.version("pytest-benchmark")
    version, _url, _digest = _locked_pytest_benchmark_spec()
    return version


def _probe_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    probe_dir = tmp_path / "probe"
    probe_dir.mkdir()
    (probe_dir / "sitecustomize.py").write_text(_SITECUSTOMIZE, encoding="utf-8")
    log_path = tmp_path / "vcs-probes.jsonl"
    log_path.write_text("", encoding="utf-8")
    pythonpath = [str(probe_dir)]
    if _benchmark_under_test() != "installed":
        source = _lock_resolved_benchmark_src()
        if source is not None:
            pythonpath.append(str(source))
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["BIOETL_VCS_PROBE_LOG"] = str(log_path)
    env["BIOETL_BENCHMARK_CALLER"] = "synthetic-proof"
    return env, log_path


def _probe_lines(log_path: Path) -> list[str]:
    return [
        line
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_missing_pytest_benchmark_package_skips(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.metadata as metadata

    monkeypatch.delenv("BIOETL_PYTEST_BENCHMARK_FETCH_LOCK", raising=False)
    monkeypatch.setattr(
        "tests.architecture.test_pytest_benchmark_caller_contract._matching_cached_wheel",
        lambda: None,
    )

    def _missing(_name: str) -> str:
        raise metadata.PackageNotFoundError

    monkeypatch.setattr(metadata, "version", _missing)
    with pytest.raises(pytest.skip.Exception):
        _lock_resolved_benchmark_src()


def test_pytest_wrappers_load_guard_before_benchmark_plugin() -> None:
    wrappers = (
        ROOT / "scripts" / "engineering" / "dev" / "run_pytest.sh",
        ROOT / "scripts" / "engineering" / "dev" / "run_pytest.ps1",
    )
    for path in wrappers:
        text = path.read_text(encoding="utf-8")
        guard_at = text.index("tests.benchmarks.benchmark_vcs_guard")
        plugin_at = text.index("pytest_benchmark.plugin")
        assert guard_at < plugin_at
        assert "BIOETL_BENCHMARK_CALLER" in text
        assert text.count("pytest_benchmark.plugin") == 1
        if path.suffix == ".ps1":
            assert "[string[]]$Args" not in text
            assert '[Alias("Args")]' in text
            assert "[string[]]$CandidateArgs" in text


def test_guard_import_does_not_sample_the_clock() -> None:
    env = os.environ.copy()
    pythonpath = [str(ROOT), str(ROOT / "src")]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import tests.benchmarks.benchmark_vcs_guard as guard\n"
                "assert guard._started_at is None\n"
            ),
        ],
        cwd=ROOT,
        env=env,
        timeout=30,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr


def test_measurement_start_uses_the_bound_clock() -> None:
    from tests.benchmarks import benchmark_vcs_guard as guard
    from tests.helpers.clock import FIXED_TEST_TIME, FixedClock

    guard.bind_measurement_clock(FixedClock(FIXED_TEST_TIME).now)
    try:
        guard.pytest_configure(object())  # type: ignore[arg-type]
        assert guard.measurement_started_at() == "2026-04-28T12:00:00Z"
        assert guard._run_block()["started_at"] == "2026-04-28T12:00:00Z"
    finally:
        guard.bind_measurement_clock(None)


def test_locked_wheel_cache_stays_outside_the_repository() -> None:
    cache = _wheel_cache_dir()
    assert cache.is_absolute()
    assert not cache.is_relative_to(ROOT)


def test_source_revision_matches_git_rev_parse() -> None:
    source = read_source_revision(ROOT)
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        timeout=20,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert source.revision == completed.stdout.strip().lower()
    assert source.revision_method == "gitdir_head_file"
    assert source.dirty_state == "unknown"


def test_source_revision_without_gitdir_is_blocked(tmp_path: Path) -> None:
    source = read_source_revision(tmp_path, allow_parent_search=False)
    assert source.revision == "unknown"
    assert source.revision_method == "blocked"
    assert source.dirty_state == "unknown"


def test_validator_rejects_missing_empty_and_false_provenance(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    with pytest.raises(BenchmarkMeasurementContractError) as missing_error:
        validate_benchmark_measurement_json(missing, search_from=ROOT)
    assert missing_error.value.code == "missing_output"

    empty = tmp_path / "empty.json"
    empty.write_text(json.dumps({"benchmarks": []}), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as empty_error:
        validate_benchmark_measurement_json(empty, search_from=ROOT)
    assert empty_error.value.code == "no_measurements"

    source = read_source_revision(ROOT)
    zero_rounds = tmp_path / "zero.json"
    zero_rounds.write_text(
        json.dumps(
            {
                "benchmarks": [{"stats": {"rounds": 0}}],
                "commit_info": {"id": source.revision, "dirty": None},
                "bioetl_source": {
                    "schema_version": 1,
                    "revision": source.revision,
                    "revision_method": "gitdir_head_file",
                    "dirty_state": "unknown",
                },
                "bioetl_run": {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "kind": "pytest-benchmark",
                    "caller": "synthetic-proof",
                },
                "bioetl_vcs_guard": {
                    "installed_before_plugin": True,
                    "blocked_probe_attempts": 0,
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(BenchmarkMeasurementContractError) as zero_error:
        validate_benchmark_measurement_json(zero_rounds, search_from=ROOT)
    assert zero_error.value.code == "no_measurements"

    synthetic = tmp_path / "synthetic.json"
    payload = json.loads(zero_rounds.read_text(encoding="utf-8"))
    payload["benchmarks"] = [{"stats": {"rounds": 1}}]
    payload["commit_info"]["id"] = "bioetl-benchmark"
    payload["bioetl_source"]["revision"] = "bioetl-benchmark"
    payload["bioetl_source"]["revision_method"] = "stub"
    synthetic.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as synthetic_error:
        validate_benchmark_measurement_json(synthetic, search_from=ROOT)
    assert synthetic_error.value.code == "blocked_provenance"

    payload["commit_info"] = {"id": source.revision, "dirty": False}
    payload["bioetl_source"]["revision"] = source.revision
    payload["bioetl_source"]["revision_method"] = "gitdir_head_file"
    false_clean = tmp_path / "false-clean.json"
    false_clean.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BenchmarkMeasurementContractError) as clean_error:
        validate_benchmark_measurement_json(false_clean, search_from=ROOT)
    assert clean_error.value.code == "false_dirty_state"


def test_pyproject_keeps_default_benchmark_disable() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    assert '"-p", "no:benchmark"' in text


def test_workflow_enables_guard_before_benchmark_and_keeps_hotspot_fail_open() -> None:
    benchmark_run = _command_text(_step_run("Run pytest-benchmark cases"))
    guard_at = benchmark_run.index(f"-p {GUARD_PLUGIN}")
    benchmark_at = benchmark_run.index("-p benchmark")
    assert guard_at < benchmark_at
    assert "tests/benchmarks/" in benchmark_run
    assert "tests/performance/" not in benchmark_run
    assert (
        "--benchmark-json=reports/performance/benchmark-measurements.json"
        in benchmark_run
    )
    assert "BIOETL_BENCHMARK_CALLER=performance-nightly" in benchmark_run

    hotspot_run = _command_text(_step_run("Run hotspot performance tests"))
    assert "tests/performance/" in hotspot_run
    assert "tests/benchmarks/" not in hotspot_run
    assert "-p benchmark" not in hotspot_run
    assert "-p no:xdist" in hotspot_run

    workflow = _workflow_text()
    assert "No hotspot observations found; skipping report." in workflow
    assert "if [ -f reports/performance/hotspot-degradation.json ]; then" in workflow
    assert "if-no-files-found: warn" in workflow
    assert "workflow_dispatch" in workflow
    assert "schedule:" not in workflow
    gate = _step_run("Require pytest-benchmark measurement JSON")
    assert f"python -m {GUARD_PLUGIN}" in gate
    assert "--validate-measurement-json" in gate
    for name in (
        "Run pytest-benchmark cases",
        "Require pytest-benchmark measurement JSON",
    ):
        step = next(item for item in _workflow_steps() if item.get("name") == name)
        assert step.get("if") == "${{ always() && !cancelled() }}"


@pytest.mark.timeout(180)
def test_default_pytest_skips_benchmark_and_does_not_probe(tmp_path: Path) -> None:
    env, log_path = _probe_env(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--confcutdir",
            str(ROOT / "tests" / "benchmarks"),
            "tests/benchmarks/test_baseline_assertions.py::TestContentHashBaselines::test_small_record_baseline",
            "-q",
            "--tb=short",
        ],
        cwd=ROOT,
        env=env,
        timeout=120,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "skipped" in (completed.stdout + completed.stderr).lower()
    assert _probe_lines(log_path) == []


@pytest.mark.timeout(180)
def test_explicit_caller_measures_case_without_vcs_probe(tmp_path: Path) -> None:
    test_path = tmp_path / "test_synthetic_benchmark.py"
    test_path.write_text(_SYNTHETIC_TEST, encoding="utf-8")
    output_path = tmp_path / "benchmark-measurements.json"
    env, log_path = _probe_env(tmp_path)
    _assert_loaded_benchmark(env)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "--confcutdir",
            str(tmp_path),
            str(test_path),
            "-p",
            GUARD_PLUGIN,
            "-p",
            "benchmark",
            "-p",
            "no:xdist",
            "--benchmark-json",
            str(output_path),
            "--benchmark-warmup=off",
            "--benchmark-min-rounds=1",
            "-q",
            "--tb=short",
        ],
        cwd=ROOT,
        env=env,
        timeout=150,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert _probe_lines(log_path) == []
    payload = validate_benchmark_measurement_json(output_path, search_from=ROOT)
    rounds = [item["stats"]["rounds"] for item in payload["benchmarks"]]
    assert rounds
    assert all(isinstance(value, int) and value >= 1 for value in rounds)
    assert payload["bioetl_run"]["caller"] == "synthetic-proof"
    assert payload["bioetl_run"]["id"] != payload["bioetl_source"]["revision"]
    assert payload["bioetl_source"]["dirty_state"] == "unknown"
    assert payload["version"] == _expected_benchmark_version()
    assert payload["bioetl_run"]["id"] != payload["commit_info"]["id"]


@pytest.mark.timeout(180)
def test_guard_after_benchmark_records_probe_and_rejects_provenance(
    tmp_path: Path,
) -> None:
    test_path = tmp_path / "test_synthetic_benchmark.py"
    test_path.write_text(_SYNTHETIC_TEST, encoding="utf-8")
    output_path = tmp_path / "late-guard.json"
    env, log_path = _probe_env(tmp_path)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "--confcutdir",
            str(tmp_path),
            str(test_path),
            "-p",
            "benchmark",
            "-p",
            GUARD_PLUGIN,
            "-p",
            "no:xdist",
            "--benchmark-json",
            str(output_path),
            "--benchmark-warmup=off",
            "--benchmark-min-rounds=1",
            "-q",
            "--tb=line",
        ],
        cwd=ROOT,
        env=env,
        timeout=150,
        check=False,
        capture_output=True,
        text=True,
    )
    assert _probe_lines(log_path), completed.stdout + completed.stderr
    assert output_path.is_file(), completed.stdout + completed.stderr
    with pytest.raises(BenchmarkMeasurementContractError) as error:
        validate_benchmark_measurement_json(output_path, search_from=ROOT)
    assert error.value.code in {"late_guard", "vcs_probe", "blocked_provenance"}
    loaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert loaded.get("version") == _expected_benchmark_version()
    del completed


def _assert_loaded_benchmark(env: dict[str, str]) -> None:
    script = (
        "import importlib.metadata as metadata\n"
        "import pytest_benchmark.utils as utils\n"
        "from pathlib import Path\n"
        "print(metadata.version('pytest-benchmark'))\n"
        "print(Path(utils.__file__).resolve())\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        timeout=30,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    version, loaded = completed.stdout.splitlines()
    assert version == _expected_benchmark_version()
    loaded_path = Path(loaded).resolve()
    cached = _matching_cached_wheel()
    if _benchmark_under_test() != "installed" and cached is not None:
        version, wheel_path, digest = cached
        source = _extracted_locked_src(wheel_path, version, digest)
        assert loaded_path.is_relative_to(source.resolve())
        return
    import importlib.metadata as metadata

    installed = Path(
        metadata.distribution("pytest-benchmark").locate_file(
            "pytest_benchmark/utils.py"
        )
    ).resolve()
    assert loaded_path == installed


@pytest.mark.timeout(120)
def test_collect_only_does_not_probe_before_execution(tmp_path: Path) -> None:
    test_path = tmp_path / "test_synthetic_benchmark.py"
    test_path.write_text(_SYNTHETIC_TEST, encoding="utf-8")
    env, log_path = _probe_env(tmp_path)
    _assert_loaded_benchmark(env)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--noconftest",
            "--confcutdir",
            str(tmp_path),
            str(test_path),
            "-p",
            GUARD_PLUGIN,
            "-p",
            "benchmark",
            "-p",
            "no:xdist",
            "--collect-only",
            "-q",
        ],
        cwd=ROOT,
        env=env,
        timeout=90,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "test_synthetic_benchmark" in completed.stdout
    assert _probe_lines(log_path) == []


def test_guard_leaves_project_subprocess_calls_intact() -> None:
    import pytest_benchmark.utils as utils

    assert isinstance(subprocess.Popen, type)
    completed = subprocess.run(
        [sys.executable, "-c", "print('seam-ok')"],
        cwd=ROOT,
        timeout=20,
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "seam-ok"
    with pytest.raises(OSError):
        utils.check_output(["git", "rev-parse", "HEAD"])
