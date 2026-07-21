from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import zstandard

from scripts.engineering.qa import run_observability_closure_campaign as campaign

pytestmark = pytest.mark.unit

_REAL_STAGE_WORKFLOW_FIXTURE = campaign._stage_workflow_fixture
_REAL_REGISTRY_PIPELINE_COMMAND = campaign._registry_pipeline_command


@pytest.fixture(autouse=True)
def _stub_registry_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "Available pipelines:\n" + "".join(
        f"  - {pipeline}\n" for pipeline in campaign.CHEMBL_PIPELINES
    )

    def fake_registry(
        _repo_root: Path, *, python: Path
    ) -> tuple[tuple[str, ...], subprocess.CompletedProcess[str]]:
        command = (str(python), "-m", "bioetl", "config", "list-pipelines")
        completed = subprocess.CompletedProcess(command, 0, stdout, "")
        return campaign.CHEMBL_PIPELINES, completed

    monkeypatch.setattr(campaign, "_registry_pipeline_command", fake_registry)

    def fake_phase(**kwargs: object) -> campaign.PhaseEvidence:
        name = str(kwargs["name"])
        command = tuple(str(item) for item in kwargs["command"])
        expected_outcome = str(kwargs.get("expected_outcome", "success"))
        phase_root = Path(str(kwargs["phase_root"]))
        phase_root.mkdir(parents=True, exist_ok=True)
        stdout_path = phase_root / "stdout.log"
        stderr_path = phase_root / "stderr.log"
        stdout_path.write_text("phase success", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        return campaign.PhaseEvidence(
            name=name,
            command=command,
            started_at="2026-07-14T00:00:00+00:00",
            finished_at="2026-07-14T00:00:01+00:00",
            exit_code=1 if expected_outcome == "failure" else 0,
            timed_out=False,
            stdout_path=str(stdout_path),
            stdout_sha256=campaign._sha256_file(stdout_path),
            stderr_path=str(stderr_path),
            stderr_sha256=campaign._sha256_file(stderr_path),
            expected_outcome=expected_outcome,
        )

    monkeypatch.setattr(campaign, "_run_phase_command", fake_phase)

    def fake_stage_fixture(
        *, canonical_bronze_root: Path, audit_root: Path
    ) -> tuple[Path, dict[str, object]]:
        _ = canonical_bronze_root
        root = audit_root / "fixtures" / "chembl-baseline"
        root.mkdir(parents=True, exist_ok=True)
        return root, {"records": []}

    monkeypatch.setattr(campaign, "_stage_workflow_fixture", fake_stage_fixture)


def _canonical_roots(tmp_path: Path) -> tuple[Path, Path]:
    data_root = tmp_path / "canonical" / "data"
    log_root = tmp_path / "canonical" / "logs"
    (data_root / "output" / "bronze").mkdir(parents=True)
    log_root.mkdir(parents=True)
    (data_root / "sentinel.txt").write_text("data", encoding="utf-8")
    (log_root / "sentinel.log").write_text("logs", encoding="utf-8")
    return data_root, log_root


def test_registry_discovery_binds_subprocess_to_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "checkout"
    (repo_root / "src").mkdir(parents=True)
    captured: dict[str, object] = {}

    def fake_run(
        command: tuple[str, ...], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        stdout = "Available pipelines:\n" + "".join(
            f"  - {pipeline}\n" for pipeline in campaign.CHEMBL_PIPELINES
        )
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(subprocess, "run", fake_run)

    names, _ = _REAL_REGISTRY_PIPELINE_COMMAND(repo_root, python=Path(sys.executable))

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONPATH"].split(os.pathsep)[:2] == [
        str((repo_root / "src").resolve()),
        str(repo_root.resolve()),
    ]
    assert names == campaign.CHEMBL_PIPELINES


def test_tree_signature_tracks_manifest_mutations_without_reading_payloads(
    tmp_path: Path,
) -> None:
    root = tmp_path / "canonical"
    root.mkdir()
    payload = root / "large.parquet"
    payload.write_bytes(b"before")
    before = campaign._tree_signature(root)

    previous_mtime = payload.stat().st_mtime_ns
    payload.write_bytes(b"after!")
    distinct_mtime = previous_mtime + 10_000_000_000
    os.utime(payload, ns=(distinct_mtime, distinct_mtime))

    assert payload.stat().st_mtime_ns != previous_mtime
    assert campaign._tree_signature(root) != before


def test_tree_signature_records_concurrently_removed_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "canonical"
    root.mkdir()
    payload = root / "ephemeral.parquet"
    payload.write_bytes(b"payload")
    original_lstat = Path.lstat

    def lstat_with_disappearance(path: Path) -> os.stat_result:
        if path == payload:
            raise FileNotFoundError(path)
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", lstat_with_disappearance)

    assert campaign._tree_signature(root)


def test_stage_workflow_fixture_selects_compatible_join_records(
    tmp_path: Path,
) -> None:
    bronze = tmp_path / "bronze"
    rows = {
        "assay": {
            "assay_chembl_id": "CHEMBL-A",
            "target_chembl_id": "CHEMBL-T",
            "document_chembl_id": "CHEMBL-D",
        },
        "target": {
            "target_chembl_id": "CHEMBL-T",
            "target_type": "SINGLE PROTEIN",
            "pref_name": "Human target",
            "organism": "Homo sapiens",
            "tax_id": 9606,
            "target_components": [
                {
                    "accession": "P12345",
                    "component_id": 1,
                    "component_type": "PROTEIN",
                }
            ],
        },
        "publication": {"document_chembl_id": "CHEMBL-D", "title": "Evidence"},
    }
    for entity, row in rows.items():
        path = bronze / "chembl" / entity / "2026-07-14" / "batch.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    fixture_root, evidence = _REAL_STAGE_WORKFLOW_FIXTURE(
        canonical_bronze_root=bronze,
        audit_root=tmp_path / "audit",
    )

    assert evidence["target_id"] == "CHEMBL-T"
    assert evidence["publication_id"] == "CHEMBL-D"
    assert len(evidence["records"]) == 3
    assert len(list(fixture_root.rglob("*.jsonl"))) == 3
    assert len(list(fixture_root.rglob("*.jsonl.zst"))) == 3


def test_stage_standalone_fixture_cache_covers_canonical_universe(
    tmp_path: Path,
) -> None:
    fixture_root, evidence = campaign._stage_standalone_fixture_cache(
        repo_root=Path.cwd(),
        audit_root=tmp_path / "audit",
    )

    records = evidence["records"]
    assert isinstance(records, list)
    assert {row["pipeline"] for row in records} == set(campaign.CHEMBL_PIPELINES)
    assert sum(
        row["source_kind"] == "recorded_provider_response" for row in records
    ) == len(campaign._RECORDED_SPECIAL_FIXTURES)
    assert len(list(fixture_root.rglob("*.jsonl"))) == 15
    assert len(list(fixture_root.rglob("*.jsonl.zst"))) == 15
    assert all(row["record_count"] >= 1 for row in records)


def test_dq_boundary_probe_avoids_global_conftest() -> None:
    command = campaign._dq_hard_failure_test_command(python=Path(sys.executable))

    assert "--noconftest" in command
    assert "addopts=" in command
    assert "timeout=0" in command


def test_stage_workflow_fixture_projects_disjoint_compressed_samples(
    tmp_path: Path,
) -> None:
    bronze = tmp_path / "bronze"
    rows = {
        "assay": {
            "assay_chembl_id": "CHEMBL-A",
            "target_chembl_id": "CHEMBL-OLD-T",
            "document_chembl_id": "CHEMBL-OLD-D",
        },
        "target": {
            "target_chembl_id": "CHEMBL-T",
            "target_type": "SINGLE PROTEIN",
            "pref_name": "Human target",
            "organism": "Homo sapiens",
            "tax_id": 9606,
            "target_components": [
                {
                    "accession": "P12345",
                    "component_id": 1,
                    "component_type": "PROTEIN",
                }
            ],
        },
        "publication": {"document_chembl_id": "CHEMBL-D", "title": "Evidence"},
    }
    compressor = zstandard.ZstdCompressor(level=3)
    for entity, row in rows.items():
        path = bronze / "chembl" / entity / "2026-07-14" / "batch.jsonl.zst"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(compressor.compress((json.dumps(row) + "\n").encode()))

    fixture_root, evidence = _REAL_STAGE_WORKFLOW_FIXTURE(
        canonical_bronze_root=bronze,
        audit_root=tmp_path / "audit",
    )

    assay = json.loads(
        next((fixture_root / "chembl" / "assay").rglob("*.jsonl")).read_text()
    )
    assay_evidence = next(
        row for row in evidence["records"] if row["entity"] == "assay"
    )
    assert assay["target_chembl_id"] == "CHEMBL-T"
    assert assay["document_chembl_id"] == "CHEMBL-D"
    assert assay_evidence["derivation"] == "deterministic_workflow_join_projection"
    assert assay_evidence["source_record_sha256"] != assay_evidence["record_sha256"]


def test_isolated_work_root_links_only_tracked_configs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    configs_root = repo_root / "configs"
    configs_root.mkdir(parents=True)
    work_root = tmp_path / "attempt"
    work_root.mkdir()

    campaign._ensure_tracked_runtime_links(
        work_root=work_root,
        repo_root=repo_root,
    )

    assert campaign._is_directory_link(work_root / "configs")
    assert (work_root / "configs").resolve() == configs_root.resolve()
    assert not (work_root / "data").exists()


def _retain_raw(path: Path, raw_bytes: bytes, kind: str) -> dict[str, str]:
    path.write_bytes(raw_bytes)
    return {
        "path": str(path),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "kind": kind,
    }


def _raw_payload(key: str, kind: str, index: int) -> dict[str, object]:
    if key == "tracing_parity":
        return {
            "pipeline": campaign.CHEMBL_PIPELINES[index // 2],
            "tracing": bool(index % 2),
            "status": "success",
            "run_id": (
                f"run-{campaign.CHEMBL_PIPELINES[index // 2]}-{bool(index % 2)}"
            ),
            "data_signature": f"signature-{campaign.CHEMBL_PIPELINES[index // 2]}",
            "decision_trace": [{"decision": "retain"}],
        }
    if key == "metric_reconciliation":
        pipeline = campaign.CHEMBL_PIPELINES[index]
        if kind == "prometheus-response":
            return {
                "status": "success",
                "pipeline": pipeline,
                "run_id": f"run-{pipeline}",
                "pipeline_runs_total_delta": 1,
                "health_probe_counter_delta": 0,
            }
        if kind == "ledger-snapshot":
            return {
                "pipeline": pipeline,
                "run_id": f"run-{pipeline}",
                "events": [{"event_type": "run_finished"}],
                "terminal_run_result_count": 1,
            }
        return {
            "source_present": True,
            "metric": "bioetl_dq_anomaly_detected",
            "delta": 1,
            "test_node_id": "tests/unit/dq/test_hard_failure.py::test_hard_failure",
        }
    if key == "workflow_correlation":
        workflow_index = index % 2
        workflow_run_id = f"workflow-{workflow_index}"
        if kind == "workflow-result":
            return {
                "workflow_run_id": workflow_run_id,
                "workflow_name": "chembl_baseline",
                "workflow_step_id": "extract",
                "child_run_id": f"run-{index}",
                "child_manifest_id": f"manifest-{index}",
                "status": "success" if workflow_index == 0 else "failed",
            }
        return {
            "workflow_run_id": workflow_run_id,
            "run_id": f"run-{index}",
            "manifest_id": f"manifest-{index}",
            "workflow_name": "chembl_baseline",
            "workflow_step_id": "extract",
            "terminal_event": ("run_finished" if workflow_index == 0 else "run_failed"),
        }
    if key == "metric_surface":
        return {
            "recording_rule_outputs": [f"bioetl_record_{item}" for item in range(103)],
            "policy_alias_metrics": [f"bioetl_alias_{item}" for item in range(20)],
            "typed_target_counts": {
                "promql": 171,
                "http": 30,
                "loki": 5,
                "tempo": 0,
                "unknown": 0,
            },
            "recording_declarations_without_output": [],
            "recording_outputs_without_declaration": [],
            "policy_aliases_without_catalog": [],
            "catalog_aliases_without_declaration": [],
            "policy_aliases_overlapping_outputs": [],
            "http_semantics_violations": [],
            "panel_contract_drift": [],
            "prometheus_run_id_selector_violations": [],
        }
    if key == "dashboard_variables":
        return {
            "dashboard_uid": f"dashboard-{index}",
            "pipelines": list(campaign.CHEMBL_PIPELINES),
        }
    if key == "zero_evidence":
        return {"source_present": True, "state": "present", "value": 0}
    if key == "scrape_targets":
        return {
            "target_id": f"target-{index}",
            "captured_at": "2026-07-14T00:00:00+00:00",
            "scrape_interval_elapsed": True,
            "raw_value": index,
            "expected_value": index,
        }
    if key == "promtool":
        return {
            "phase": (
                "check-observability",
                "check-control-plane",
                "test-fixtures",
            )[index],
            "tool_version": "3.13.1",
            "exit_code": 0,
            "output": "SUCCESS",
        }
    if key == "online_run" and kind == "online-run-result":
        return {
            "status": "success",
            "cached_mode": False,
            "terminal_event": "run_finished",
            "run_id": "online-run-1",
            "manifest_id": "online-manifest-1",
        }
    if key == "online_run":
        return {
            "raw_source_present": True,
            "metrics": {
                "bioetl_adapter_requests_total": {
                    "source_present": True,
                    "delta": 1,
                },
                "bioetl_data_source_retries_total": {
                    "source_present": True,
                    "delta": 1,
                },
                "bioetl_rate_limiter_wait_seconds_count": {
                    "source_present": True,
                    "delta": 1,
                },
                "bioetl_circuit_breaker_success_total": {
                    "source_present": True,
                    "delta": 1,
                },
                "bioetl_adapter_request_duration_seconds_count": {
                    "source_present": True,
                    "delta": 1,
                },
            },
        }
    if key == "backend_profile" and kind == "backend-http-response":
        return {
            "state": "populated",
            "read_only_mount": True,
            "data_root": "/audit/data",
            "record_count": 1,
        }
    if key == "backend_profile" and kind == "loki-response":
        return {
            "job": "bioetl-audit",
            "sentinel_match_count": 1,
            "read_only_mount": True,
            "log_root": "/audit/logs",
        }
    if key == "backend_profile":
        return {"before": {"data": "x"}, "after": {"data": "x"}, "unchanged": True}
    raise AssertionError(f"unsupported raw payload: {key}/{kind}")


def _write_valid_raw_artifacts(raw_root: Path, key: str) -> list[dict[str, str]]:
    retained: list[dict[str, str]] = []
    if key == "render_stability":
        screenshot_hashes: list[str] = []
        for index in range(16):
            raw_bytes = b"\x89PNG\r\n\x1a\n" + f"screenshot-{index}".encode()
            artifact = _retain_raw(
                raw_root / f"{key}--screenshot--{index}.png",
                raw_bytes,
                "screenshot",
            )
            retained.append(artifact)
            screenshot_hashes.append(artifact["sha256"])
        for index in range(16):
            payload = {
                "dashboard_uid": f"dashboard-{index // 2}",
                "render_index": index % 2 + 1,
                "stable_window_id": "stable-window-1",
                "status": "success",
                "screenshot_sha256": screenshot_hashes[index],
            }
            retained.append(
                _retain_raw(
                    raw_root / f"{key}--render-manifest--{index}.json",
                    json.dumps(payload).encode(),
                    "render-manifest",
                )
            )
        return retained
    for kind, minimum in campaign.EVIDENCE_RAW_KIND_REQUIREMENTS[key].items():
        for index in range(minimum):
            retained.append(
                _retain_raw(
                    raw_root / f"{key}--{kind}--{index}.json",
                    json.dumps(_raw_payload(key, kind, index)).encode(),
                    kind,
                )
            )
    return retained


def _write_evidence_bundle(
    audit_root: Path,
    *,
    source_revision: str,
    campaign_binding: dict[str, object] | None = None,
) -> list[str]:
    evidence_root = audit_root / "evidence"
    evidence_root.mkdir(parents=True, exist_ok=True)
    raw_root = evidence_root / "raw"
    raw_root.mkdir(exist_ok=True)
    args: list[str] = []
    for key, requirements in campaign.EVIDENCE_SUMMARY_REQUIREMENTS.items():
        path = evidence_root / f"{key}.json"
        payload = {
            "schema_version": 1,
            "evidence_type": key,
            "status": "pass",
            "source_revision": source_revision,
            "generated_at": "2026-07-14T00:00:00+00:00",
            **(
                {"campaign_binding": campaign_binding}
                if campaign_binding is not None
                else {}
            ),
            "summary": dict(requirements),
            "producer": {
                "command": [
                    sys.executable,
                    "-m",
                    campaign.CANONICAL_EVIDENCE_ASSEMBLER,
                    "--category",
                    key,
                    "--output",
                    str(path),
                ],
                "exit_code": 0,
                **({"tool_version": "3.13.1"} if key == "promtool" else {}),
            },
            "assertions": [
                {
                    "name": f"{key}-acceptance",
                    "expected": 0,
                    "actual": 0,
                    "status": "pass",
                }
            ],
            "raw_artifacts": _write_valid_raw_artifacts(raw_root, key),
        }
        path.write_text(json.dumps(payload), encoding="utf-8")
        args.extend(("--evidence", f"{key}={path}"))
    return args


def test_discovered_chembl_pipeline_universe_matches_closure_contract() -> None:
    repo_root = campaign._repo_root()
    assert campaign._discover_chembl_pipelines(repo_root) == campaign.CHEMBL_PIPELINES
    assert (
        campaign._discover_registered_chembl_pipelines(repo_root)
        == campaign.CHEMBL_PIPELINES
    )


def test_plan_mode_is_non_mutating_and_lists_both_tracing_modes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    audit_root = tmp_path / "audit"

    exit_code = campaign.main(
        ["--audit-root", str(audit_root), "--tracing-mode", "both"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "planned"
    assert len(payload["pipelines"]) == 15
    assert len(payload["attempts"]) == 30
    assert {item["tracing"] for item in payload["attempts"]} == {False, True}
    assert not audit_root.exists()


def test_execute_requires_both_canonical_signature_roots(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = campaign.main(["--audit-root", str(tmp_path / "audit"), "--execute"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert payload["status"] == "error"
    assert "requires --canonical-data-root and --canonical-log-root" in payload["error"]


def test_missing_canonical_root_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = campaign.main(
        [
            "--audit-root",
            str(tmp_path / "audit"),
            "--canonical-data-root",
            str(tmp_path / "missing-data"),
            "--canonical-log-root",
            str(tmp_path / "missing-logs"),
            "--execute",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert "canonical root must be an existing directory" in payload["error"]


def test_reused_audit_runtime_root_is_rejected(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_root, log_root = _canonical_roots(tmp_path)
    audit_root = tmp_path / "audit"
    (audit_root / "data").mkdir(parents=True)

    exit_code = campaign.main(
        [
            "--audit-root",
            str(audit_root),
            "--canonical-data-root",
            str(data_root),
            "--canonical-log-root",
            str(log_root),
            "--execute",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 2
    assert "retained runtime state" in payload["error"]


def test_external_evidence_gate_rejects_empty_or_reused_artifacts(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    evidence_root = audit_root / "evidence"
    evidence_root.mkdir(parents=True)
    empty = evidence_root / "empty.json"
    empty.write_text("{}", encoding="utf-8")
    evidence = {key: str(empty) for key in campaign.REQUIRED_EXTERNAL_EVIDENCE}

    gate = campaign._evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision="abc1234",
    )

    assert gate["satisfied"] is False
    assert "_paths" in gate["errors"]
    assert "schema_version must equal 1" in gate["errors"]["tracing_parity"]


def test_external_evidence_gate_accepts_typed_unique_current_artifacts(
    tmp_path: Path,
) -> None:
    audit_root = tmp_path / "audit"
    revision = "0123456789abcdef"
    args = _write_evidence_bundle(audit_root, source_revision=revision)
    evidence = campaign._parse_evidence(args[1::2])

    gate = campaign._evidence_gate(
        evidence,
        audit_root=audit_root,
        source_revision=revision,
    )

    assert gate["satisfied"] is True
    assert gate["errors"] == {}
    assert len(gate["artifacts"]) == 11


def test_metric_reconciliation_rejects_vacuous_and_misaligned_rows(
    tmp_path: Path,
) -> None:
    retained = _write_valid_raw_artifacts(tmp_path, "metric_reconciliation")
    prometheus_path = next(
        Path(row["path"]) for row in retained if row["kind"] == "prometheus-response"
    )
    payload = json.loads(prometheus_path.read_text(encoding="utf-8"))
    payload["pipeline_runs_total_delta"] = 0
    prometheus_path.write_text(json.dumps(payload), encoding="utf-8")

    errors = campaign._validate_metric_reconciliation_raw(retained)

    assert "each terminal run must increment pipeline_runs_total exactly once" in errors


def test_online_raw_requires_observed_instrumentation_deltas(tmp_path: Path) -> None:
    retained = _write_valid_raw_artifacts(tmp_path, "online_run")
    instrumentation_path = next(
        Path(row["path"])
        for row in retained
        if row["kind"] == "instrumentation-response"
    )
    payload = json.loads(instrumentation_path.read_text(encoding="utf-8"))
    payload["metrics"]["bioetl_data_source_retries_total"]["delta"] = 0
    instrumentation_path.write_text(json.dumps(payload), encoding="utf-8")

    errors = campaign._validate_online_raw(retained)

    assert (
        "controlled online retry probe must increment retry metric exactly once"
        in errors
    )


def test_raw_content_gate_rejects_incomplete_tracing_payloads(tmp_path: Path) -> None:
    retained: list[dict[str, str]] = []
    for index in range(2):
        path = tmp_path / f"attempt-{index}.json"
        raw_bytes = json.dumps(
            {
                "pipeline": "chembl_activity",
                "tracing": bool(index),
                "status": "success",
                "data_signature": f"different-{index}",
                "decision_trace": [],
            }
        ).encode()
        retained.append(_retain_raw(path, raw_bytes, "attempt-result"))

    errors = campaign._validate_raw_content("tracing_parity", retained)

    assert "tracing parity requires exactly 30 attempt results" in errors


def _workflow_raw_artifacts(
    tmp_path: Path,
    *,
    second_step_id: str = "extract",
    second_child_workflow_run_id: str = "workflow-1",
) -> list[dict[str, str]]:
    retained: list[dict[str, str]] = []
    for index, status in enumerate(("success", "failed")):
        workflow_run_id = f"workflow-{index}"
        step_id = "extract" if index == 0 else second_step_id
        parent = {
            "workflow_run_id": workflow_run_id,
            "workflow_name": "chembl_baseline",
            "workflow_step_id": step_id,
            "child_run_id": f"run-{index}",
            "child_manifest_id": f"manifest-{index}",
            "status": status,
        }
        child = {
            "workflow_run_id": (
                workflow_run_id if index == 0 else second_child_workflow_run_id
            ),
            "run_id": f"run-{index}",
            "manifest_id": f"manifest-{index}",
            "workflow_name": "chembl_baseline",
            "workflow_step_id": step_id,
            "terminal_event": "run_finished" if index == 0 else "run_failed",
        }
        for kind, payload in (("workflow-result", parent), ("child-result", child)):
            retained.append(
                _retain_raw(
                    tmp_path / f"{kind}-{index}.json",
                    json.dumps(payload).encode(),
                    kind,
                )
            )
    return retained


def test_workflow_raw_accepts_reciprocal_repeated_step_runs(tmp_path: Path) -> None:
    retained = _workflow_raw_artifacts(tmp_path)

    assert campaign._validate_workflow_raw(retained) == []


def test_workflow_raw_rejects_nonreciprocal_child_context(tmp_path: Path) -> None:
    retained = _workflow_raw_artifacts(
        tmp_path,
        second_child_workflow_run_id="workflow-wrong",
    )

    errors = campaign._validate_workflow_raw(retained)

    assert "parent/child workflow_run_id must match for reciprocal anchors" in errors


def test_workflow_raw_requires_repeated_runs_of_same_step(tmp_path: Path) -> None:
    retained = _workflow_raw_artifacts(tmp_path, second_step_id="publish")

    errors = campaign._validate_workflow_raw(retained)

    assert (
        "workflow raw evidence requires repeated success/failure runs for one step"
        in errors
    )


def test_residual_findings_gate_requires_resolution_before_completion() -> None:
    missing = campaign._residual_findings_gate(["renderer remains unstable"], [])
    valid = campaign._residual_findings_gate(
        ["renderer remains unstable"],
        [
            "RENDER-001=https://github.com/SatoryKono/"
            "BioactivityDataAcquisition/issues/6268"
        ],
    )

    assert missing["satisfied"] is False
    assert valid["satisfied"] is False
    assert valid["mappings"][0]["finding_id"] == "RENDER-001"
    assert "must be resolved" in valid["errors"][-1]


def test_attempt_closure_rejects_timeout_failure_and_ambiguous_identity() -> None:
    base = {
        "pipeline": "chembl_activity",
        "tracing": False,
        "started_at": "2026-07-14T00:00:00+00:00",
        "finished_at": "2026-07-14T00:00:01+00:00",
        "command": ("python",),
        "stdout_path": "stdout.log",
        "stderr_path": "stderr.log",
    }
    assert campaign.AttemptEvidence(
        **base,
        exit_code=0,
        timed_out=False,
        manifest_ids=("manifest-1",),
        run_ids=("run-1",),
        terminal_ledger_events=("run_finished",),
        manifest_artifacts=({"path": "manifest.json"},),
        ledger_artifacts=({"path": "ledger.jsonl"},),
        checkpoint_artifacts=({"path": "checkpoint.json"},),
        output_artifacts=({"path": "silver.delta", "sha256": "c" * 64},),
        semantic_output_records=1,
        result_signature="signature",
    ).satisfies_closure
    assert not campaign.AttemptEvidence(
        **base,
        exit_code=124,
        timed_out=True,
        manifest_ids=("manifest-1",),
        run_ids=("run-1",),
        terminal_ledger_events=("run_failed",),
    ).satisfies_closure
    assert not campaign.AttemptEvidence(
        **base,
        exit_code=0,
        timed_out=False,
        manifest_ids=("manifest-1", "manifest-2"),
        run_ids=("run-1",),
        terminal_ledger_events=("run_finished",),
    ).satisfies_closure


def test_attempt_closure_accepts_checkpoint_not_applicable_below_interval() -> None:
    disposition, interval = campaign._checkpoint_policy(
        campaign._repo_root(), "chembl_activity", 1
    )
    assert (disposition, interval) == ("not_applicable_below_interval", 1000)
    assert campaign.AttemptEvidence(
        pipeline="chembl_activity",
        tracing=False,
        started_at="2026-07-14T00:00:00+00:00",
        finished_at="2026-07-14T00:00:01+00:00",
        exit_code=0,
        timed_out=False,
        command=("python",),
        stdout_path="stdout.log",
        stderr_path="stderr.log",
        manifest_ids=("manifest-1",),
        run_ids=("run-1",),
        terminal_ledger_events=("run_finished",),
        manifest_artifacts=({"path": "manifest.json"},),
        ledger_artifacts=({"path": "ledger.jsonl"},),
        checkpoint_disposition=disposition,
        checkpoint_interval=interval,
        output_artifacts=({"path": "silver.parquet"},),
        semantic_output_records=1,
        result_signature="signature",
    ).satisfies_closure


def test_semantic_output_payload_ignores_occurrence_identity(tmp_path: Path) -> None:
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text(
        json.dumps(
            {
                "molecule_id": "CHEMBL1",
                "run_id": "run-a",
                "bronze_batch_id": "batch-a",
                "_valid_from": "2026-07-14T00:00:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    second.write_text(
        json.dumps(
            {
                "molecule_id": "CHEMBL1",
                "run_id": "run-b",
                "bronze_batch_id": "batch-b",
                "_valid_from": "2026-07-14T00:01:00Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    diagnostic = tmp_path / "dq-report.json"
    diagnostic.write_text(
        json.dumps({"execution_fingerprint": "occurrence-specific"}),
        encoding="utf-8",
    )

    first_payload, first_count = campaign._semantic_output_payload([first, diagnostic])
    second_payload, second_count = campaign._semantic_output_payload(
        [second, diagnostic]
    )

    assert first_count == second_count == 1
    assert first_payload == second_payload


def test_attempt_command_is_explicitly_incremental_online_and_traced() -> None:
    off = campaign._attempt_command(
        python=Path("/python"),
        pipeline="chembl_activity",
        limit=1,
        tracing=False,
        cached_bronze_root=Path("/cache"),
    )
    on = campaign._attempt_command(
        python=Path("/python"),
        pipeline="chembl_activity",
        limit=1,
        tracing=True,
        cached_bronze_root=Path("/cache"),
    )
    online = campaign._attempt_command(
        python=Path("/python"),
        pipeline="chembl_activity",
        limit=1,
        tracing=False,
        cached_bronze_root=None,
    )
    assert "--run-type" in off and "incremental" in off
    assert "--use-cached-bronze" in off
    assert "--cached-bronze-path" in off
    assert "--no-ensure-observability-backend" in off
    assert "--no-tracing" in off
    assert "--tracing" in on
    assert "--no-cached-bronze" in online
    profile_index = online.index("--required-persistence-profile")
    assert online[profile_index + 1] == "degraded_observable"


def test_execute_then_finalize_writes_complete_report_only_when_every_gate_is_satisfied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_root = tmp_path / "audit"
    data_root, log_root = _canonical_roots(tmp_path)
    revision = campaign._source_revision(campaign._repo_root())
    monkeypatch.setattr(
        campaign,
        "_source_provenance",
        lambda _repo_root: {
            "revision": revision,
            "tree": "tree-hash",
            "clean": True,
            "dirty_entries": (),
        },
    )

    def fake_attempt(**kwargs: object) -> campaign.AttemptEvidence:
        pipeline = str(kwargs["pipeline"])
        tracing = bool(kwargs["tracing"])
        run_mode = str(kwargs.get("run_mode", "standalone_cached"))
        run_id = "online-run-1" if run_mode == "online" else f"run-{pipeline}-{tracing}"
        artifact_root = (
            audit_root / "fake-artifacts" / f"{run_mode}-{pipeline}-{tracing}"
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        artifacts: dict[str, dict[str, str]] = {}
        for name in ("manifest", "ledger", "checkpoint", "output"):
            path = artifact_root / f"{name}.json"
            path.write_text(json.dumps({"name": name}), encoding="utf-8")
            artifacts[name] = {
                "path": str(path),
                "sha256": campaign._sha256_file(path),
            }
        return campaign.AttemptEvidence(
            pipeline=pipeline,
            tracing=tracing,
            started_at="2026-07-14T00:00:00+00:00",
            finished_at="2026-07-14T00:00:01+00:00",
            exit_code=0,
            timed_out=False,
            command=("python",),
            stdout_path="stdout.log",
            stderr_path="stderr.log",
            manifest_ids=(f"manifest-{pipeline}-{tracing}",),
            run_ids=(run_id,),
            terminal_ledger_events=("run_finished",),
            manifest_artifacts=(artifacts["manifest"],),
            ledger_artifacts=(artifacts["ledger"],),
            checkpoint_artifacts=(artifacts["checkpoint"],),
            output_artifacts=(artifacts["output"],),
            semantic_output_records=1,
            terminal_details={"adaptive_memory": {"decision_trace": [{"step": 1}]}},
            result_signature=f"signature-{pipeline}",
            run_mode=run_mode,
        )

    monkeypatch.setattr(campaign, "_run_attempt", fake_attempt)

    exit_code = campaign.main(
        [
            "--audit-root",
            str(audit_root),
            "--canonical-data-root",
            str(data_root),
            "--canonical-log-root",
            str(log_root),
            "--tracing-mode",
            "both",
            "--execute",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    report_path = Path(summary["report"])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert summary["status"] == "awaiting_external_evidence"
    assert report["attempt_gate"]["actual_tracing_mode"] == "both"
    assert report["attempt_gate"]["attempt_count"] == 30
    assert report["attempt_gate"]["required_tracing_mode"] == "both"
    assert report["attempt_gate"]["tracing_result_parity"] is True
    assert report["attempt_gate"]["satisfied"] is True
    assert report["canonical_signature_gate"]["satisfied"] is True
    assert report["external_evidence_gate"]["satisfied"] is False

    evidence_args = _write_evidence_bundle(
        audit_root,
        source_revision=revision,
        campaign_binding=report["campaign_binding"],
    )
    finalize_exit = campaign.main(
        [
            "--audit-root",
            str(audit_root),
            "--finalize-report",
            str(report_path),
            *evidence_args,
        ]
    )
    finalized_summary = json.loads(capsys.readouterr().out)
    finalized_report = json.loads(report_path.read_text(encoding="utf-8"))
    assert finalize_exit == 0
    assert finalized_summary["status"] == "complete"
    assert finalized_report["external_evidence_gate"]["satisfied"] is True
    assert finalized_report["retained_artifact_gate"]["satisfied"] is True


def test_execute_returns_nonzero_when_campaign_is_incomplete(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_root = tmp_path / "audit"
    data_root, log_root = _canonical_roots(tmp_path)
    revision = campaign._source_revision(campaign._repo_root())
    monkeypatch.setattr(
        campaign,
        "_source_provenance",
        lambda _repo_root: {
            "revision": revision,
            "tree": "tree-hash",
            "clean": True,
            "dirty_entries": (),
        },
    )

    def fake_failed_attempt(**kwargs: object) -> campaign.AttemptEvidence:
        pipeline = str(kwargs["pipeline"])
        tracing = bool(kwargs["tracing"])
        return campaign.AttemptEvidence(
            pipeline=pipeline,
            tracing=tracing,
            started_at="2026-07-14T00:00:00+00:00",
            finished_at="2026-07-14T00:00:01+00:00",
            exit_code=124,
            timed_out=True,
            command=("python",),
            stdout_path="stdout.log",
            stderr_path="stderr.log",
            manifest_ids=(),
            run_ids=(),
            terminal_ledger_events=(),
        )

    monkeypatch.setattr(campaign, "_run_attempt", fake_failed_attempt)

    exit_code = campaign.main(
        [
            "--audit-root",
            str(audit_root),
            "--canonical-data-root",
            str(data_root),
            "--canonical-log-root",
            str(log_root),
            "--tracing-mode",
            "off",
            "--execute",
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    report = json.loads(Path(summary["report"]).read_text(encoding="utf-8"))
    assert exit_code == 1
    assert summary["status"] == "incomplete"
    assert report["attempt_gate"]["satisfied"] is False
    assert report["external_evidence_gate"]["satisfied"] is False
