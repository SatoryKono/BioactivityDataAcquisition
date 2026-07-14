from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.engineering.qa import run_observability_closure_campaign as campaign


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
        return campaign.PhaseEvidence(
            name=name,
            command=command,
            started_at="2026-07-14T00:00:00+00:00",
            finished_at="2026-07-14T00:00:01+00:00",
            exit_code=0,
            timed_out=False,
            stdout_path="stdout.log",
            stdout_sha256="a" * 64,
            stderr_path="stderr.log",
            stderr_sha256="b" * 64,
        )

    monkeypatch.setattr(campaign, "_run_phase_command", fake_phase)


def _canonical_roots(tmp_path: Path) -> tuple[Path, Path]:
    data_root = tmp_path / "canonical" / "data"
    log_root = tmp_path / "canonical" / "logs"
    (data_root / "output" / "bronze").mkdir(parents=True)
    log_root.mkdir(parents=True)
    (data_root / "sentinel.txt").write_text("data", encoding="utf-8")
    (log_root / "sentinel.log").write_text("logs", encoding="utf-8")
    return data_root, log_root


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
            "pipeline": "chembl_activity",
            "tracing": bool(index),
            "status": "success",
            "data_signature": "same-data-signature",
            "decision_trace": [{"decision": "retain"}],
        }
    if key == "metric_reconciliation":
        return (
            {"status": "success", "expected": 1, "actual": 1}
            if kind == "prometheus-response"
            else {
                "events": [{"event_type": "run_finished"}],
                "expected": 1,
                "actual": 1,
            }
        )
    if key == "workflow_correlation":
        workflow_index = index % 2
        workflow_run_id = f"workflow-{workflow_index}"
        if kind == "workflow-result":
            return {
                "workflow_run_id": workflow_run_id,
                "status": "success" if workflow_index == 0 else "failed",
            }
        return {
            "workflow_run_id": workflow_run_id,
            "run_id": f"run-{index}",
            "manifest_id": f"manifest-{index}",
            "workflow_name": "chembl_baseline",
            "workflow_step_id": f"step-{index}",
            "terminal_event": ("run_finished" if workflow_index == 0 else "run_failed"),
        }
    if key == "metric_surface":
        return {
            "recording_rule_outputs": [f"bioetl_record_{item}" for item in range(103)],
            "recording_declarations_without_output": [],
            "recording_outputs_without_declaration": [],
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
                "bioetl_adapter_requests_total": 1,
                "bioetl_data_source_retries_total": 0,
                "bioetl_rate_limiter_tokens_available": 1,
                "bioetl_circuit_breaker_state": 0,
                "bioetl_adapter_request_duration_seconds": 0.1,
            },
        }
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


def _write_evidence_bundle(audit_root: Path, *, source_revision: str) -> list[str]:
    evidence_root = audit_root / "evidence"
    evidence_root.mkdir(parents=True)
    raw_root = evidence_root / "raw"
    raw_root.mkdir()
    args: list[str] = []
    for key, requirements in campaign.EVIDENCE_SUMMARY_REQUIREMENTS.items():
        path = evidence_root / f"{key}.json"
        payload = {
            "schema_version": 1,
            "evidence_type": key,
            "status": "pass",
            "source_revision": source_revision,
            "generated_at": "2026-07-14T00:00:00+00:00",
            "summary": dict(requirements),
            "producer": {
                "command": ["validated-producer", key],
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
    assert len(gate["artifacts"]) == 10


def test_raw_content_gate_rejects_fabricated_tracing_payloads(tmp_path: Path) -> None:
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

    assert "tracing attempt data signatures must be identical and non-empty" in errors
    assert "at least one tracing attempt requires a non-empty decision trace" in errors


def test_residual_findings_gate_requires_one_unique_real_issue_mapping() -> None:
    missing = campaign._residual_findings_gate(["renderer remains unstable"], [])
    valid = campaign._residual_findings_gate(
        ["renderer remains unstable"],
        [
            "RENDER-001=https://github.com/SatoryKono/"
            "BioactivityDataAcquisition/issues/7000"
        ],
    )

    assert missing["satisfied"] is False
    assert valid["satisfied"] is True
    assert valid["mappings"][0]["finding_id"] == "RENDER-001"


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
    assert "--run-type" in off and "incremental" in off
    assert "--use-cached-bronze" in off
    assert "--cached-bronze-path" in off
    assert "--no-tracing" in off
    assert "--tracing" in on


def test_execute_writes_complete_report_only_when_every_gate_is_satisfied(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    audit_root = tmp_path / "audit"
    data_root, log_root = _canonical_roots(tmp_path)
    revision = campaign._source_revision(campaign._repo_root())
    evidence_args = _write_evidence_bundle(audit_root, source_revision=revision)
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
            run_ids=(f"run-{pipeline}-{tracing}",),
            terminal_ledger_events=("run_finished",),
            manifest_artifacts=({"path": "manifest.json"},),
            ledger_artifacts=({"path": "ledger.jsonl"},),
            checkpoint_artifacts=({"path": "checkpoint.json"},),
            output_artifacts=({"path": "silver.delta", "sha256": "c" * 64},),
            result_signature=f"signature-{pipeline}",
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
            *evidence_args,
        ]
    )

    summary = json.loads(capsys.readouterr().out)
    report = json.loads(Path(summary["report"]).read_text(encoding="utf-8"))
    assert exit_code == 0
    assert summary["status"] == "complete"
    assert report["attempt_gate"]["actual_tracing_mode"] == "both"
    assert report["attempt_gate"]["attempt_count"] == 30
    assert report["attempt_gate"]["required_tracing_mode"] == "both"
    assert report["attempt_gate"]["tracing_result_parity"] is True
    assert report["attempt_gate"]["satisfied"] is True
    assert report["canonical_signature_gate"]["satisfied"] is True
    assert report["external_evidence_gate"]["satisfied"] is True


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
