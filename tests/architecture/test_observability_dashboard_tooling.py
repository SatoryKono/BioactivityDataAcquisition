# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Guardrails for observability dashboard maintenance tooling."""

import pytest

import ast
import json
import shlex
from pathlib import Path

import yaml

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit
from scripts.ops.observability.grafana import (
    run_grafana_dashboard_audit_cycle as audit_cycle,
)


pytestmark = pytest.mark.architecture


def test_legacy_fix_grafana_mutation_script_is_removed() -> None:
    """Legacy regex-based dashboard mutator must not remain in the repo."""
    assert not Path(
        "scripts/ops/observability/grafana/fix_grafana_dashboards.py"
    ).exists(), "Legacy fix_grafana_dashboards.py script must be removed"


def test_scripts_ops_cli_does_not_expose_legacy_fix_grafana_command() -> None:
    """scripts.ops must not expose the removed mutable Grafana rewrite entrypoint."""
    content = Path("scripts/ops/__main__.py").read_text(encoding="utf-8")

    assert "fix-grafana" not in content
    assert "fix_grafana_dashboards.py" not in content


def test_observability_dashboard_scripts_do_not_write_dashboard_json() -> None:
    """Observability dashboard tooling must stay validation/render-only."""
    grafana_dir = Path("scripts/ops/observability/grafana")
    offenders: list[str] = []
    allowed_report_write_targets = {
        "config.output_path",
        'config.output_dir / "render-manifest.json"',
    }
    reviewed_dashboard_generators = {
        "_apply_ds2_all.py",
        "_apply_dsa_residual.py",
        "_fix_no_scroll_triage_panels.py",
        "apply_dux2_residual.py",
        "apply_dux4_enforcement.py",
        "apply_dux5_residual.py",
        "apply_dux6_residual.py",
        "apply_dux7_live_residual.py",
        "generate_dux4_issue_pack.py",
        "generate_dux5_issue_pack.py",
        "generate_dux6_issue_pack.py",
        "render_nav_bus.py",
        "run_dux7_live_residual.py",
    }

    for script in sorted(grafana_dir.glob("*.py")):
        if script.name in reviewed_dashboard_generators:
            continue
        content = script.read_text(encoding="utf-8")
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "write_text":
                continue
            target = ast.get_source_segment(content, node.func.value) or ""
            if target.strip("()") in allowed_report_write_targets:
                continue
            offenders.append(f"{script}: {target}.write_text")

    assert not offenders, (
        "Observability dashboard tooling must not mutate shipped dashboard JSON:\n"
        + "\n".join(offenders)
    )


def test_audit_cycle_gate_output_rejects_shipped_dashboard_path() -> None:
    """Gate evidence must not be writable over a shipped dashboard."""
    dashboard_path = audit_cycle.SHIPPED_DASHBOARD_DIR / "blocked.json"

    with pytest.raises(ValueError, match="must not overwrite shipped dashboard JSON"):
        audit_cycle._resolve_gate_output_path(dashboard_path)


def test_audit_cycle_gate_output_writes_review_evidence(tmp_path: Path) -> None:
    """A normal gate target remains a deterministic JSON evidence artifact."""
    output_path = tmp_path / "dashboard-release-gates.json"
    screenshot_dir = tmp_path / "screenshots"
    config = audit_cycle._parse_args(
        [
            "--gate-output",
            str(output_path),
            "--screenshot-dir",
            str(screenshot_dir),
            "--occurrence-id",
            "architecture-test-occurrence",
        ]
    )
    config.semantic_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.semantic_output_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-07-16T00:00:00+00:00",
                "occurrence_id": config.occurrence_id,
                "semantic_gate": {"status": "pass"},
                "results": [{"dashboard_uid": "bioetl-dq-v2", "panel_id": 101}],
            }
        ),
        encoding="utf-8",
    )
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    (screenshot_dir / "render-manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-16T00:00:00+00:00",
                "occurrence_id": config.occurrence_id,
                "terminal_state_validation": {"status": "ok"},
                "dashboards": [
                    {
                        "uid": "bioetl-dq-v2",
                        "renderStatus": "rendered",
                        "terminalStateValidation": {
                            "status": "ok",
                            "panelStates": [{"id": 101, "classification": "healthy"}],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    release_passed = audit_cycle._write_gate_report(
        config,
        semantic_status="pass",
        render_status="pass",
        semantic_detail="semantic evidence passed",
        render_detail="render evidence passed",
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert release_passed is True
    assert payload["dashboard_semantic_gate"]["status"] == "pass"
    assert payload["dashboard_render_gate"]["status"] == "pass"
    assert payload["release_passed"] is True
    assert payload["dashboard_semantic_gate"]["source_artifact"]["sha256"]
    assert payload["dashboard_render_gate"]["source_artifact"]["sha256"]
    assert payload["dashboard_semantic_gate"]["source_artifact"]["dashboard_scope"] == [
        "bioetl-dq-v2#101"
    ]
    assert payload["dashboard_render_gate"]["source_artifact"]["dashboard_scope"] == [
        "bioetl-dq-v2#101"
    ]


def test_ci_dashboard_semantic_gate_covers_declared_release_contracts() -> None:
    workflow = yaml.safe_load(
        Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    )
    steps = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if isinstance(step, dict)
    ]

    def named_step(name: str) -> dict[str, object]:
        matches = [step for step in steps if step.get("name") == name]
        assert len(matches) == 1, name
        return matches[0]

    semantic_step = named_step("Dashboard semantic release policy gate (token-free)")
    semantic_run = semantic_step.get("run")
    assert isinstance(semantic_run, str)

    required_contracts = (
        "report-observability-metric-inventory",
        "tests/architecture/test_observability_dashboard_contracts.py",
        "tests/architecture/test_observability_dashboard_tooling.py",
        "tests/architecture/test_observability_docs_drift.py",
        "tests/architecture/test_observability_metric_governance.py",
        "tests/integration/ci/test_dashboard_active_docs_sync.py",
        "tests/integration/test_dashboard_no_data_policy.py",
        "tests/integration/test_grafana_config.py",
        "tests/integration/test_grafana_datasource_provisioning.py",
        "tests/integration/test_grafana_selector_contract.py",
        "tests/integration/test_grafana_surface_contracts.py",
        "tests/integration/test_grafana_variable_reference.py",
    )
    logical_commands = [
        shlex.split(line, comments=True, posix=True)
        for line in semantic_run.replace("\\\n", " ").splitlines()
        if line.strip()
    ]
    report_contract, *pytest_contracts = required_contracts

    def _has_qa_report(command: list[str], report: str) -> bool:
        # Allow optional uv flags such as --frozen --no-build.
        if len(command) < 2 or command[0] != "uv" or command[1] != "run":
            return False
        try:
            python_idx = command.index("python")
        except ValueError:
            return False
        return command[python_idx : python_idx + 4] == [
            "python",
            "-m",
            "scripts.engineering.qa",
            report,
        ]

    assert any(_has_qa_report(command, report_contract) for command in logical_commands)

    def _is_uv_pytest(command: list[str]) -> bool:
        if len(command) < 2 or command[0] != "uv" or command[1] != "run":
            return False
        return "pytest" in command

    pytest_commands = [
        command for command in logical_commands if _is_uv_pytest(command)
    ]
    assert len(pytest_commands) == 1
    pytest_arguments = set(pytest_commands[0])
    for contract in pytest_contracts:
        assert contract in pytest_arguments

    upload_step = named_step("Upload dashboard semantic policy evidence")
    upload_config = upload_step.get("with")
    assert isinstance(upload_config, dict)
    upload_paths = upload_config.get("path")
    assert isinstance(upload_paths, str)
    assert {path.strip() for path in upload_paths.splitlines() if path.strip()} == {
        "reports/observability/ci/dashboard-semantic-policy.xml",
        "reports/observability/runtime_cardinality_review_pr.json",
    }


@pytest.mark.parametrize(
    ("classification", "result_status", "expected_gate"),
    [
        ("query_invalid", "error", "fail"),
        ("datasource_unavailable", "error", "fail"),
        ("blocked_backend_unavailable", "error", "fail"),
        ("empty_result", "ok", "review_required"),
        ("zero_result", "ok", "pass"),
        ("nonzero_result", "ok", "pass"),
        ("nonempty_result", "ok", "pass"),
        ("resolved_numeric", "ok", "pass"),
        ("expected_empty", "ok", "pass"),
        ("unknown_result", "ok", "review_required"),
    ],
)
def test_semantic_classification_policy_is_release_enforced(
    classification: str,
    result_status: str,
    expected_gate: str,
) -> None:
    result = live_audit.AuditResult(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="policy fixture",
        source_kind="loki",
        semantic_kind="loki_query",
        status=result_status,
        classification=classification,
        detail="fixture",
        query_preview='{job="bioetl"}',
    )

    evidence = live_audit.semantic_gate_evidence([result])

    assert evidence["status"] == expected_gate


def test_closure_evidence_writers_use_atomic_storage_primitive() -> None:
    paths = (
        Path("scripts/ops/observability/grafana/run_grafana_dashboard_audit_cycle.py"),
        Path("scripts/ops/observability/grafana/audit_live_grafana_panels.py"),
        Path("scripts/ops/observability/grafana/rerender_grafana_screenshots.py"),
        Path("scripts/engineering/qa/run_observability_closure_campaign.py"),
    )

    for path in paths:
        source = path.read_text(encoding="utf-8")
        assert "atomic_write_text" in source
        assert ".write_text(" not in source
        assert ".write_bytes(" not in source


def test_live_panel_audit_blocks_all_http_panels_after_one_backend_failure(
    monkeypatch,
) -> None:
    """HTTP-backed panel audit must fail boundedly when the backend is down."""
    specs = (
        live_audit.PanelAuditSpec(
            dashboard_uid="bioetl-control-plane-v1",
            panel_id=9402,
            title="ID",
            source_kind="http",
            semantic_kind="http_table",
        ),
        live_audit.PanelAuditSpec(
            dashboard_uid="bioetl-runtime",
            panel_id=9403,
            title="Processed Records",
            source_kind="http",
            semantic_kind="http_table",
        ),
    )
    calls = {"resolve": 0, "http": 0}

    monkeypatch.setattr(live_audit, "effective_panel_specs", lambda: specs)
    monkeypatch.setattr(
        live_audit,
        "_find_panel",
        lambda _spec: {"targets": [{"refId": "A", "url": "/blocked"}]},
    )

    def raise_backend_down(_config: live_audit.AuditConfig) -> str:
        calls["resolve"] += 1
        raise OSError("connection refused")

    def fail_if_called(*_args, **_kwargs):
        calls["http"] += 1
        raise AssertionError("HTTP panel fetch should not run after backend failure")

    monkeypatch.setattr(live_audit, "_resolve_app_base_url", raise_backend_down)
    monkeypatch.setattr(live_audit, "_audit_http_panel", fail_if_called)

    results = live_audit.run_audit(
        live_audit.AuditConfig(
            prometheus_base_url="http://prometheus.invalid",
            app_base_url="http://app.invalid",
            loki_base_url="http://loki.invalid",
            tempo_base_url="http://tempo.invalid",
            grafana_base_url="http://grafana.invalid",
            grafana_username="admin",
            grafana_password="changeme",
            workflow="chembl_target",
            pipeline="chembl_target",
            run_type="backfill",
            run_id="run-1",
            range_hours=12,
            output_path=Path("/tmp/live-panel-audit.json"),
            request_timeout_seconds=0.2,
        )
    )

    assert calls == {"resolve": 1, "http": 0}
    assert [result.classification for result in results] == [
        "blocked_backend_unavailable",
        "blocked_backend_unavailable",
    ]
    assert all(result.status == "error" for result in results)
    assert "all HTTP-backed panel checks are blocked" in results[0].detail


def test_live_panel_audit_config_exposes_request_timeout_flag() -> None:
    config = live_audit._parse_args(
        [
            "--request-timeout-seconds",
            "0.5",
            "--output",
            "/tmp/live-panel-audit.json",
        ]
    )

    assert config.request_timeout_seconds == 0.5


def test_playwright_runtime_is_pinned_as_repo_dev_dependency() -> None:
    """Full browser dashboard render must not rely on a global Playwright install."""
    package = json.loads(Path("package.json").read_text(encoding="utf-8"))
    dev_dependencies = package.get("devDependencies", {})

    assert "playwright" in dev_dependencies

    setup_script = Path(
        "scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh"
    ).read_text(encoding="utf-8")
    preflight = Path(
        "scripts/ops/observability/grafana/check_grafana_dashboard_audit_preflight.py"
    ).read_text(encoding="utf-8")

    assert "npm ci --include=dev" in setup_script
    assert "BIOETL_PLAYWRIGHT_NODE_MODULES" in setup_script
    assert "expanded-row-capture" in preflight
    assert "Playwright expanded-row capture is unavailable" in preflight
