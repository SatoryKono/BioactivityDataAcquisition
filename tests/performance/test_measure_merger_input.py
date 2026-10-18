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
