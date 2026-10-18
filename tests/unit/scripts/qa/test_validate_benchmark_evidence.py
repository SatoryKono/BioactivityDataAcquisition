"""Synthetic schema fixtures only: these tests do not capture benchmark timings."""

from __future__ import annotations

import hashlib
import json

import pytest

from scripts.engineering.qa.generate_hotspot_degradation_report import (
    validate_benchmark_evidence_main as main,
    validate_evidence,
)

pytestmark = pytest.mark.unit
_SHA = "a" * 40
_RUN = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def payload() -> dict:
    return {
        "benchmarks": [
            {
                "name": "test_fixture",
                "stats": {
                    "mean": 1.0,
                    "min": 0.5,
                    "max": 1.5,
                    "median": 1.0,
                    "stddev": 0.1,
                    "total": 5.0,
                    "rounds": 5,
                    "iterations": 1,
                },
            }
        ],
        "commit_info": {"id": _SHA},
        "bioetl_source": {"revision": _SHA, "revision_method": "gitdir_head_file"},
        "bioetl_run": {"id": _RUN},
        "machine_info": {
            "node": "fixture-host",
            "system": "Linux",
            "machine": "x86_64",
            "python_version": "3.12",
        },
        "bioetl_measurement": {
            "dataset": "synthetic-schema-fixture-v1",
            "environment": "local",
        },
    }


def _validate(tmp_path, payload, **kwargs):
    path = tmp_path / "measurements.json"
    path.write_text(json.dumps(payload))
    return validate_evidence(
        path,
        _SHA,
        producer_outcome="success",
        root=tmp_path,
        environ=kwargs.get("environ", {}),
    )


def test_benchmark_evidence_valid_evidence_binds_raw_bytes_and_local_provenance(
    tmp_path, payload
):
    manifest = _validate(tmp_path, payload)
    assert manifest["revision"] == manifest["checkout_sha"] == _SHA
    assert manifest["benchmarks_count"] == 1
    assert manifest["dataset_identity"] == "synthetic-schema-fixture-v1"
    assert manifest["environment_identity"] == payload["machine_info"]
    assert (
        manifest["raw_sha256"]
        == hashlib.sha256((tmp_path / "measurements.json").read_bytes()).hexdigest()
    )
    assert manifest["run_id"] == manifest["measured_run_id"] == _RUN
    assert manifest["run_url"] is None


@pytest.mark.parametrize(
    "raw,match",
    [
        (b"", "Empty JSON"),
        (b"{", "Malformed JSON"),
        (b"\xff", "Malformed JSON"),
        (b"[]", "JSON structure"),
    ],
)
def test_benchmark_evidence_invalid_json(tmp_path, raw, match):
    path = tmp_path / "invalid.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match=match):
        validate_evidence(path, _SHA, producer_outcome="success", root=tmp_path)


def test_benchmark_evidence_missing_observations(tmp_path):
    with pytest.raises(ValueError, match="Missing observations"):
        validate_evidence(
            tmp_path / "missing.json", _SHA, producer_outcome="success", root=tmp_path
        )


@pytest.mark.parametrize(
    "benchmarks", [[], {}, "wrong", [None], [{}], [{"name": "test"}]]
)
def test_benchmark_evidence_missing_or_malformed_benchmarks(
    tmp_path, payload, benchmarks
):
    payload["benchmarks"] = benchmarks
    with pytest.raises(ValueError):
        _validate(tmp_path, payload)


@pytest.mark.parametrize("field", ["min", "max", "mean", "median", "stddev", "total"])
@pytest.mark.parametrize(
    "value", [None, True, "1.0", float("nan"), float("inf"), float("-inf"), -1, 10**400]
)
def test_benchmark_evidence_rejects_nonfinite_or_invalid_timings(
    tmp_path, payload, field, value
):
    payload["benchmarks"][0]["stats"][field] = value
    with pytest.raises(ValueError, match="stats"):
        _validate(tmp_path, payload)


@pytest.mark.parametrize("field", ["rounds", "iterations"])
@pytest.mark.parametrize("value", [0, -1, True, None, 1.5])
def test_benchmark_evidence_rejects_unexecuted_samples(tmp_path, payload, field, value):
    payload["benchmarks"][0]["stats"][field] = value
    with pytest.raises(ValueError, match="positive integer"):
        _validate(tmp_path, payload)


@pytest.mark.parametrize(
    "field",
    [
        "commit_info",
        "bioetl_source",
        "bioetl_run",
        "machine_info",
        "bioetl_measurement",
    ],
)
def test_benchmark_evidence_requires_provenance(tmp_path, payload, field):
    del payload[field]
    with pytest.raises(ValueError):
        _validate(tmp_path, payload)


@pytest.mark.parametrize("field", ["node", "system", "machine", "python_version"])
def test_benchmark_evidence_requires_machine_identity(tmp_path, payload, field):
    del payload["machine_info"][field]
    with pytest.raises(ValueError, match="machine_info"):
        _validate(tmp_path, payload)


@pytest.mark.parametrize("value", [None, "", "unknown", {}, 1])
def test_benchmark_evidence_requires_dataset_identity(tmp_path, payload, value):
    payload["bioetl_measurement"]["dataset"] = value
    with pytest.raises(ValueError, match="dataset identity"):
        _validate(tmp_path, payload)


@pytest.mark.parametrize("outcome", ["failure", "cancelled", "skipped", ""])
def test_benchmark_evidence_partial_producer_never_certifies_nonempty_json(
    tmp_path, payload, outcome
):
    path = tmp_path / "partial.json"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="producer did not succeed"):
        validate_evidence(path, _SHA, producer_outcome=outcome, root=tmp_path)


def test_benchmark_evidence_wrong_sha(tmp_path, payload):
    payload["commit_info"]["id"] = "b" * 40
    with pytest.raises(ValueError, match="Wrong SHA"):
        _validate(tmp_path, payload)


def test_benchmark_evidence_source_sha_mismatch(tmp_path, payload):
    payload["bioetl_source"]["revision"] = "b" * 40
    with pytest.raises(ValueError, match="source revision"):
        _validate(tmp_path, payload)


def test_benchmark_evidence_failed_benchmark(tmp_path, payload):
    payload["benchmarks"][0]["has_error"] = True
    with pytest.raises(ValueError, match="Failed benchmark"):
        _validate(tmp_path, payload)


def test_benchmark_evidence_duplicate_benchmark(tmp_path, payload):
    payload["benchmarks"] *= 2
    with pytest.raises(ValueError, match="Duplicate benchmark"):
        _validate(tmp_path, payload)


def test_benchmark_evidence_github_run_requires_real_run_identity(tmp_path, payload):
    payload["bioetl_measurement"]["environment"] = "github-actions"
    with pytest.raises(ValueError, match="GitHub run provenance"):
        _validate(tmp_path, payload, environ={"GITHUB_ACTIONS": "true"})
    manifest = _validate(
        tmp_path,
        payload,
        environ={
            "GITHUB_ACTIONS": "true",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_SERVER_URL": "https://github.com",
        },
    )
    assert (
        manifest["run_url"]
        == "https://github.com/owner/repo/actions/runs/123/attempts/2"
    )
    assert manifest["measured_run_id"] == _RUN
    assert manifest["run_id"] == "123"


def test_benchmark_evidence_cli_removes_stale_manifest_on_failure(tmp_path, payload):
    raw = tmp_path / "measurements.json"
    raw.write_text(json.dumps(payload))
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"status": "validated"}')
    assert (
        main(
            [
                "--output-root",
                str(tmp_path),
                "--measurements",
                str(raw),
                "--manifest-out",
                str(manifest),
                "--expected-sha",
                _SHA,
                "--producer-outcome",
                "failure",
            ]
        )
        == 1
    )
    assert not manifest.exists()
    assert json.loads(raw.read_text()) == payload


def test_benchmark_evidence_cli_rejects_escape_and_overwrite(tmp_path, payload):
    raw = tmp_path / "measurements.json"
    raw.write_text(json.dumps(payload))
    for output in (str(raw), "../escape.json"):
        assert (
            main(
                [
                    "--output-root",
                    str(tmp_path),
                    "--measurements",
                    str(raw),
                    "--manifest-out",
                    output,
                    "--expected-sha",
                    _SHA,
                    "--producer-outcome",
                    "success",
                ]
            )
            == 1
        )
        assert json.loads(raw.read_text()) == payload


def test_benchmark_evidence_router_validation_never_calls_reducer_or_hotspot(
    tmp_path, payload, monkeypatch
):
    from scripts.engineering.qa import __main__ as qa_router
    from scripts.engineering.qa import generate_hotspot_degradation_report as owner

    def forbidden(*args, **kwargs):
        pytest.fail("Independent validation called another performance command")

    monkeypatch.setattr(owner, "reduce_benchmark_evidence_main", forbidden)
    monkeypatch.setattr(owner, "hotspot_report_main", forbidden)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(payload))
    original = raw.read_bytes()
    manifest = tmp_path / "validation.json"
    assert (
        qa_router.main(
            [
                "validate-benchmark-evidence",
                "--output-root",
                str(tmp_path),
                "--measurements",
                str(raw),
                "--manifest-out",
                str(manifest),
                "--expected-sha",
                _SHA,
                "--producer-outcome",
                "success",
            ]
        )
        == 0
    )
    assert json.loads(manifest.read_text())["status"] == "validated"
    assert raw.read_bytes() == original
    assert sorted(path.name for path in tmp_path.iterdir()) == [
        "raw.json",
        "validation.json",
    ]


@pytest.mark.parametrize("github", [False, True])
def test_guard_producer_context_is_accepted_without_vcs_probe(
    tmp_path, payload, monkeypatch, github
):
    from datetime import UTC, datetime
    from tests.benchmarks import benchmark_vcs_guard as guard

    gitdir = tmp_path / ".git"
    gitdir.mkdir()
    (gitdir / "HEAD").write_text(_SHA + "\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BIOETL_BENCHMARK_CALLER", "schema-contract-test")
    monkeypatch.setenv("BIOETL_BENCHMARK_DATASET", "synthetic-schema-fixture-v1")
    monkeypatch.setattr(guard, "_RUN_ID", _RUN)
    monkeypatch.setattr(guard, "_started_at", None)
    monkeypatch.setattr(guard, "_clock_now", lambda: datetime(2026, 1, 1, tzinfo=UTC))
    monkeypatch.setattr(guard, "_INSTALLED_BEFORE_PLUGIN", True)
    monkeypatch.setattr(guard, "_BLOCKED_PROBES", [])
    env = (
        {
            "GITHUB_ACTIONS": "true",
            "GITHUB_RUN_ID": "123",
            "GITHUB_RUN_ATTEMPT": "1",
            "GITHUB_REPOSITORY": "test/repository",
            "GITHUB_SERVER_URL": "https://github.com",
        }
        if github
        else {}
    )
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    payload.pop("bioetl_measurement")
    guard.pytest_benchmark_update_json(None, [], payload)
    path = tmp_path / "schema-only.json"
    path.write_text(json.dumps(payload))
    assert (
        guard.validate_benchmark_measurement_json(path, search_from=tmp_path) == payload
    )
    manifest = validate_evidence(
        path, _SHA, producer_outcome="success", environ=env, root=tmp_path
    )
    assert manifest["dataset_identity"] == "synthetic-schema-fixture-v1"
    assert manifest["environment"] == ("github-actions" if github else "local")
    if not github:
        assert manifest["run_url"] is None


def test_guard_rejects_missing_dataset_instead_of_fabricating_identity(
    payload, monkeypatch
):
    from tests.benchmarks import benchmark_vcs_guard as guard

    monkeypatch.delenv("BIOETL_BENCHMARK_DATASET", raising=False)
    with pytest.raises(
        guard.BenchmarkMeasurementContractError, match="BIOETL_BENCHMARK_DATASET"
    ):
        guard.pytest_benchmark_update_json(None, [], payload)
