"""Targeted unit coverage boosts for CLI helper and diagnostics modules."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.control_plane.manifest.inspection_service import (
    RunManifestInspectionCorruptionError,
)
from bioetl.application.services.control_plane.workflow.inspection_service import (
    WorkflowInspectionResult,
)
from bioetl.application.services.workflow_runner_models import (
    WorkflowRunExecutionResult,
    WorkflowStepExecutionResult,
)
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.interfaces.cli.commands import _run_manifest_output as run_manifest_output
from bioetl.interfaces.cli.commands import _workflow_support as workflow_support
from bioetl.interfaces.cli.commands import config_dq
from bioetl.interfaces.cli.commands import lineage as lineage_cmd
from bioetl.interfaces.cli.commands import run_manifest as run_manifest_cmd
from bioetl.interfaces.cli.commands.domains.diagnostics import contract_checks
from bioetl.interfaces.cli.commands.domains.health import (
    observability_backend_process as backend_process,
)


pytestmark = pytest.mark.unit


def _make_workflow_config() -> WorkflowConfig:
    return WorkflowConfig(
        name="chembl_baseline",
        version="1.2.0",
        defaults=WorkflowRunOptionsConfig(),
        steps=(
            WorkflowStepConfig(
                step_id="extract",
                pipeline_name="chembl_activity",
            ),
            WorkflowStepConfig(
                step_id="publish",
                pipeline_name="chembl_activity_publish",
                depends_on=("extract",),
            ),
            TransformStepConfig(
                step_id="reconcile",
                transform_name="reconcile_foreign_keys",
                depends_on=("publish",),
                config={"action": "delete_orphans"},
            ),
        ),
    )


def test_load_metric_allowlist_supports_allowed_key_and_invalid_payloads(
    tmp_path: Path,
) -> None:
    allowlist = tmp_path / "allowlist.yaml"
    allowlist.write_text(
        "allowed:\n  registry: [metric_a, metric_b]\n", encoding="utf-8"
    )

    result = contract_checks._load_metric_allowlist(allowlist)

    assert result == {"registry": {"metric_a", "metric_b"}}

    invalid = tmp_path / "invalid.yaml"
    invalid.write_text("allowed: []\n", encoding="utf-8")
    assert contract_checks._load_metric_allowlist(invalid) == {}


def test_render_contract_check_report_includes_all_detail_sections() -> None:
    report = contract_checks.ObservabilityContractCheckReport(
        passed=False,
        checks=(
            contract_checks.ContractCheck(
                name="metric_inventory_drift",
                passed=False,
                details={"violations": {"registry": ["metric_a"]}},
            ),
            contract_checks.ContractCheck(
                name="slo_alert_contract",
                passed=False,
                details={"missing": ["AlertA"], "mismatches": ["AlertB:severity"]},
            ),
        ),
    )

    rendered = contract_checks.render_contract_check_report(report)

    assert "metric_inventory_drift: fail" in rendered
    assert "registry: ['metric_a']" in rendered
    assert "missing: ['AlertA']" in rendered
    assert "mismatches: ['AlertB:severity']" in rendered


def test_check_tracing_coverage_contract_reports_missing_and_forbidden_terms(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / "configs" / "quality").mkdir(parents=True)
    target_file = repo_root / "src" / "tracked.py"
    target_file.parent.mkdir(parents=True)
    target_file.write_text("emit_event('started')\nlegacy_term\n", encoding="utf-8")
    contract_path = (
        repo_root / "configs" / "quality" / "mandatory_tracing_coverage.yaml"
    )
    contract_path.write_text(
        """
surfaces:
  runtime:
    files:
      - path: src/tracked.py
        required_terms: [emit_event, span]
        forbidden_terms: [legacy_term]
      - path: src/missing.py
        required_terms: [emit_event]
""".strip(),
        encoding="utf-8",
    )

    result = contract_checks._check_tracing_coverage_contract(repo_root)

    assert result.passed is False
    assert "src/missing.py" in result.details["missing"]
    assert "src/tracked.py:missing:span" in result.details["mismatches"]
    assert "src/tracked.py:forbidden:legacy_term" in result.details["mismatches"]


def test_observability_contract_checks_cover_metric_and_alert_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import scripts.engineering.qa as engineering_qa

    metric_module = SimpleNamespace(
        collect_metric_inventory=lambda repo_root: {
            "registered_without_runtime": ["metric.a"],
            "runtime_without_registry": [],
        },
        validate_metric_inventory=lambda report, allowlist: {"registry": ["metric.a"]},
    )
    monkeypatch.setattr(
        engineering_qa,
        "report_observability_metric_inventory",
        metric_module,
        raising=False,
    )
    allowlist_path = tmp_path / "configs" / "quality"
    allowlist_path.mkdir(parents=True)
    (allowlist_path / "observability_metric_inventory_allowlist.yaml").write_text(
        "allowed: {}\n", encoding="utf-8"
    )

    metric_check = contract_checks._check_metric_inventory(tmp_path)
    assert metric_check.passed is False
    assert metric_check.details["violations"] == {"registry": ["metric.a"]}

    rules_path = tmp_path / "grafana" / "prometheus-rules"
    rules_path.mkdir(parents=True)
    config_path = tmp_path / "configs" / "quality"
    (rules_path / "bioetl_observability.yml").write_text(
        """
groups:
  - name: slo
    rules:
      - alert: AlertMissingMetric
        expr: up == 1
        for: 10m
        labels: {severity: critical}
        annotations: {runbook: wrong}
      - alert: OrphanAlert
        expr: bioetl_latency_seconds > 0
        for: 5m
        labels: {severity: warning}
        annotations: {runbook: orphan}
""".strip(),
        encoding="utf-8",
    )
    (config_path / "observability_slo_alert_contract.yaml").write_text(
        """
slo_contracts:
  replay:
    metrics: [bioetl_latency_seconds]
    alerts:
      - name: AlertMissingMetric
        severity: warning
        for: 5m
        runbook: expected
      - name: AlertNotPresent
        severity: critical
        for: 1m
        runbook: absent
""".strip(),
        encoding="utf-8",
    )

    alert_check = contract_checks._check_slo_alert_contract(tmp_path)
    assert alert_check.passed is False
    assert "AlertNotPresent" in alert_check.details["missing"]
    assert "AlertMissingMetric:severity" in alert_check.details["mismatches"]
    assert "AlertMissingMetric:for" in alert_check.details["mismatches"]
    assert "AlertMissingMetric:runbook" in alert_check.details["mismatches"]
    assert (
        "AlertMissingMetric:replay:metric_reference"
        in alert_check.details["mismatches"]
    )
    assert "OrphanAlert:orphan" in alert_check.details["mismatches"]


def test_contract_check_helpers_cover_invalid_structures_and_rule_maps(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "configs" / "quality"
    config_path.mkdir(parents=True)

    (config_path / "mandatory_tracing_coverage.yaml").write_text(
        "surfaces: []\n",
        encoding="utf-8",
    )
    invalid_surfaces = contract_checks._check_tracing_coverage_contract(tmp_path)
    assert invalid_surfaces.details["missing"] == ["surfaces"]

    (config_path / "mandatory_tracing_coverage.yaml").write_text(
        """
surfaces:
  runtime: []
  broken:
    files: invalid
  bad_entry:
    files:
      - invalid
      - {}
""".strip(),
        encoding="utf-8",
    )
    invalid_entries = contract_checks._check_tracing_coverage_contract(tmp_path)
    assert "runtime:invalid_surface" in invalid_entries.details["mismatches"]
    assert "broken:missing_files" in invalid_entries.details["mismatches"]
    assert "bad_entry:invalid_file_entry" in invalid_entries.details["mismatches"]
    assert "bad_entry:missing_path" in invalid_entries.details["mismatches"]

    yaml_path = tmp_path / "simple.yaml"
    yaml_path.write_text("- value\n", encoding="utf-8")
    assert contract_checks._load_yaml(yaml_path) == {}

    assert contract_checks._build_alert_rule_map({"groups": "invalid"}) == {}
    assert contract_checks._build_alert_rule_map(
        {
            "groups": [
                "bad",
                {"rules": ["bad", {"alert": "AlertA", "expr": "up"}]},
            ]
        }
    ) == {"AlertA": {"alert": "AlertA", "expr": "up"}}

    contract = {
        "slo_contracts": {
            "good": {
                "metrics": ["metric.a", 1],
                "alerts": [{"name": "AlertA", "severity": "warning"}],
            },
            "invalid": "bad",
            "missing_alerts": {"metrics": ["metric.b"], "alerts": "bad"},
        }
    }
    assert contract_checks._iter_slo_contract_alerts(contract) == [
        ("good", {"name": "AlertA", "severity": "warning"}, {"metric.a"})
    ]
    assert contract_checks._contract_alert_names(contract) == {"AlertA"}
    assert contract_checks._string_list(["a", 1, "b"]) == ["a", "b"]
    assert contract_checks._string_list("bad") == []


def test_parse_only_steps_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="must contain at least one step ID"):
        workflow_support.parse_only_steps(" , ")


def test_select_workflow_steps_includes_dependencies() -> None:
    config = _make_workflow_config()

    filtered = workflow_support.select_workflow_steps(config, "reconcile")

    assert tuple(step.step_id for step in filtered.steps) == (
        "extract",
        "publish",
        "reconcile",
    )


def test_select_workflow_steps_rejects_unknown_ids() -> None:
    with pytest.raises(ValueError, match="Unknown workflow step IDs"):
        workflow_support.select_workflow_steps(_make_workflow_config(), "missing")


def test_apply_cli_overrides_and_status_render_helpers_cover_branchy_paths() -> None:
    config = _make_workflow_config()
    unchanged = workflow_support.apply_cli_overrides(
        config,
        dry_run=False,
        run_type=None,
        start_offset=None,
        limit=None,
        input_csv=None,
        filter_column=None,
        filter_field=None,
        vacuum_after_run=None,
        vacuum_retention_days=None,
        log_level=None,
        ignore_yaml_filter=None,
        skip_gold=None,
        execution_context=None,
        use_cached_bronze=None,
        cached_bronze_path=None,
        cached_bronze_date=None,
        exact_replay=None,
        required_persistence_profile=None,
        replay_of_run_id=None,
        replay_of_manifest_id=None,
        enable_tracing=None,
        debug_export_enabled=None,
        debug_export_formats=(),
        debug_export_dir=None,
    )
    assert unchanged is config

    updated = workflow_support.apply_cli_overrides(
        config,
        dry_run=True,
        run_type="incremental",
        start_offset=5,
        limit=10,
        input_csv="input.csv",
        filter_column="id",
        filter_field="entity_id",
        vacuum_after_run=True,
        vacuum_retention_days=7,
        log_level="DEBUG",
        ignore_yaml_filter=True,
        skip_gold=True,
        execution_context="cli",
        use_cached_bronze=True,
        cached_bronze_path="/tmp/bronze",
        cached_bronze_date="2026-01-01",
        exact_replay=True,
        required_persistence_profile="exact",
        replay_of_run_id="run-1",
        replay_of_manifest_id="manifest-1",
        enable_tracing=True,
        debug_export_enabled=True,
        debug_export_formats=("json",),
        debug_export_dir="/tmp/debug",
    )
    assert updated.defaults.dry_run is True
    assert updated.steps[0].run_options.limit == 10

    no_history = workflow_support.build_status_payload(
        config,
        only_steps=None,
        inspection=None,
    )
    assert no_history["execution_history_available"] is False
    assert workflow_support._render_history_lines(no_history) == [
        "history: unavailable"
    ]
    assert workflow_support._render_status_steps("invalid") == []
    rendered_step = workflow_support._render_status_step(
        {
            "step_id": "reconcile",
            "kind": "transform",
            "transform_name": "reconcile_foreign_keys",
            "depends_on": ["publish"],
        }
    )
    assert (
        "- reconcile [transform] transform=reconcile_foreign_keys depends_on=publish"
        in rendered_step
    )


def test_build_status_payload_with_history_uses_inspection_snapshot() -> None:
    inspection = WorkflowInspectionResult(
        workflow_name="chembl_baseline",
        workflow_run_id="workflow-run-1",
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        status="failed",
        workflow_version="1.2.0",
        selected_step_ids=("publish",),
        repair_required=True,
        repair_hint="resume from last persisted step",
        ambiguous_step_ids=("publish",),
        last_error_type="RuntimeError",
        last_error_message="boom",
        ledger_entry_count=7,
        step_states=(
            {
                "step_id": "publish",
                "step_kind": "pipeline",
                "status": "failed",
            },
        ),
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
        completed_at=None,
    )

    payload = workflow_support.build_status_payload(
        _make_workflow_config(),
        only_steps="publish",
        inspection=inspection,
    )

    assert payload["execution_history_available"] is True
    assert payload["repair_required"] is True
    assert payload["ambiguous_step_ids"] == ["publish"]
    assert payload["selected_step_filter"] == ["publish"]


def test_render_status_payload_and_run_result_cover_error_and_dry_run_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "workflow": "chembl_baseline",
        "version": "1.2.0",
        "topological_step_ids": ["extract", "publish"],
        "execution_history_available": True,
        "status": "failed",
        "workflow_run_id": "workflow-run-1",
        "manifest_id": "manifest-1",
        "execution_fingerprint": "fingerprint-1",
        "ledger_entry_count": 3,
        "repair_required": True,
        "repair_hint": "resume",
        "last_error_type": "RuntimeError",
        "last_error_message": "boom",
        "steps": [
            {
                "step_id": "extract",
                "kind": "pipeline",
                "pipeline_name": "chembl_activity",
                "depends_on": [],
            },
            {
                "step_id": "reconcile",
                "kind": "unknown",
                "status": "failed",
                "error_type": "ValueError",
                "error_message": "bad data",
            },
        ],
        "note": "rendered from history",
    }

    rendered = workflow_support.render_status_payload(payload)

    assert "repair_required: yes" in rendered
    assert "last_error: RuntimeError / boom" in rendered
    assert "- extract [pipeline] pipeline=chembl_activity depends_on=-" in rendered
    assert "- reconcile [unknown] -> failed (ValueError: bad data)" in rendered

    lines: list[str] = []
    monkeypatch.setattr(workflow_support, "echo_info", lines.append)
    result = WorkflowRunExecutionResult(
        workflow_name="chembl_baseline",
        status="completed",
        workflow_run_id="workflow-run-1",
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        resumed=True,
        steps=(
            WorkflowStepExecutionResult(
                step_id="reconcile",
                step_kind="transform",
                status="completed",
                payload=SimpleNamespace(output={"dry_run": True, "would_mutate": True}),
            ),
        ),
    )

    workflow_support.render_run_result(
        _make_workflow_config(),
        result,
        dry_run=True,
        only_steps="reconcile",
        resume_last=True,
    )

    assert any("Execution mode: resumed" in line for line in lines)
    assert any("dry-run blocked destructive mutation" in line for line in lines)


def test_run_manifest_output_renders_cross_surface_diff_and_fallback_json() -> None:
    payload = {
        "left_manifest_id": "manifest-left",
        "right_manifest_id": "manifest-right",
        "classification": "semantic_change",
        "semantic_equivalent": False,
        "occurrence_only": False,
        "replay_relationship": "independent",
        "cross_surface_replay_diff": {
            "verdict": "mismatch",
            "effective_config": {"semantic_equivalent": False},
            "checkpoint_anchors": {
                "compatible": False,
                "mismatched_fields": ["effective_config_hash"],
            },
            "lineage": {"planned_artifacts_match": True},
        },
        "differences": [{"field": "contract_ref", "left": "a", "right": "b"}],
    }

    rendered = run_manifest_output.render_diff_payload(payload)

    assert "cross_surface_replay_diff:" in rendered
    assert "mismatched_fields:" in rendered
    assert "- field: contract_ref" in rendered

    fallback = run_manifest_output.render_show_payload({"manifest": "not-a-dict"})
    assert json.loads(fallback)["manifest"] == "not-a-dict"

    mixed = run_manifest_output.render_show_payload(
        {
            "manifest": {"manifest_id": "manifest-1", "run_id": "run-1"},
            "ledger_entries": "bad",
            "diagnostics": [],
            "identity_graph": [],
        }
    )
    assert "manifest_id: manifest-1" in mixed


def test_run_manifest_output_renderers_cover_verify_forensic_and_score_paths() -> None:
    verify = run_manifest_output.render_verify_payload(
        {
            "left_manifest_id": "left",
            "right_manifest_id": "right",
            "left_run_id": "run-left",
            "right_run_id": "run-right",
            "verdict": "match",
            "verified": True,
            "semantic_equivalent": True,
            "occurrence_only": False,
            "missing_evidence": ["none"],
            "effective_config": {"same": True},
            "left_authoritative_replay_dossier": {"manifest_id": "left"},
            "right_authoritative_replay_dossier": {"manifest_id": "right"},
        }
    )
    assert "Run Manifest Verification" in verify
    assert "missing_evidence:" in verify

    forensic = run_manifest_output.render_forensic_diff_payload(
        {
            "left_manifest_id": "left",
            "right_manifest_id": "right",
            "classification": "same",
            "semantic_equivalent": True,
            "occurrence_only": False,
            "replay_relationship": "identical",
            "replay_capability": {"capable": True},
            "checkpoint_compatibility": {"ok": True},
            "artifact_byte_equivalence": {"match": True},
            "artifact_completeness": {"complete": True},
            "lineage_closure": {"closed": True},
            "missing_evidence": [],
        }
    )
    assert "Forensic Run Diff" in forensic
    assert "lineage_closure:" in forensic

    assert run_manifest_output.render_score_payload({"other": True}).startswith("{")
    score = run_manifest_output.render_score_payload(
        {
            "identifier": "manifest-1",
            "manifest_id": "manifest-1",
            "run_id": "run-1",
            "reproducibility_audit_score": {
                "overall_score": 9.1,
                "score_scope": "run",
                "required_profile": "exact",
                "thresholds_satisfied": True,
                "supported_boundary_verdict": {
                    "verdict": "pass",
                    "supported_boundary_satisfied": True,
                    "reason": "ok",
                    "exact_replay_support_boundary": "gold",
                },
                "historical_replay_universe_exact_replay_claim": {
                    "claimed": True,
                    "verdict": "pass",
                    "reason": "ok",
                    "governed_full_corpus_gate": {
                        "satisfied": True,
                        "verdict": "pass",
                        "reason": "ok",
                    },
                },
                "executable_run_contract_claim": {
                    "claimed": True,
                    "verdict": "pass",
                    "reason": "ok",
                },
            },
            "authoritative_replay_dossier": {
                "manifest_id": "manifest-1",
                "execution_fingerprint": "fp-1",
                "effective_config_artifact_id": "cfg-1",
                "input_snapshot_identity_fingerprint": "snap-1",
            },
        }
    )
    assert "Run Manifest Score" in score
    assert "governed_full_corpus_gate:" in score
    assert "authoritative_replay_dossier:" in score


def test_lineage_text_renderers_cover_non_dict_nodes_and_identifier_resolution() -> (
    None
):
    assert lineage_cmd._render_node_lines(["node-a"]) == ["  - node-a"]
    assert lineage_cmd._render_relation_lines(["relation-a"]) == ["  - relation-a"]
    assert (
        lineage_cmd._resolve_explain_identifier(run_id=None, manifest_id=None) is None
    )
    assert (
        lineage_cmd._resolve_explain_identifier(run_id="run-1", manifest_id=None)
        == "run-1"
    )


def test_lineage_text_renderers_cover_structured_payloads_and_command_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rendered_fragment = lineage_cmd._render_fragment_payload(
        {
            "fragment": {
                "fragment_id": "fragment-1",
                "stored_fragment_id": "occurrence-1",
                "run_id": "run-1",
                "manifest_id": "manifest-1",
                "created_at": "2026-01-01T00:00:00Z",
                "nodes": [
                    {"node_type": "dataset", "node_id": "silver:chembl.activity"}
                ],
                "edges": [],
            }
        }
    )
    assert "Lineage Fragment" in rendered_fragment
    assert "dataset: silver:chembl.activity" in rendered_fragment

    rendered_trace = lineage_cmd._render_trace_payload(
        {
            "dataset_ref": "silver:chembl.activity",
            "fragment_ids": ["fragment-1"],
            "stored_fragment_ids": ["occurrence-1"],
            "upstream": [
                {
                    "edge_type": "derived_from",
                    "fragment_id": "fragment-1",
                    "stored_fragment_id": "occurrence-1",
                    "node": {"node_id": "bronze:batch-1", "label": "bronze"},
                }
            ],
            "downstream": [],
        }
    )
    assert "Lineage Trace" in rendered_trace
    assert (
        "derived_from via fragment-1 occurrence=occurrence-1: bronze:batch-1 label=bronze"
        in rendered_trace
    )

    rendered_explain = lineage_cmd._render_explain_payload(
        {
            "identifier": "manifest-1",
            "run_id": "run-1",
            "manifest_id": "manifest-1",
            "fragment_ids": ["fragment-1"],
            "stored_fragment_ids": ["occurrence-1"],
            "produced_datasets": [
                {"node_type": "dataset", "node_id": "silver:chembl.activity"}
            ],
            "produced_bronze_batches": [],
            "transforms": [],
            "source_systems": [],
            "source_requests": [],
        }
    )
    assert "Lineage Run" in rendered_explain
    assert "Produced Bronze Batches" in rendered_explain
    assert lineage_cmd._render_text_payload({"other": True}).startswith("{")

    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        lineage_cmd, "echo_error", lambda title, detail: errors.append((title, detail))
    )
    monkeypatch.setattr(
        lineage_cmd,
        "get_lineage_service",
        lambda: SimpleNamespace(
            show_fragment=lambda fragment_id, semantic=False: (_ for _ in ()).throw(
                ValueError("missing fragment")
            ),
            trace=lambda dataset_ref: (_ for _ in ()).throw(
                ValueError("missing trace")
            ),
            explain_run=lambda identifier: (_ for _ in ()).throw(
                ValueError("missing run")
            ),
        ),
    )

    lineage_cmd.show_fragment_command.callback("fragment-1", False, "json")
    lineage_cmd.trace_command.callback("silver:missing", "json")
    lineage_cmd.explain_command.callback("run-1", None, "json")
    with pytest.raises(SystemExit):
        lineage_cmd.explain_command.callback("run-1", "manifest-1", "json")

    assert ("Lineage fragment not found", "missing fragment") in errors
    assert ("Lineage trace not found", "missing trace") in errors
    assert ("Lineage run explanation not found", "missing run") in errors


@pytest.mark.skipif(
    sys.platform != "win32", reason="Windows-specific backend process test"
)
def test_backend_process_helpers_cover_env_kwargs_and_argument_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=1)
    fake_subprocess = SimpleNamespace(
        DEVNULL=object(),
        DETACHED_PROCESS=0x1,
        CREATE_NEW_PROCESS_GROUP=0x2,
        CREATE_NO_WINDOW=0x4,
        STARTF_USESHOWWINDOW=0x8,
        SW_HIDE=0,
        STARTUPINFO=lambda: startupinfo,
    )

    kwargs = backend_process._build_detached_backend_popen_kwargs(
        os_name="nt",
        subprocess_module=fake_subprocess,
    )
    assert kwargs["creationflags"] == 0x1 | 0x2 | 0x4
    assert kwargs["startupinfo"] is startupinfo

    env = backend_process._build_detached_backend_env(
        current_env={"PYTHONPATH": "existing"}
    )
    assert env["PYTHONPATH"].endswith("existing")
    assert str(Path(backend_process.__file__).resolve().parents[6]) in env["PYTHONPATH"]

    monkeypatch.setattr(
        backend_process,
        "_find_listening_backend_pids_by_port",
        lambda port: state["pids"] if port == 8080 else (),
    )
    state = {"pids": (111, 222)}
    calls: list[tuple[int, int]] = []
    monkeypatch.setattr(
        backend_process.os,
        "kill",
        lambda pid, sig: (calls.append((pid, sig)), state.update({"pids": ()})),
    )

    assert backend_process.drop_listening_backend_on_port(8080, sleep_fn=lambda _: None)
    assert calls
    assert backend_process.python_executable_to_tuple(["python", "-m", "bioetl"]) == (
        "python",
        "-m",
        "bioetl",
    )
    assert backend_process.python_executable_to_tuple("python") == ("python",)


@pytest.mark.skipif(
    sys.platform == "win32", reason="PosixPath not available on Windows"
)
def test_backend_process_helpers_cover_listener_parsing_and_detached_start(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    original_find_pids = backend_process._find_listening_backend_pids_by_port
    fake_result = SimpleNamespace(
        stdout="\n".join(
            [
                'LISTEN 0 128 127.0.0.1:9090 users:(("python",pid=123,fd=4))',
                'LISTEN 0 128 127.0.0.1:9090 users:(("python",pid=bad,fd=4))',
            ]
        )
    )
    monkeypatch.setattr(
        backend_process.subprocess,
        "run",
        lambda *args, **kwargs: fake_result,
    )
    monkeypatch.setattr(backend_process.os, "name", "posix")
    assert backend_process._find_listening_backend_pids_by_port(9090) == (123,)
    assert backend_process._find_listening_backend_pid_by_port(9090) == 123

    startupinfo = SimpleNamespace(dwFlags=0, wShowWindow=1)
    fake_subprocess = SimpleNamespace(
        DEVNULL=object(),
        DETACHED_PROCESS=0x1,
        CREATE_NEW_PROCESS_GROUP=0x2,
        CREATE_NO_WINDOW=0x4,
        STARTUPINFO=lambda: startupinfo,
        STARTF_USESHOWWINDOW=0x0,
    )
    assert (
        backend_process._build_detached_backend_popen_kwargs(
            os_name="posix",
            subprocess_module=fake_subprocess,
        )["start_new_session"]
        is True
    )
    assert (
        backend_process._build_detached_backend_popen_kwargs(
            os_name="nt",
            subprocess_module=fake_subprocess,
        )["startupinfo"]
        is startupinfo
    )

    state = {"pids": (111,)}
    monkeypatch.setattr(
        backend_process,
        "_find_listening_backend_pids_by_port",
        lambda port: state["pids"],
    )
    monkeypatch.setattr(
        backend_process.os,
        "kill",
        lambda pid, sig: (_ for _ in ()).throw(OSError("busy")),
    )
    assert (
        backend_process.drop_listening_backend_on_port(8080, sleep_fn=lambda _: None)
        is False
    )

    captured: dict[str, object] = {}
    log_path = tmp_path / "backend.log"
    monkeypatch.setattr(
        backend_process, "build_detached_backend_log_path", lambda port: log_path
    )
    monkeypatch.setattr(
        backend_process,
        "_build_detached_backend_popen_kwargs",
        lambda: {"stdout": "drop", "stderr": "drop"},
    )
    monkeypatch.setattr(
        backend_process,
        "_build_detached_backend_env",
        lambda: {"PYTHONPATH": "src"},
    )

    def _fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return "process-sentinel"

    result = backend_process.start_detached_quarantine_backend(
        bind_host="127.0.0.1",
        port=7777,
        python_executable="python-custom",
        popen_factory=_fake_popen,
    )

    assert result == "process-sentinel"
    assert captured["command"][:4] == [
        "python-custom",
        "-m",
        "bioetl",
        "quarantine",
    ]
    assert captured["kwargs"]["env"] == {"PYTHONPATH": "src"}
    assert log_path.exists()

    monkeypatch.setattr(
        backend_process,
        "_find_listening_backend_pids_by_port",
        original_find_pids,
    )
    windows_result = SimpleNamespace(
        stdout="\n".join(
            [
                "TCP 127.0.0.1:8080 0.0.0.0:0 LISTENING 321",
                "TCP 127.0.0.1:8080 0.0.0.0:0 LISTENING bad",
            ]
        )
    )
    import os as os_module
    import subprocess as subprocess_module

    monkeypatch.setattr(
        subprocess_module, "run", lambda *args, **kwargs: windows_result
    )
    monkeypatch.setattr(os_module, "name", "nt")
    monkeypatch.setattr(
        backend_process, "_resolve_system_executable", lambda x: "netstat"
    )
    assert backend_process._find_listening_backend_pids_by_port(8080) == (321,)


def test_config_dq_command_helpers_cover_error_and_compatibility_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        config_dq, "echo_info", lambda *args: messages.append(("info", args))
    )
    monkeypatch.setattr(
        config_dq, "echo_error", lambda *args: messages.append(("error", args))
    )

    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("- not-a-mapping\n", encoding="utf-8")
    service = MagicMock()
    monkeypatch.setattr(config_dq, "get_config_service", lambda: service)

    config_dq.validate_dq_config_command.callback(
        "chembl_activity", str(invalid_config)
    )
    assert any(
        "Config file must contain a mapping" in str(args[-1]) for _, args in messages
    )

    messages.clear()
    artifact1 = tmp_path / "artifact1.json"
    artifact2 = tmp_path / "artifact2.json"
    artifact1.write_text('["invalid"]', encoding="utf-8")
    artifact2.write_text("{}", encoding="utf-8")
    config_dq.check_compatibility_command.callback(str(artifact1), str(artifact2))
    assert any(
        "Artifacts must be JSON objects" in str(args[-1]) for _, args in messages
    )

    messages.clear()
    artifact1.write_text(
        json.dumps(
            {
                "artifact_id": "a1",
                "dq_contract_compatibility_hash": "same",
                "effective_config_hash": "same",
            }
        ),
        encoding="utf-8",
    )
    artifact2.write_text(
        json.dumps(
            {
                "artifact_id": "a2",
                "dq_contract_compatibility_hash": "same",
                "effective_config_hash": "same",
            }
        ),
        encoding="utf-8",
    )
    service.check_config_compatibility.return_value = True

    config_dq.check_compatibility_command.callback(str(artifact1), str(artifact2))

    assert any(
        "[OK] Configurations are compatible" in str(args[0]) for _, args in messages
    )


def test_config_dq_helpers_cover_lazy_import_and_error_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        config_dq, "echo_info", lambda *args: messages.append(("info", args))
    )
    monkeypatch.setattr(
        config_dq, "echo_error", lambda *args: messages.append(("error", args))
    )

    api_module = SimpleNamespace(get_config_service=lambda: "config-service")
    monkeypatch.setitem(
        __import__("sys").modules,
        "bioetl.composition.control_plane_service_access",
        api_module,
    )
    assert config_dq.get_config_service() == "config-service"

    service = MagicMock()
    monkeypatch.setattr(config_dq, "get_config_service", lambda: service)
    service.get_dq_config.side_effect = FileNotFoundError("missing dq")
    config_dq.show_dq_config_command.callback("chembl_activity", "yaml")
    assert any(
        kind == "error" and args[0] == "DQ Config file not found"
        for kind, args in messages
    )

    messages.clear()
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text(":\n", encoding="utf-8")
    config_dq.validate_dq_config_command.callback("chembl_activity", str(bad_yaml))
    assert any(
        kind == "error" and args[0] == "DQ Configuration validation failed"
        for kind, args in messages
    )

    messages.clear()
    service.get_dq_config.side_effect = ValueError("invalid dq")
    config_dq.validate_dq_config_command.callback("chembl_activity", None)
    assert any(
        kind == "error" and args[0] == "DQ Configuration invalid"
        for kind, args in messages
    )

    messages.clear()
    service.get_effective_config_artifact.side_effect = ValueError("bad effective")
    config_dq.show_effective_config_command.callback(
        "chembl_activity", "json", ("bad",)
    )
    assert any(
        kind == "error" and args[0] == "Effective config error"
        for kind, args in messages
    )

    messages.clear()
    service.get_effective_config_artifact.side_effect = FileNotFoundError("missing cfg")
    config_dq.show_effective_config_command.callback("chembl_activity", "yaml", ())
    assert any(
        kind == "error" and args[0] == "Config file not found"
        for kind, args in messages
    )

    messages.clear()
    service.get_effective_config_artifact.side_effect = TypeError("artifact failed")
    config_dq.show_effective_config_command.callback(
        "chembl_activity", "yaml", ("k=v",)
    )
    assert any(
        kind == "error" and args[0] == "Failed to create effective config artifact"
        for kind, args in messages
    )

    messages.clear()
    missing_file = tmp_path / "missing.json"
    config_dq.check_compatibility_command.callback(str(missing_file), str(missing_file))
    assert any(
        kind == "error" and args[0] == "Artifact file not found"
        for kind, args in messages
    )

    messages.clear()
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{bad", encoding="utf-8")
    config_dq.check_compatibility_command.callback(str(invalid_json), str(invalid_json))
    assert any(
        kind == "error" and args[0] == "Invalid JSON in artifact file"
        for kind, args in messages
    )

    messages.clear()
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}", encoding="utf-8")
    service.check_config_compatibility.side_effect = ValueError("compat failure")
    config_dq.check_compatibility_command.callback(str(artifact), str(artifact))
    assert any(
        kind == "error" and args[0] == "Compatibility check failed"
        for kind, args in messages
    )


def test_config_dq_helpers_cover_success_and_incompatible_branches(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        config_dq, "echo_info", lambda *args: messages.append(("info", args))
    )
    monkeypatch.setattr(
        config_dq, "echo_error", lambda *args: messages.append(("error", args))
    )
    service = MagicMock()
    monkeypatch.setattr(config_dq, "get_config_service", lambda: service)

    service.get_dq_config.return_value = {
        "contract_ref": "chembl_activity_dq",
        "contract_version": "1.0",
        "rule_bundle_version": "2026.06",
        "default_disposition_policy": "quarantine",
        "strictness_mode": "strict",
    }
    config_dq.show_dq_config_command.callback("chembl_activity", "json")
    config_dq.validate_dq_config_command.callback("chembl_activity", None)
    assert any(
        '"contract_ref": "chembl_activity_dq"' in str(args[0]) for _, args in messages
    )
    assert any(
        "Contract Ref: chembl_activity_dq" in str(args[0]) for _, args in messages
    )

    messages.clear()
    config_file = tmp_path / "dq.yaml"
    config_file.write_text("contract_ref: chembl_activity_dq\n", encoding="utf-8")
    service.validate_dq_config.return_value = True
    config_dq.validate_dq_config_command.callback("chembl_activity", str(config_file))
    assert any("[OK] DQ configuration is valid" in str(args[0]) for _, args in messages)

    messages.clear()
    service.validate_dq_config.return_value = False
    config_dq.validate_dq_config_command.callback("chembl_activity", str(config_file))
    assert any(
        "[ERROR] DQ configuration is invalid" in str(args[0]) for _, args in messages
    )

    messages.clear()
    artifact1 = tmp_path / "artifact1.json"
    artifact2 = tmp_path / "artifact2.json"
    artifact1.write_text(json.dumps({"artifact_id": "a1"}), encoding="utf-8")
    artifact2.write_text(json.dumps({"artifact_id": "a2"}), encoding="utf-8")
    service.check_config_compatibility.return_value = False
    config_dq.check_compatibility_command.callback(str(artifact1), str(artifact2))
    assert any("NOT compatible" in str(args[0]) for _, args in messages)


def test_run_manifest_commands_cover_error_and_persisted_artifact_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    emitted: list[tuple[dict[str, object], str]] = []
    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        run_manifest_cmd,
        "_emit_payload",
        lambda payload, fmt: emitted.append((payload, fmt)),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "echo_error",
        lambda title, detail: errors.append((title, detail)),
    )

    manifest_result = SimpleNamespace(
        manifest=SimpleNamespace(manifest_id="manifest-1", run_id="run-1"),
        diagnostics={
            "reproducibility_audit_score": {"overall_score": 9.1},
            "authoritative_replay_dossier": {"manifest_id": "manifest-1"},
        },
        to_dict=lambda: {"manifest": {"manifest_id": "manifest-1"}},
    )
    diff_result = SimpleNamespace(to_dict=lambda: {"differences": []})
    service = SimpleNamespace(
        show=lambda identifier: manifest_result,
        diff=lambda left, right: diff_result,
        verify=lambda left, right: diff_result,
    )
    monkeypatch.setattr(run_manifest_cmd, "get_run_manifest_service", lambda: service)
    monkeypatch.setattr(
        run_manifest_cmd,
        "build_run_replay_bundle_descriptor",
        lambda result: SimpleNamespace(
            to_dict=lambda: {"bundle": result.manifest.manifest_id}
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_forensic_run_diff_service",
        lambda: SimpleNamespace(compare=lambda left, right: diff_result),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_corpus_service",
        lambda: SimpleNamespace(
            build_certifiability_inventory=lambda: SimpleNamespace(
                to_dict=lambda: {"inventory": True}
            ),
            certify_retained_corpus=lambda specs: SimpleNamespace(
                to_dict=lambda: {"certified": specs}
            ),
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_closure_service",
        lambda: SimpleNamespace(
            build_closure_report=lambda residual_dispositions: SimpleNamespace(
                to_dict=lambda: {"closure": residual_dispositions}
            )
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_universe_service",
        lambda: SimpleNamespace(
            build_universe_closure_report=lambda external_records: SimpleNamespace(
                governed_full_corpus_gate={"satisfied": True},
                durable_evidence_coverage_claim={"claimed": True},
                to_dict=lambda: {"universe": external_records},
            )
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "_coerce_bulk_certification_specs",
        lambda payload: ("spec", payload),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "_load_residual_dispositions",
        lambda path: {"source": str(path) if path else "none"},
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "_load_universe_external_records",
        lambda paths: [{"path_count": len(paths)}],
    )

    api_module = SimpleNamespace(
        persist_historical_replay_closure_report=lambda report: (
            tmp_path / "closure.json"
        ),
        persist_historical_replay_universe_report=lambda report: (
            tmp_path / "universe.json"
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "bioetl.composition.control_plane_service_access",
        api_module,
    )

    plan_path = tmp_path / "bulk.json"
    plan_path.write_text('{"records": [1]}', encoding="utf-8")

    run_manifest_cmd.score_command.callback("manifest-1", "json")
    run_manifest_cmd.diff_command.callback("left", "right", "json")
    run_manifest_cmd.verify_command.callback("left", "right", "json")
    run_manifest_cmd.replay_bundle_command.callback("manifest-1", "json")
    run_manifest_cmd.forensic_diff_command.callback("left", "right", "json")
    run_manifest_cmd.inventory_command.callback("json")
    run_manifest_cmd.certify_historical_bulk_command.callback(plan_path, "json")
    run_manifest_cmd.closure_report_command.callback(plan_path, True, "json")
    run_manifest_cmd.universe_report_command.callback(
        (plan_path,), True, True, True, "json"
    )

    assert emitted[0][0]["identifier"] == "manifest-1"
    assert any(payload.get("bundle") == "manifest-1" for payload, _ in emitted)
    assert any(
        "artifact_path" in payload
        for payload, _ in emitted
        if "closure" in payload or "universe" in payload
    )
    assert not errors


def test_run_manifest_commands_cover_failure_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    emitted: list[tuple[dict[str, object], str]] = []
    errors: list[tuple[str, str]] = []
    monkeypatch.setattr(
        run_manifest_cmd,
        "_emit_payload",
        lambda payload, fmt: emitted.append((payload, fmt)),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "echo_error",
        lambda title, detail: errors.append((title, detail)),
    )

    corrupt = RunManifestInspectionCorruptionError("manifest-1", "corrupt")
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_run_manifest_service",
        lambda: SimpleNamespace(
            show=lambda identifier: (_ for _ in ()).throw(corrupt),
            diff=lambda left, right: (_ for _ in ()).throw(ValueError("bad diff")),
            verify=lambda left, right: (_ for _ in ()).throw(ValueError("bad verify")),
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_forensic_run_diff_service",
        lambda: SimpleNamespace(
            compare=lambda left, right: (_ for _ in ()).throw(
                ValueError("bad forensic")
            )
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_corpus_service",
        lambda: SimpleNamespace(
            certify_retained_corpus=lambda specs: (_ for _ in ()).throw(
                ValueError("bad bulk")
            )
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_closure_service",
        lambda: SimpleNamespace(
            build_closure_report=lambda residual_dispositions: (_ for _ in ()).throw(
                ValueError("bad closure")
            )
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd,
        "get_historical_replay_universe_service",
        lambda: SimpleNamespace(
            build_universe_closure_report=lambda external_records: (
                _ for _ in ()
            ).throw(ValueError("bad universe"))
        ),
    )
    monkeypatch.setattr(
        run_manifest_cmd, "_coerce_bulk_certification_specs", lambda payload: payload
    )
    monkeypatch.setattr(
        run_manifest_cmd, "_load_residual_dispositions", lambda path: {}
    )
    monkeypatch.setattr(
        run_manifest_cmd, "_load_universe_external_records", lambda paths: []
    )

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{bad", encoding="utf-8")

    run_manifest_cmd.show_command.callback("manifest-1", "json")
    run_manifest_cmd.diff_command.callback("left", "right", "json")
    run_manifest_cmd.verify_command.callback("left", "right", "json")
    run_manifest_cmd.replay_bundle_command.callback("manifest-1", "json")
    run_manifest_cmd.forensic_diff_command.callback("left", "right", "json")
    run_manifest_cmd.certify_historical_bulk_command.callback(invalid_json, "json")
    run_manifest_cmd.closure_report_command.callback(None, False, "json")
    run_manifest_cmd.universe_report_command.callback((), False, False, False, "json")

    assert not emitted
    assert any(
        title == "Run manifest store corruption" and "corrupt" in detail
        for title, detail in errors
    )
    assert ("Run manifest diff failed", "bad diff") in errors
    assert ("Run manifest verification failed", "bad verify") in errors
    assert ("Forensic run diff failed", "bad forensic") in errors
    assert any(
        title == "Historical replay bulk certification failed" for title, _ in errors
    )
    assert any(
        title == "Historical replay closure report failed" for title, _ in errors
    )
    assert any(
        title == "Historical replay universe report failed" for title, _ in errors
    )
