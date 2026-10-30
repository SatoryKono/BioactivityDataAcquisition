"""Regression and negative checks for the bounded production-input probe."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.engineering.performance import measure_merger_input as harness

pytestmark = [
    pytest.mark.performance,
    pytest.mark.serial,
    pytest.mark.skipif(
        sys.platform != "linux" or harness.resource is None,
        reason="The bounded production-input probe requires Linux RLIMIT_AS",
    ),
]


@pytest.mark.timeout(120)
def test_measurement_harness_smoke(tmp_path):
    """Each repeat uses real production read code in a distinct limited process."""
    output = tmp_path / "observations.json"
    result = subprocess.run(
        [
            sys.executable,
            str(Path(harness.__file__)),
            "--scales",
            "10",
            "--repeats",
            "2",
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=100,
    )
    assert result.returncode == 0, result.stderr + (
        output.read_text() if output.exists() else ""
    )
    payload = json.loads(output.read_text())
    first, second = payload["observations"]
    assert first["raw"]["pid"] != second["raw"]["pid"]
    assert (
        first["raw"]["service"]
        == "bioetl.application.composite.merge_service.MergeService"
    )
    assert (
        first["raw"]["read_method"] == "bioetl.application.composite.merger_input_mixin"
    )
    assert first["raw"]["rlimit_as_bytes"] == 4096 * harness.MIB
    assert first["raw"]["process_peak_rss_bytes"] > 0
    assert first["preparation"]["exit_code"] == first["measurement"]["exit_code"] == 0
    assert first["fixture_sha256"]
    assert payload["source"]["harness_sha256"]
    assert payload["source_unchanged"]
    assert payload["conclusion"].startswith("NOT_ESTABLISHED")


@pytest.mark.parametrize(
    "arguments",
    [
        ["--memory-mib", "0"],
        ["--memory-mib", "4097"],
        ["--scales", "100001"],
        ["--scales", "-1"],
        ["--repeats", "0"],
        ["--timeout-s", "0"],
        ["--phase", "measure"],
        ["--scales", "1", "2", "3", "4", "5", "6", "7", "8", "9"],
    ],
)
def test_rejects_unbounded_or_invalid_requests(arguments):
    """Invalid inputs fail before importing data libraries or launching a child."""
    result = subprocess.run(
        [sys.executable, harness.__file__, *arguments],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2


def test_guard_keeps_stricter_inherited_address_limit():
    """A lower inherited hard limit is kept; the harness must not raise it."""
    code = (
        "import resource\n"
        "from scripts.engineering.performance.measure_merger_input import apply_guard\n"
        "resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2, 256 * 1024**2))\n"
        "apply_guard(512, 5)\n"
        "soft, hard = resource.getrlimit(resource.RLIMIT_AS)\n"
        "assert soft == hard == 256 * 1024**2, (soft, hard)\n"
    )
    result = harness.run_bounded([sys.executable, "-c", code], 10)
    assert result["exit_code"] == 0, result["stderr"]


def test_source_identity_reports_git_timeout(monkeypatch):
    """A hung git status must fail source collection instead of blocking forever."""

    def expire(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(
            cmd=["git"], timeout=harness.GIT_IDENTITY_TIMEOUT_S
        )

    monkeypatch.setattr(harness.subprocess, "check_output", expire)
    with pytest.raises(RuntimeError, match="source identity collection timed out"):
        harness.source_identity()


def test_missing_cgroup_is_recorded_as_null(tmp_path, monkeypatch):
    """Measurements are still written when cgroup v2 memory.max is absent."""
    monkeypatch.setattr(
        harness, "read_cgroup_memory_max", lambda: (None, "unavailable")
    )
    monkeypatch.setattr(harness, "source_identity", lambda: {"head": "bound"})
    monkeypatch.setattr(
        harness,
        "run_bounded",
        lambda *_args, **_kwargs: {"exit_code": 0, "timed_out": False},
    )
    monkeypatch.setattr(
        harness, "fixture_identity", lambda _directory: {"table": "digest"}
    )
    monkeypatch.setattr(
        harness,
        "measure_repeat",
        lambda *_args, **_kwargs: {"status": "COMPLETED"},
    )
    output = tmp_path / "observations.json"
    code = harness.orchestrate(
        SimpleNamespace(
            scales=[10],
            repeats=1,
            memory_mib=128,
            timeout_s=5,
            out=output,
        )
    )
    payload = json.loads(output.read_text())
    assert code == 0
    assert payload["environment"]["cgroup_memory_max"] is None
    assert payload["environment"]["cgroup_memory_max_status"] == "unavailable"


def test_cgroup_memory_max_reads_available_value(tmp_path):
    """A present memory.max value is kept with an explicit collected status."""
    path = tmp_path / "memory.max"
    path.write_text("17179869184\n", encoding="utf-8")
    assert harness.read_cgroup_memory_max(path) == ("17179869184", "collected")
    missing = tmp_path / "absent.max"
    assert harness.read_cgroup_memory_max(missing) == (None, "unavailable")


def test_guard_enforces_allocation_limit():
    """A real child cannot allocate beyond RLIMIT_AS; this is not a mock assertion."""
    code = (
        "from scripts.engineering.performance.measure_merger_input import apply_guard; "
        "apply_guard(128, 5); bytearray(256 * 1024**2)"
    )
    result = harness.run_bounded([sys.executable, "-c", code], 10)
    assert result["exit_code"] != 0
    assert "MemoryError" in result["stderr"]


def test_timeout_records_actual_exit():
    """Timeout is blocked evidence with the actual kill exit, never successful telemetry."""
    result = harness.run_bounded(
        [sys.executable, "-c", "import time; time.sleep(10)"], 1
    )
    assert result["timed_out"]
    assert result["exit_code"] == -9


def test_existing_raw_evidence_is_preserved(tmp_path):
    """The CLI cannot overwrite an earlier observation file."""
    output = tmp_path / "raw.json"
    output.write_text("historical bytes")
    result = subprocess.run(
        [sys.executable, harness.__file__, "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert output.read_text() == "historical bytes"


def test_output_boundary_rejects_escape_before_launch():
    """An absolute output outside the two supported roots cannot launch work."""
    result = subprocess.run(
        [sys.executable, harness.__file__, "--out", "/proc/pr12274-never-created.json"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "Path must resolve inside" in result.stderr


def test_output_boundary_resolves_symlinks(tmp_path):
    """A symlink inside temporary storage cannot escape to an external root."""
    link = tmp_path / "escape"
    link.symlink_to("/proc", target_is_directory=True)
    with pytest.raises(ValueError, match="Path must resolve inside"):
        harness.confined_path(link / "pr12274-never-created.json")


@pytest.mark.parametrize("rows", [1, 10, 100_000])
def test_value_validation_accepts_finite_roundoff(rows):
    """One representable step is allowed, including around the zero-row-index sum."""
    import math

    expected = 0.75 * rows * (rows - 1)
    assert (
        harness.validate_values(rows, math.nextafter(expected, math.inf), rows) is None
    )


@pytest.mark.parametrize(
    ("actual_rows", "total", "rows"),
    [
        (9, 67.5, 10),
        (10, float("nan"), 10),
        (10, float("inf"), 10),
        (10, -float("inf"), 10),
        (10, 69.0, 10),
        (1, 1e-8, 1),
        (100_000, 7_499_925_001.5, 100_000),
    ],
)
def test_value_validation_rejects_wrong_count_nonfinite_or_corruption(
    actual_rows, total, rows
):
    """Tolerance must not accept a missing row, nonfinite sum or one fixture step."""
    with pytest.raises(ValueError, match="row count/value validation"):
        harness.validate_values(actual_rows, total, rows)


@pytest.mark.parametrize(
    ("prep_exit", "prep_timeout", "run_exit", "run_timeout", "stdout", "status"),
    [
        (2, False, 0, False, "{}", "BLOCKED"),
        (0, True, 0, False, "{}", "BLOCKED"),
        (0, False, -9, True, "partial", "BLOCKED"),
        (0, False, 3, False, "error", "BLOCKED"),
        (0, False, 0, True, "{}", "BLOCKED"),
        (0, False, 0, False, "invalid json", "BLOCKED_INVALID_OUTPUT"),
        (0, False, 0, False, '{"rows": 10}', "COMPLETED"),
    ],
)
def test_repeat_preserves_raw_failure_and_success_states(
    monkeypatch, prep_exit, prep_timeout, run_exit, run_timeout, stdout, status
):
    """Refactoring must preserve exit/timeout/stdout/stderr and skip failed fixtures."""
    preparation = {"exit_code": prep_exit, "timed_out": prep_timeout}
    run = {
        "exit_code": run_exit,
        "timed_out": run_timeout,
        "stdout": stdout,
        "stderr": "raw stderr",
        "elapsed_s": 0.125,
    }
    calls = []

    def fake_run(command, timeout_s):
        calls.append((command, timeout_s))
        return run

    monkeypatch.setattr(harness, "run_bounded", fake_run)
    fixture = {"table": "digest"}
    result = harness.measure_repeat(10, 2, preparation, fixture, ["worker"], 30)
    assert result["status"] == status
    assert result["preparation"] is preparation
    assert result["fixture_sha256"] is fixture
    assert (result["rows"], result["repeat"]) == (10, 2)
    if prep_exit or prep_timeout:
        assert calls == []
        assert result["measurement"] is None
    else:
        assert calls == [(["worker", "--phase", "measure"], 30)]
        assert result["measurement"] is run
    if status == "COMPLETED":
        assert result["raw"] == {"rows": 10}
    else:
        assert "raw" not in result
