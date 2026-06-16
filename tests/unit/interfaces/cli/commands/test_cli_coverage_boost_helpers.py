"""Targeted unit coverage boosts for CLI helper and diagnostics modules."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

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
    allowlist.write_text("allowed:\n  registry: [metric_a, metric_b]\n", encoding="utf-8")

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
    contract_path = repo_root / "configs" / "quality" / "mandatory_tracing_coverage.yaml"
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
                payload=SimpleNamespace(
                    output={"dry_run": True, "would_mutate": True}
                ),
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


def test_lineage_text_renderers_cover_non_dict_nodes_and_identifier_resolution() -> None:
    assert lineage_cmd._render_node_lines(["node-a"]) == ["  - node-a"]
    assert lineage_cmd._render_relation_lines(["relation-a"]) == ["  - relation-a"]
    assert (
        lineage_cmd._resolve_explain_identifier(run_id=None, manifest_id=None) is None
    )
    assert (
        lineage_cmd._resolve_explain_identifier(run_id="run-1", manifest_id=None)
        == "run-1"
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


def test_config_dq_command_helpers_cover_error_and_compatibility_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    messages: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(config_dq, "echo_info", lambda *args: messages.append(("info", args)))
    monkeypatch.setattr(config_dq, "echo_error", lambda *args: messages.append(("error", args)))

    invalid_config = tmp_path / "invalid.yaml"
    invalid_config.write_text("- not-a-mapping\n", encoding="utf-8")
    service = MagicMock()
    monkeypatch.setattr(config_dq, "get_config_service", lambda: service)

    config_dq.validate_dq_config_command.callback("chembl_activity", str(invalid_config))
    assert any("Config file must contain a mapping" in str(args[-1]) for _, args in messages)

    messages.clear()
    artifact1 = tmp_path / "artifact1.json"
    artifact2 = tmp_path / "artifact2.json"
    artifact1.write_text('["invalid"]', encoding="utf-8")
    artifact2.write_text("{}", encoding="utf-8")
    config_dq.check_compatibility_command.callback(str(artifact1), str(artifact2))
    assert any("Artifacts must be JSON objects" in str(args[-1]) for _, args in messages)

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

    assert any("[OK] Configurations are compatible" in str(args[0]) for _, args in messages)
