from __future__ import annotations

import json
from pathlib import Path

from scripts.engineering.ci.collect_stage0_evidence import (
    evaluate_mypy_criterion,
    sha256,
)
from scripts.engineering.ci.evaluate_mypy import (
    diagnostics_digest,
    normalize_diagnostics,
)


def test_sha256_dict():
    # Positive test
    data1 = {"a": 1, "b": 2}
    data2 = {"b": 2, "a": 1}
    assert sha256(data1) == sha256(data2)


def test_sha256_string():
    # Positive test
    assert (
        sha256("test")
        == "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
    )


def test_normalize_diagnostics_removes_lines():
    # Positive test
    output = "src/file.py:10: error: Something went wrong\nsrc/file.py:15:20: note: See here\nSuccess: no issues found in 2607 source files"
    normalized = normalize_diagnostics(output)
    assert normalized == [
        "src/file.py: error: Something went wrong",
        "src/file.py: note: See here",
    ]


def test_normalize_diagnostics_ignores_success_messages():
    # Negative test (ensure it strips out success/found msgs which vary)
    output = "Found 12 errors in 3 files"
    normalized = normalize_diagnostics(output)
    assert normalized == []


def test_diagnostics_digest_is_stable_sha256():
    normalized = ["a: error: x", "b: note: y"]
    digest = diagnostics_digest(normalized)
    assert digest == diagnostics_digest(list(normalized))
    expected_payload = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    import hashlib

    assert digest == hashlib.sha256(expected_payload.encode("utf-8")).hexdigest()
    assert len(digest) == 64
    assert digest != diagnostics_digest(["other"])


def test_evaluate_mypy_criterion_missing(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = evaluate_mypy_criterion("reports/mypy_eval.json")
    assert result["status"] == "MISSING"
    assert result["typecheck_pass"] is False


def test_evaluate_mypy_criterion_from_pass_report(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    payload = {
        "cold": {"returncode": 0, "time_s": 10.0},
        "warm": {"returncode": 0, "time_s": 4.0},
        "comparison": {
            "diagnostics_match": True,
            "cold_time": 10.0,
            "warm_time": 4.0,
            "speedup": 2.5,
        },
    }
    (reports / "mypy_eval.json").write_text(json.dumps(payload), encoding="utf-8")
    result = evaluate_mypy_criterion("reports/mypy_eval.json")
    assert result["status"] == "PASS"
    assert result["typecheck_pass"] is True
    assert result["cache_measurement_usable"] is True


def test_evaluate_mypy_criterion_typecheck_pass_without_speedup(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    payload = {
        "cold": {"returncode": 0, "time_s": 10.0},
        "warm": {"returncode": 0, "time_s": 10.1},
        "comparison": {
            "diagnostics_match": True,
            "cold_time": 10.0,
            "warm_time": 10.1,
            "speedup": 0.99,
        },
    }
    (reports / "mypy_eval.json").write_text(json.dumps(payload), encoding="utf-8")
    result = evaluate_mypy_criterion("reports/mypy_eval.json")
    assert result["status"] == "PARTIAL"
    assert result["typecheck_pass"] is True
    assert result["cache_measurement_usable"] is False
    assert "Type-checking PASS" in result["note"]
    assert "non-PASS" not in result["note"]


def test_evaluate_mypy_criterion_non_pass(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    reports = tmp_path / "reports"
    reports.mkdir()
    payload = {
        "cold": {"returncode": 1, "time_s": 10.0},
        "warm": {"returncode": 1, "time_s": 4.0},
        "comparison": {
            "diagnostics_match": True,
            "cold_time": 10.0,
            "warm_time": 4.0,
            "speedup": 2.5,
        },
    }
    (reports / "mypy_eval.json").write_text(json.dumps(payload), encoding="utf-8")
    result = evaluate_mypy_criterion("reports/mypy_eval.json")
    assert result["status"] == "PARTIAL"
    assert result["typecheck_pass"] is False
    assert "non-PASS" in result["note"]
