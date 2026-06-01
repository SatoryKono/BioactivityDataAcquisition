"""Guardrails for observability dashboard maintenance tooling."""

import pytest

import ast
import json
from pathlib import Path

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit


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

    for script in sorted(grafana_dir.glob("*.py")):
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
