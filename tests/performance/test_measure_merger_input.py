"""Regression and negative checks for the bounded production-input probe."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.engineering.performance import measure_merger_input as harness

pytestmark = [pytest.mark.performance, pytest.mark.serial]


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
        timeout=90,
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
    harness.validate_values(rows, math.nextafter(expected, math.inf), rows)


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
