import pytest

pytestmark = pytest.mark.architecture

import json
import subprocess
from pathlib import Path


def test_missing_json(tmp_path: Path) -> None:
    raw_json = tmp_path / "missing.json"
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "missing_observations" in gate.read_text()
    assert "Integration blocker: caller contract unavailable" in result.stderr


def test_malformed_json(tmp_path: Path) -> None:
    raw_json = tmp_path / "malformed.json"
    raw_json.write_text("{bad json")
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "malformed_json" in gate.read_text()


def test_zero_execution(tmp_path: Path) -> None:
    raw_json = tmp_path / "empty.json"
    raw_json.write_text(json.dumps({"benchmarks": []}))
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "zero_execution" in gate.read_text()


def test_all_skipped(tmp_path: Path) -> None:
    raw_json = tmp_path / "skipped.json"
    raw_json.write_text(
        json.dumps(
            {
                "benchmarks": [{"has_error": False, "stats": {}}],
                "bioetl_source": {"revision": "abcdef123456"},
            }
        )
    )
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
            "--checkout-sha",
            "abcdef123456",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "all_skipped" in gate.read_text()


def test_failed_benchmark(tmp_path: Path) -> None:
    raw_json = tmp_path / "failed.json"
    raw_json.write_text(
        json.dumps(
            {
                "benchmarks": [{"has_error": True, "stats": None}],
                "bioetl_source": {"revision": "abcdef123456"},
            }
        )
    )
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
            "--checkout-sha",
            "abcdef123456",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "measured_regression" in gate.read_text()


def test_wrong_sha(tmp_path: Path) -> None:
    raw_json = tmp_path / "measurements.json"
    raw_json.write_text(
        json.dumps(
            {
                "benchmarks": [{"stats": {"mean": 1.0}}],
                "bioetl_source": {"revision": "abcdef123456"},
            }
        )
    )
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
            "--checkout-sha",
            "wrongsha",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "wrong_sha" in gate.read_text()


def test_valid_evidence_passed(tmp_path: Path) -> None:
    raw_json = tmp_path / "measurements.json"
    raw_json.write_text(
        json.dumps(
            {
                "benchmarks": [{"stats": {"mean": 1.0}}],
                "bioetl_source": {"revision": "abcdef123456"},
            }
        )
    )
    manifest = tmp_path / "manifest.json"
    gate = tmp_path / "gate.json"

    result = subprocess.run(
        [
            "python",
            "-m",
            "scripts.engineering.qa.reduce_benchmark_evidence",
            "--raw-json",
            str(raw_json),
            "--manifest-out",
            str(manifest),
            "--gate-out",
            str(gate),
            "--checkout-sha",
            "abcdef123456",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "passed" in gate.read_text()
    assert json.loads(manifest.read_text())["actual_measured_sha"] == "abcdef123456"
