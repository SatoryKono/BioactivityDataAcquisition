from __future__ import annotations

import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

_TIMEOUT_SECONDS = 30
_HEAD = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    check=True,
    capture_output=True,
    text=True,
    timeout=_TIMEOUT_SECONDS,
).stdout.strip()
_TEST_ID = "tests/benchmarks/test_perf.py::test_alpha"
_NEW_ID = "tests/benchmarks/test_perf.py::test_beta"
_OTHER_SCOPE = "tests/performance/test_hotspot_budgets.py::test_gamma"


def _run(
    args: list[str], *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            env=env,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f"child process exceeded {_TIMEOUT_SECONDS}s: {exc}")


def _github_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REPOSITORY": "SatoryKono/BioactivityDataAcquisition",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_RUN_ID": "38926061151",
            "GITHUB_SERVER_URL": "https://github.com",
            "GITHUB_SHA": _HEAD,
        }
    )
    return env


def _measurement(
    mean: int,
    *,
    test_id: str = _TEST_ID,
    dataset: str = "locked-nightly",
    has_error: bool = False,
    rounds: int | None = 5,
    include_stats: bool = True,
) -> dict[str, object]:
    entry: dict[str, object] = {"fullname": test_id, "has_error": has_error}
    if include_stats:
        stats: dict[str, object] = {"rounds": rounds}
        if mean is not None:
            stats["mean"] = mean
        entry["stats"] = stats
    payload: dict[str, object] = {
        "benchmarks": [entry],
        "bioetl_measurement": {
            "dataset": dataset,
            "environment": "github-actions",
        },
        "bioetl_run": {"id": "11111111-1111-1111-1111-111111111111"},
        "bioetl_source": {
            "revision": _HEAD,
            "revision_method": "gitdir_head_file",
        },
        "commit_info": {"dirty": None, "id": _HEAD},
    }
    return payload


def _baseline(
    mean: int = 100, *, test_id: str = _TEST_ID, scope: str = "tests/benchmarks/"
) -> dict[str, object]:
    return {
        "adoption": "measured",
        "baseline_sha": "a" * 40,
        "dataset": "locked-nightly",
        "environment": "github-actions",
        "schema_version": 1,
        "tests": [
            {
                "dataset": "locked-nightly",
                "environment": "github-actions",
                "mean": mean,
                "scope": scope,
                "test_id": test_id,
            }
        ],
        "threshold": "0.1",
    }


def _invoke(
    tmp_path: Path,
    raw: bytes | None,
    *,
    baseline: dict[str, object] | None = None,
    env: dict[str, str] | None = None,
    gate_name: str = "gate.json",
    extra: list[str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    raw_path = tmp_path / "benchmark-measurements.json"
    if raw is not None:
        raw_path.write_bytes(raw)
    gate = tmp_path / gate_name
    manifest = tmp_path / "manifest.json"
    baseline_path = tmp_path / "benchmark-summary.json"
    baseline_path.write_text(
        json.dumps(baseline if baseline is not None else _baseline()),
        encoding="utf-8",
    )
    args = [
        sys.executable,
        "-m",
        "scripts.engineering.qa",
        "reduce-benchmark-evidence",
        "--raw-json",
        str(raw_path),
        "--manifest-out",
        str(manifest),
        "--gate-out",
        str(gate),
        "--baseline",
        str(baseline_path),
        "--evidence-dir",
        str(tmp_path / "evidence"),
        "--output-root",
        str(tmp_path),
        "--checkout-sha",
        _HEAD,
        *(extra or []),
    ]
    return _run(args, env=env if env is not None else _github_env()), gate, manifest


def _gate(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_missing_empty_encoding_and_malformed_json(tmp_path: Path) -> None:
    missing, gate, _manifest = _invoke(tmp_path, None)
    assert missing.returncode == 1, missing.stderr
    assert _gate(gate)["reason"] == "missing_observations"
    assert _gate(gate)["status"] == "failed"

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    empty, empty_gate, _manifest = _invoke(empty_dir, b"")
    assert empty.returncode == 1, empty.stderr
    assert _gate(empty_gate)["reason"] == "empty_input"

    binary_dir = tmp_path / "binary"
    binary_dir.mkdir()
    binary, binary_gate, _manifest = _invoke(binary_dir, b"\xff\xfe")
    assert binary.returncode == 1, binary.stderr
    assert _gate(binary_gate)["reason"] == "invalid_encoding"

    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    bad, bad_gate, _manifest = _invoke(bad_dir, b"{bad")
    assert bad.returncode == 1, bad.stderr
    assert _gate(bad_gate)["reason"] == "malformed_json"


def test_structural_failures_have_exact_reasons(tmp_path: Path) -> None:
    cases = {
        "root": (b"[]", "malformed_json"),
        "null-entry": (
            json.dumps({"benchmarks": [None]}).encode(),
            "malformed_entries",
        ),
        "zero": (json.dumps({"benchmarks": []}).encode(), "zero_execution"),
        "skipped": (
            json.dumps({"benchmarks": [{"fullname": _TEST_ID}]}).encode(),
            "all_skipped",
        ),
        "partial": (
            json.dumps(
                {
                    "benchmarks": [
                        {"fullname": _TEST_ID, "stats": {"mean": 100, "rounds": 5}},
                        {"fullname": _NEW_ID},
                    ]
                }
            ).encode(),
            "incomplete_evidence",
        ),
        "nan": (
            b'{"benchmarks":[{"fullname":"tests/benchmarks/test_perf.py::test_alpha","stats":{"mean":NaN,"rounds":5}}]}',
            "malformed_json",
        ),
        "bool-mean": (
            json.dumps(
                {
                    "benchmarks": [
                        {
                            "fullname": _TEST_ID,
                            "stats": {"mean": True, "rounds": 5},
                        }
                    ]
                }
            ).encode(),
            "unusable_measurement",
        ),
    }
    for name, (raw, reason) in cases.items():
        case_dir = tmp_path / name
        case_dir.mkdir()
        result, gate, _manifest = _invoke(case_dir, raw)
        assert result.returncode == 1, result.stderr
        assert _gate(gate)["status"] == "failed"
        assert _gate(gate)["reason"] == reason, name


def test_execution_error_is_not_labeled_regression(tmp_path: Path) -> None:
    payload = _measurement(100, has_error=True, include_stats=False)
    result, gate, _manifest = _invoke(
        tmp_path, json.dumps(payload).encode(), env=_github_env()
    )
    assert result.returncode == 1, result.stderr
    body = _gate(gate)
    assert body["status"] == "failed"
    assert body["reason"] == "execution_error"


def test_rejects_paths_outside_the_output_root(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"outside-gate-{tmp_path.name}.json"
    if outside.exists():
        outside.unlink()
    raw = tmp_path / "benchmark-measurements.json"
    raw.write_text("{}", encoding="utf-8")
    result = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "reduce-benchmark-evidence",
            "--raw-json",
            str(raw),
            "--manifest-out",
            str(tmp_path / "manifest.json"),
            "--gate-out",
            str(outside),
            "--baseline",
            str(tmp_path / "benchmark-summary.json"),
            "--evidence-dir",
            str(tmp_path / "evidence"),
            "--output-root",
            str(tmp_path),
        ]
    )
    assert result.returncode == 2, result.stderr
    assert "rejected_output_path" in result.stderr
    assert not outside.exists()


def test_stale_passed_gate_is_replaced(tmp_path: Path) -> None:
    gate = tmp_path / "gate.json"
    gate.write_text('{"reason":"complete","status":"passed"}\n', encoding="utf-8")
    result, written, _manifest = _invoke(tmp_path, None, gate_name="gate.json")
    assert result.returncode == 1, result.stderr
    body = _gate(written)
    assert body["status"] == "failed"
    assert body["reason"] == "missing_observations"


def test_fifteen_percent_slowdown_fails_and_improvement_passes(tmp_path: Path) -> None:
    slow_dir = tmp_path / "slow"
    slow_dir.mkdir()
    slow_raw = json.dumps(_measurement(115)).encode()
    slow, slow_gate, _manifest = _invoke(slow_dir, slow_raw, baseline=_baseline(100))
    assert slow.returncode == 1, slow.stderr
    slow_body = _gate(slow_gate)
    assert slow_body["status"] == "failed"
    assert slow_body["reason"] == "measured_regression"
    assert slow_body["threshold"] == "0.1"
    row = slow_body["comparisons"][0]
    assert row["verdict"] == "measured_regression"
    assert Decimal(str(row["delta_ratio"])) == Decimal("0.15")
    assert row["scope"] == "tests/benchmarks/"
    evidence = list((slow_dir / "evidence").rglob("benchmark-measurements.json"))
    assert evidence
    assert evidence[0].read_bytes() == slow_raw
    assert (slow_dir / "benchmark-measurements.json").read_bytes() == slow_raw

    fast_dir = tmp_path / "fast"
    fast_dir.mkdir()
    fast, fast_gate, manifest = _invoke(
        fast_dir, json.dumps(_measurement(90)).encode(), baseline=_baseline(100)
    )
    assert fast.returncode == 0, fast.stderr
    fast_body = _gate(fast_gate)
    assert fast_body["status"] == "passed"
    assert fast_body["reason"] == "improvement"
    assert fast_body["run_id"] == "38926061151"
    assert fast_body["run_url"] == (
        "https://github.com/SatoryKono/BioactivityDataAcquisition/actions/runs/38926061151"
    )
    assert fast_body["baseline_sha"] == "a" * 40
    assert fast_body["measured_sha"] == _HEAD
    assert "tests/performance/" not in fast_body["scopes"]
    assert json.loads(manifest.read_text(encoding="utf-8"))["reason"] == "improvement"
    stored_gate = list((fast_dir / "evidence").rglob("benchmark-gate.json"))
    stored_manifest = list((fast_dir / "evidence").rglob("benchmark-manifest.json"))
    assert len(stored_gate) == 1
    assert len(stored_manifest) == 1
    assert (
        json.loads(stored_gate[0].read_text(encoding="utf-8"))["reason"]
        == "improvement"
    )
    assert stored_manifest[0].read_bytes() == stored_gate[0].read_bytes()


def test_new_test_needs_a_comparable_baseline(tmp_path: Path) -> None:
    added = _measurement(100)
    added["benchmarks"] = [
        {"fullname": _TEST_ID, "stats": {"mean": 100, "rounds": 5}},
        {"fullname": _NEW_ID, "stats": {"mean": 100, "rounds": 5}},
    ]
    allowed_dir = tmp_path / "allowed"
    allowed_dir.mkdir()
    allowed, allowed_gate, _manifest = _invoke(
        allowed_dir, json.dumps(added).encode(), baseline=_baseline(100)
    )
    assert allowed.returncode == 0, allowed.stderr
    body = _gate(allowed_gate)
    assert body["status"] == "passed"
    verdicts = {row["test_id"]: row["verdict"] for row in body["comparisons"]}
    assert verdicts[_NEW_ID] == "new_test"
    assert verdicts[_TEST_ID] == "within_threshold"

    absent_dir = tmp_path / "absent"
    absent_dir.mkdir()
    absent, absent_gate, _manifest = _invoke(
        absent_dir,
        json.dumps(_measurement(100)).encode(),
        baseline={
            "adoption": "absent",
            "reason": "no_accepted_measurement",
            "schema_version": 1,
            "tests": [],
            "threshold": "0.1",
        },
    )
    assert absent.returncode == 1, absent.stderr
    assert _gate(absent_gate)["reason"] == "insufficient_baseline"

    other_dir = tmp_path / "other-scope"
    other_dir.mkdir()
    other_payload = _measurement(100, test_id=_OTHER_SCOPE)
    other, other_gate, _manifest = _invoke(
        other_dir, json.dumps(other_payload).encode(), baseline=_baseline(100)
    )
    assert other.returncode == 1, other.stderr
    assert _gate(other_gate)["reason"] == "insufficient_baseline"

    both = _baseline(100)
    both["tests"].append(
        {
            "dataset": "locked-nightly",
            "environment": "github-actions",
            "mean": 100,
            "scope": "tests/performance/",
            "test_id": _OTHER_SCOPE,
        }
    )
    dropped_dir = tmp_path / "dropped-scope"
    dropped_dir.mkdir()
    dropped, dropped_gate, _manifest = _invoke(
        dropped_dir, json.dumps(_measurement(100)).encode(), baseline=both
    )
    assert dropped.returncode == 1, dropped.stderr
    assert _gate(dropped_gate)["reason"] == "missing_baseline_scope"


def test_missing_baseline_test_fails(tmp_path: Path) -> None:
    result, gate, _manifest = _invoke(
        tmp_path,
        json.dumps(_measurement(100, test_id=_NEW_ID)).encode(),
        baseline=_baseline(100, test_id=_TEST_ID),
    )
    assert result.returncode == 1, result.stderr
    body = _gate(gate)
    assert body["reason"] == "missing_baseline_test"
    assert body["comparisons"][0]["verdict"] == "missing_baseline_test"


def test_unknown_run_and_ancestry_do_not_pass(tmp_path: Path) -> None:
    local = os.environ.copy()
    local.pop("GITHUB_ACTIONS", None)
    result, gate, _manifest = _invoke(
        tmp_path, json.dumps(_measurement(90)).encode(), env=local
    )
    assert result.returncode == 1, result.stderr
    assert _gate(gate)["reason"] == "unproven_environment"

    uuid_dir = tmp_path / "uuid-run"
    uuid_dir.mkdir()
    uuid_env = _github_env()
    uuid_env["GITHUB_RUN_ID"] = "11111111-1111-1111-1111-111111111111"
    uuid_result, uuid_gate, _manifest = _invoke(
        uuid_dir, json.dumps(_measurement(90)).encode(), env=uuid_env
    )
    assert uuid_result.returncode == 1, uuid_result.stderr
    assert _gate(uuid_gate)["reason"] == "unproven_run"

    ancestor_dir = tmp_path / "ancestor"
    ancestor_dir.mkdir()
    payload = _measurement(90)
    payload["bioetl_source"]["revision"] = "b" * 40
    payload["commit_info"]["id"] = "b" * 40
    ancestor, ancestor_gate, _manifest = _invoke(
        ancestor_dir, json.dumps(payload).encode()
    )
    assert ancestor.returncode == 1, ancestor.stderr
    assert _gate(ancestor_gate)["reason"] == "wrong_sha"


def test_synthetic_fixture_can_pass_after_adoption(tmp_path: Path) -> None:
    baseline = _baseline(100)
    baseline["dataset"] = "synthetic"
    baseline["tests"][0]["dataset"] = "synthetic"
    adopted_dir = tmp_path / "adopted"
    adopted_dir.mkdir()
    adopted, adopted_gate, _manifest = _invoke(
        adopted_dir,
        json.dumps(_measurement(90, dataset="synthetic")).encode(),
        baseline=baseline,
    )
    assert adopted.returncode == 0, adopted.stderr
    assert _gate(adopted_gate)["reason"] == "improvement"
    assert _gate(adopted_gate)["dataset"] == "synthetic"

    absent = {
        "adoption": "absent",
        "reason": "no_accepted_measurement",
        "schema_version": 1,
        "tests": [],
        "threshold": "0.1",
    }
    initial_dir = tmp_path / "initial"
    initial_dir.mkdir()
    raw = json.dumps(_measurement(90, dataset="synthetic")).encode()
    initial, initial_gate, _manifest = _invoke(initial_dir, raw, baseline=absent)
    assert initial.returncode == 1, initial.stderr
    assert _gate(initial_gate)["reason"] == "insufficient_baseline"
    stored = list((initial_dir / "evidence").rglob("benchmark-summary-candidate.json"))
    assert len(stored) == 1
    candidate = json.loads(stored[0].read_text(encoding="utf-8"))
    assert candidate["adoption"] == "proposed"
    assert candidate["dataset"] == "synthetic"
    assert candidate["tests"][0]["mean"] == "90"
    measurements = list((initial_dir / "evidence").rglob("benchmark-measurements.json"))
    assert measurements[0].read_bytes() == raw
    committed = json.loads(
        (initial_dir / "benchmark-summary.json").read_text(encoding="utf-8")
    )
    assert committed["adoption"] == "absent"


def test_hotspot_gate_rejects_missing_summary_and_missing_report(
    tmp_path: Path,
) -> None:
    report = tmp_path / "hotspot-degradation.json"
    report.write_text(
        json.dumps({"summary": {"failed": 0}, "verdict": "measured"}),
        encoding="utf-8",
    )
    zero = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "gate-hotspot-report",
            "--report",
            str(report),
            "--output-root",
            str(tmp_path),
        ]
    )
    assert zero.returncode == 1, zero.stderr
    assert json.loads(zero.stdout)["reason"] == "zero_observations"

    defaulted = tmp_path / "defaulted.json"
    defaulted.write_text(json.dumps({"verdict": "measured"}), encoding="utf-8")
    masked = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "gate-hotspot-report",
            "--report",
            str(defaulted),
            "--output-root",
            str(tmp_path),
        ]
    )
    assert masked.returncode == 1, masked.stderr
    assert json.loads(masked.stdout)["reason"] == "missing_summary"

    missing = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "gate-hotspot-report",
            "--report",
            str(tmp_path / "absent.json"),
            "--output-root",
            str(tmp_path),
        ]
    )
    assert missing.returncode == 1, missing.stderr
    assert "missing_report" in missing.stderr

    outside = tmp_path.parent / f"hotspot-outside-{tmp_path.name}.json"
    escaped = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "gate-hotspot-report",
            "--report",
            str(outside),
            "--output-root",
            str(tmp_path),
        ]
    )
    assert escaped.returncode == 2, escaped.stderr
    assert "rejected_output_path" in escaped.stderr


def test_non_positive_means_do_not_pass(tmp_path: Path) -> None:
    zero_current = tmp_path / "zero-current"
    zero_current.mkdir()
    current, current_gate, _manifest = _invoke(
        zero_current, json.dumps(_measurement(0)).encode(), baseline=_baseline(100)
    )
    assert current.returncode == 1, current.stderr
    assert _gate(current_gate)["reason"] == "unusable_measurement"

    negative_current = tmp_path / "negative-current"
    negative_current.mkdir()
    negative, negative_gate, _manifest = _invoke(
        negative_current,
        json.dumps(_measurement(-1)).encode(),
        baseline=_baseline(100),
    )
    assert negative.returncode == 1, negative.stderr
    assert _gate(negative_gate)["reason"] == "unusable_measurement"

    zero_base = tmp_path / "zero-base"
    zero_base.mkdir()
    raw = zero_base / "benchmark-measurements.json"
    raw.write_bytes(json.dumps(_measurement(90)).encode())
    based, based_gate, _manifest = _invoke(
        zero_base, raw.read_bytes(), baseline=_baseline(0)
    )
    assert based.returncode == 1, based.stderr
    assert _gate(based_gate)["reason"] == "invalid_baseline"
    assert raw.read_bytes() == json.dumps(_measurement(90)).encode()
    assert _gate(based_gate)["status"] == "failed"

    duplicate = _baseline(100)
    rows = duplicate["tests"]
    assert isinstance(rows, list)
    rows.append(
        {
            "dataset": "locked-nightly",
            "environment": "github-actions",
            "mean": 1000,
            "scope": "tests/benchmarks/",
            "test_id": _TEST_ID,
        }
    )
    duplicate_dir = tmp_path / "duplicate-key"
    duplicate_dir.mkdir()
    duplicated, duplicated_gate, _manifest = _invoke(
        duplicate_dir,
        json.dumps(_measurement(500)).encode(),
        baseline=duplicate,
    )
    assert duplicated.returncode == 1, duplicated.stderr
    assert _gate(duplicated_gate)["reason"] == "invalid_baseline"

    snan = _baseline(100)
    snan["threshold"] = "sNaN"
    snan_dir = tmp_path / "snan"
    snan_dir.mkdir()
    snan_result, snan_gate, _manifest = _invoke(
        snan_dir, json.dumps(_measurement(90)).encode(), baseline=snan
    )
    assert snan_result.returncode == 1, snan_result.stderr
    assert "InvalidOperation" not in snan_result.stderr
    assert _gate(snan_gate)["reason"] == "invalid_baseline"

    repeated = _measurement(100)
    benchmarks = repeated["benchmarks"]
    assert isinstance(benchmarks, list)
    benchmarks.append(dict(benchmarks[0]))
    repeated_dir = tmp_path / "duplicate-current"
    repeated_dir.mkdir()
    repeated_result, repeated_gate, _manifest = _invoke(
        repeated_dir,
        json.dumps(repeated).encode(),
        baseline=_baseline(100),
    )
    assert repeated_result.returncode == 1, repeated_result.stderr
    assert _gate(repeated_gate)["reason"] == "duplicate_measurement"
    assert not any(
        (repeated_dir / "evidence").rglob("benchmark-summary-candidate.json")
    )


def test_clean_checkout_accepts_boolean_dirty_false(tmp_path: Path) -> None:
    payload = _measurement(90)
    payload["commit_info"] = {"dirty": False, "id": _HEAD}
    clean_dir = tmp_path / "clean"
    clean_dir.mkdir()
    clean, clean_gate, _manifest = _invoke(
        clean_dir, json.dumps(payload).encode(), baseline=_baseline(100)
    )
    assert clean.returncode == 0, clean.stderr
    assert _gate(clean_gate)["reason"] == "improvement"

    dirty_payload = _measurement(90)
    dirty_payload["commit_info"] = {"dirty": True, "id": _HEAD}
    dirty_dir = tmp_path / "dirty"
    dirty_dir.mkdir()
    dirty, dirty_gate, _manifest = _invoke(
        dirty_dir, json.dumps(dirty_payload).encode(), baseline=_baseline(100)
    )
    assert dirty.returncode == 1, dirty.stderr
    assert _gate(dirty_gate)["reason"] == "incomplete_evidence"


def test_distinct_outputs_and_string_baseline_mean(tmp_path: Path) -> None:
    raw = tmp_path / "benchmark-measurements.json"
    raw.write_bytes(json.dumps(_measurement(90)).encode())
    original = raw.read_bytes()
    collided = _run(
        [
            sys.executable,
            "-m",
            "scripts.engineering.qa",
            "reduce-benchmark-evidence",
            "--raw-json",
            str(raw),
            "--manifest-out",
            str(raw),
            "--gate-out",
            str(tmp_path / "gate.json"),
            "--baseline",
            str(tmp_path / "benchmark-summary.json"),
            "--evidence-dir",
            str(tmp_path / "evidence"),
            "--output-root",
            str(tmp_path),
            "--checkout-sha",
            _HEAD,
        ],
        env=_github_env(),
    )
    assert collided.returncode == 2, collided.stderr
    assert "rejected_output_path" in collided.stderr
    assert raw.read_bytes() == original

    string_dir = tmp_path / "strings"
    string_dir.mkdir()
    string_mean = _baseline(100)
    string_mean["tests"][0]["mean"] = "100"
    adopted, adopted_gate, _manifest = _invoke(
        string_dir,
        json.dumps(_measurement(90)).encode(),
        baseline=string_mean,
    )
    assert adopted.returncode == 0, adopted.stderr
    assert _gate(adopted_gate)["reason"] == "improvement"


def test_hotspot_rejects_negative_failures_and_non_positive_latency(
    tmp_path: Path,
) -> None:
    from scripts.engineering.qa.generate_hotspot_degradation_report import (
        HotspotLoadError,
        _load_observations,
        judge_hotspot_report,
    )

    status, reason = judge_hotspot_report(
        {"summary": {"failed": -1, "total": 1}, "verdict": "measured"}
    )
    assert status == "failed"
    assert reason == "invalid_summary"
    empty_status, empty_reason = judge_hotspot_report(
        {"summary": {"failed": 0, "total": 1}, "verdict": "measured"}
    )
    assert empty_status == "failed"
    assert empty_reason == "inconsistent_summary"
    contradicted, contradicted_reason = judge_hotspot_report(
        {
            "benchmarks": [{"within_budget": False}],
            "summary": {"failed": 0, "total": 1},
            "verdict": "measured",
        }
    )
    assert contradicted == "failed"
    assert contradicted_reason == "inconsistent_summary"

    observations = tmp_path / "observations.jsonl"
    observations.write_text(
        json.dumps(
            {
                "benchmark_key": "alpha",
                "latency_ms": 0,
                "p95_latency_ms": 1,
                "throughput_rps": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(HotspotLoadError) as captured:
        _load_observations(observations, root=tmp_path)
    assert captured.value.reason == "malformed_observations"


def test_confined_byte_write_ignores_predictable_tmp_sibling(tmp_path: Path) -> None:
    from scripts.engineering.common.repo_paths import write_bytes_confined

    target = tmp_path / "benchmark-measurements.json"
    decoy = tmp_path / "benchmark-measurements.json.tmp"
    decoy.write_bytes(b"keep")
    write_bytes_confined(target, b"payload", root=tmp_path)
    assert target.read_bytes() == b"payload"
    assert decoy.read_bytes() == b"keep"
