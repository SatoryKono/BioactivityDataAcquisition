"""Local telemetry rejects incomplete and substituted measurement artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from scripts.engineering.ci.local_test_telemetry import (
    build_local_baseline,
    junit_telemetry_sha256,
    validate_local_measurement,
)
from scripts.engineering.qa.run_local_coverage_verify import SHARDS

pytestmark = pytest.mark.unit


@pytest.fixture
def measurement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(
        "scripts.engineering.ci.local_test_telemetry.subprocess.run",
        lambda *args, **kwargs: CompletedProcess(args, 0),
    )
    coverage = tmp_path / "coverage.xml"
    coverage.write_text('<coverage line-rate="0.99" branch-rate="0.91"/>')
    rows = []
    for shard in SHARDS:
        junit = tmp_path / f"{shard.name}.xml"
        junit.write_text(
            '<testsuite tests="2"><testcase classname="tests.example" name="passed" '
            'time="0"/><testcase name="skipped" time="0.01"><skipped/></testcase></testsuite>'
        )
        rows.append(
            {
                "name": shard.name,
                "exit_code": 0,
                "seconds": 1.5,
                "coverage_sha256": "a" * 64,
                "junit_file": str(junit),
                "junit_telemetry_sha256": junit_telemetry_sha256(junit),
            }
        )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "producer": "run_local_coverage_verify.py",
                "complete": True,
                "head": "b" * 40,
                "source_branch": "codex/test",
                "test_tree_sha256": "tests",
                "source_tree_sha256": "source",
                "required_shards": [shard.name for shard in SHARDS],
                "shards": rows,
                "line_gate_exit_code": 0,
                "branch_gate_exit_code": 0,
                "coverage_xml": str(coverage),
                "coverage_xml_sha256": hashlib.sha256(
                    coverage.read_bytes()
                ).hexdigest(),
                "line_percent": 99.0,
                "branch_percent": 91.0,
                "started_at_utc": "2026-10-01T00:00:00+00:00",
                "finished_at_utc": "2026-10-01T01:00:00+00:00",
            }
        )
    )
    return manifest


def _validate(manifest: Path) -> dict:
    return validate_local_measurement(
        manifest,
        repo_root=manifest.parent,
        test_tree_sha256="tests",
        source_tree_sha256="source",
    )


def test_complete_measurement_counts_zero_duration_cases(measurement: Path) -> None:
    result = _validate(measurement)
    assert result["counts"] == {"passed": 17, "skipped": 17}
    assert len(result["junit_paths"]) == 17
    assert sum(result["duration_sums"].values()) == pytest.approx(0.17)


def test_local_baseline_never_reuses_cached_ci_identity_or_summary(
    measurement: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.engineering.ci.update_test_telemetry_baseline.compute_test_telemetry_source_tree_sha256",
        lambda root: "tests",
    )
    monkeypatch.setattr(
        "scripts.engineering.qa.report_module_coverage_inventory.compute_source_tree_sha256",
        lambda **kwargs: "source",
    )
    (measurement.parent / "not-a-cached-ci-summary.json").write_text(
        json.dumps(
            {
                "total_cases": 999999,
                "top_slowest": [{"test": "cached", "duration_s": 999}],
            }
        )
    )
    baseline = build_local_baseline(measurement, repo_root=measurement.parent)
    assert baseline["source_event"] == "local_coverage_verify"
    assert baseline["source_run_url"] is None
    assert baseline["source_run_id"].startswith("local-")
    assert baseline["source_commit"] == "b" * 40
    assert baseline["coverage"]["actual_percent"] == 99.0
    assert baseline["duration_telemetry"]["total_cases"] == 17
    assert all(
        row["test"] != "cached" for row in baseline["duration_telemetry"]["top_slowest"]
    )
    assert (
        baseline["measurement_provenance"]["ci_status"] == "BLOCKED_EXTERNAL_PERMANENT"
    )
    assert baseline["measurement_provenance"]["trust_tier"] == "local_single_host"


@pytest.mark.parametrize(
    "mutation",
    [
        "incomplete",
        "missing_shard",
        "duplicate_shard",
        "failed_shard",
        "failed_gate",
        "test_drift",
        "source_drift",
        "coverage_tamper",
        "junit_tamper",
        "failed_junit",
        "missing_timestamp",
        "unreachable_commit",
        "missing_junit_digest",
        "wrong_producer",
        "future_timestamp",
        "reversed_timestamps",
    ],
)
def test_local_capture_fails_closed(
    measurement: Path,
    mutation: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = json.loads(measurement.read_text())
    if mutation == "incomplete":
        payload["complete"] = False
    elif mutation == "missing_shard":
        payload["shards"].pop()
    elif mutation == "duplicate_shard":
        payload["shards"][-1] = payload["shards"][0]
    elif mutation == "failed_shard":
        payload["shards"][0]["exit_code"] = 1
    elif mutation == "failed_gate":
        payload["branch_gate_exit_code"] = 1
    elif mutation == "test_drift":
        payload["test_tree_sha256"] = "other"
    elif mutation == "source_drift":
        payload["source_tree_sha256"] = "other"
    elif mutation == "coverage_tamper":
        Path(payload["coverage_xml"]).write_text('<coverage line-rate="0.84"/>')
    elif mutation in {"junit_tamper", "failed_junit"}:
        row = payload["shards"][0]
        junit = Path(row["junit_file"])
        junit.write_text(
            '<testsuite><testcase name="passed" time="1"><failure/></testcase></testsuite>'
        )
        if mutation == "failed_junit":
            row["junit_telemetry_sha256"] = junit_telemetry_sha256(junit)
    elif mutation == "missing_timestamp":
        payload.pop("finished_at_utc")
    elif mutation == "unreachable_commit":
        monkeypatch.setattr(
            "scripts.engineering.ci.local_test_telemetry.subprocess.run",
            lambda *args, **kwargs: CompletedProcess(args, 1),
        )
    elif mutation == "missing_junit_digest":
        payload["shards"][0].pop("junit_telemetry_sha256")
    elif mutation == "wrong_producer":
        payload["producer"] = "focused_pytest"
    elif mutation == "future_timestamp":
        payload["finished_at_utc"] = "2099-01-01T00:00:00+00:00"
    elif mutation == "reversed_timestamps":
        payload["finished_at_utc"] = "2026-09-30T00:00:00+00:00"
    measurement.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        _validate(measurement)


def test_junit_telemetry_digest_ignores_redacted_log_text(tmp_path: Path) -> None:
    junit = tmp_path / "junit.xml"
    junit.write_text(
        '<testsuite><testcase name="case" time="1"><system-out>secret</system-out></testcase></testsuite>'
    )
    original = junit_telemetry_sha256(junit)
    junit.write_text(junit.read_text().replace("secret", "[REDACTED_LOCAL_SECRET]"))
    assert junit_telemetry_sha256(junit) == original


@pytest.mark.parametrize("field", ["coverage_xml", "junit_file"])
@pytest.mark.parametrize("relative", [False, True])
def test_manifest_cannot_read_xml_outside_measurement(
    measurement: Path, monkeypatch: pytest.MonkeyPatch, field: str, relative: bool
) -> None:
    payload = json.loads(measurement.read_text())
    outside = measurement.parent.parent / f"{measurement.parent.name}-outside.xml"
    outside.write_text("sensitive external data")
    path = "../" + outside.name if relative else str(outside)
    if field == "coverage_xml":
        payload[field] = path
    else:
        payload["shards"][0][field] = path
    measurement.write_text(json.dumps(payload))
    original_read = Path.read_bytes

    def guarded_read(path: Path) -> bytes:
        assert path != outside, "External artifact was opened before validation"
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    with pytest.raises(ValueError, match="within its manifest directory"):
        _validate(measurement)


def test_manifest_itself_must_be_within_repo(
    measurement: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = measurement.parent / "repo"
    repo_root.mkdir()
    original_read = Path.read_text

    def guarded_read(path: Path, *args: object, **kwargs: object) -> str:
        assert path != measurement, "External manifest was read before validation"
        return original_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read)
    with pytest.raises(ValueError, match="within the repository"):
        validate_local_measurement(
            measurement,
            repo_root=repo_root,
            test_tree_sha256="tests",
            source_tree_sha256="source",
        )


@pytest.mark.parametrize("field", ["coverage_xml", "junit_file"])
def test_manifest_cannot_follow_xml_symlink_outside_measurement(
    measurement: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    outside = (
        measurement.parent.parent / f"{measurement.parent.name}-symlink-target.xml"
    )
    outside.write_text("external data")
    link = measurement.parent / "external.xml"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")
    payload = json.loads(measurement.read_text())
    if field == "coverage_xml":
        payload[field] = str(link)
    else:
        payload["shards"][0][field] = str(link)
    measurement.write_text(json.dumps(payload))
    original_read = Path.read_bytes

    def guarded_read(path: Path) -> bytes:
        assert path not in {outside, link}, "External symlink target was read"
        return original_read(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read)
    with pytest.raises(ValueError, match="within its manifest directory"):
        _validate(measurement)


@pytest.mark.parametrize("target_exists", [False, True])
def test_external_xml_symlink_does_not_disclose_target_existence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_exists: bool
) -> None:
    from scripts.engineering.ci.local_test_telemetry import _measurement_file

    measurement_root = tmp_path / "measurement"
    measurement_root.mkdir()
    external = tmp_path / "external.xml"
    if target_exists:
        external.write_text("private data")
    link = measurement_root / "coverage.xml"
    try:
        link.symlink_to(external)
    except OSError as error:
        pytest.skip(f"symlink creation unavailable: {error}")

    def forbidden_probe(path: Path) -> bool:
        pytest.fail(f"File existence was probed before boundary rejection: {path}")

    monkeypatch.setattr(Path, "is_file", forbidden_probe)
    monkeypatch.setattr(Path, "resolve", forbidden_probe)
    with pytest.raises(
        ValueError,
        match="^Local measurement XML must remain within its manifest directory$",
    ):
        _measurement_file(str(link), measurement_root=measurement_root)


@pytest.mark.parametrize("target_exists", [False, True])
def test_noncanonical_xml_is_rejected_before_filesystem_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, target_exists: bool
) -> None:
    from scripts.engineering.ci.local_test_telemetry import _measurement_file

    candidate = tmp_path / "private.xml"
    if target_exists:
        candidate.write_text("private")

    def forbidden_probe(*args: object, **kwargs: object) -> bool:
        pytest.fail("An unregistered artifact must not cause a filesystem probe")

    monkeypatch.setattr(Path, "is_file", forbidden_probe)
    monkeypatch.setattr(Path, "is_symlink", forbidden_probe)
    monkeypatch.setattr(Path, "resolve", forbidden_probe)
    with pytest.raises(ValueError, match="within its manifest directory"):
        _measurement_file(str(candidate), measurement_root=tmp_path)
