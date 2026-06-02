from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from urllib.error import HTTPError, URLError

import pytest

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight_subject,
)
from scripts.ops.observability.grafana import (
    run_grafana_dashboard_audit_cycle as cycle_subject,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_subject,
)
from tests.helpers import assert_router_python_command

pytestmark = pytest.mark.repo_backed


def _backend_result(
    *,
    backend_available: bool,
    health_url: str = "http://127.0.0.1:8081/health",
    message: str = "ok",
    status: str = "started",
) -> SimpleNamespace:
    return SimpleNamespace(
        backend_available=backend_available,
        health_url=health_url,
        message=message,
        status=status,
    )


def test_rerender_config_uses_env_defaults(monkeypatch: Any, tmp_path: Path) -> None:
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana.local:3000")
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")
    monkeypatch.setenv("GRAFANA_SERVICE_ACCOUNT_TOKEN", "grafana-token")

    config = rerender_subject._parse_args(
        ["--output-dir", str(tmp_path), "--uids", "bioetl-dq-v2"]
    )

    assert config.base_url == "http://grafana.local:3000"
    assert config.username == "viewer"
    assert config.password == "secret"
    assert config.service_account_token == "grafana-token"
    assert config.output_dir == tmp_path
    assert config.selected_uids == ("bioetl-dq-v2",)
    assert config.fallback == "auto"


def test_rerender_load_dashboards_filters_and_sorts(
    monkeypatch: Any, tmp_path: Path
) -> None:
    dashboard_dir = tmp_path / "tmp-test-dashboards"
    monkeypatch.setattr(rerender_subject, "_dashboard_dir", lambda: dashboard_dir)
    dashboard_dir.mkdir(exist_ok=True)
    (dashboard_dir / "runtime.json").write_text(
        json.dumps({"uid": "bioetl-runtime", "title": "Runtime"}) + "\n",
        encoding="utf-8",
    )
    (dashboard_dir / "dq.json").write_text(
        json.dumps({"uid": "bioetl-dq-v2", "title": "DQ"}) + "\n",
        encoding="utf-8",
    )
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=Path("reports/observability/grafana/screenshots"),
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=("bioetl-dq-v2",),
        fallback="auto",
    )

    dashboards = rerender_subject._load_dashboards(config)

    assert dashboards == [
        rerender_subject.DashboardRecord(
            uid="bioetl-dq-v2",
            url="/d/bioetl-dq-v2/dq",
            title="DQ",
        )
    ]


def test_rerender_scope_maps_run_id_to_silver_reject_explorer_run_filter(
    tmp_path: Path,
) -> None:
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=(),
        fallback="auto",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=96,
    )

    params = rerender_subject._scope_query_params(config)

    assert params["var-run_id"] == "run-123"
    assert params["var-quarantine_run_id"] == "run-123"


def test_rerender_failure_hint_includes_frontend_renderer_state(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        rerender_subject,
        "_request_json",
        lambda *_, **__: {
            "rendererAvailable": True,
            "rendererVersion": "5.0.0",
        },
    )
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=(),
        fallback="auto",
    )

    hint = rerender_subject._render_failure_hint(config)

    assert "rendererAvailable=True" in hint
    assert "rendererVersion='5.0.0'" in hint
    assert "GF_RENDERING_RENDERER_TOKEN must match AUTH_TOKEN" in hint
    assert "BROWSER_FLAGS" in hint
    assert "Playwright fallback" in hint


def test_rerender_failure_hint_explains_grafana_auth_drift(
    monkeypatch: Any, tmp_path: Path
) -> None:
    def raise_unauthorized(*_args: object, **_kwargs: object) -> object:
        raise HTTPError(
            url="http://localhost:3000/api/frontend/settings",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(rerender_subject, "_request_json", raise_unauthorized)
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=(),
        fallback="auto",
    )

    hint = rerender_subject._render_failure_hint(config)

    assert "Grafana auth failed" in hint
    assert "scripts/ops/support/load_repo_env.sh" in hint


def test_rerender_manifest_records_engine_and_run_scope(tmp_path: Path) -> None:
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=("bioetl-control-plane-v1",),
        fallback="none",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="b51986c6-870b-4457-aa70-baedac2710ad",
        range_hours=12,
    )
    screenshot = tmp_path / "bioetl-control-plane-v1.png"
    screenshot.write_bytes(b"png")

    rerender_subject._write_manifest(
        config,
        rendered=[
            (
                rerender_subject.DashboardRecord(
                    uid="bioetl-control-plane-v1",
                    url="/d/bioetl-control-plane-v1/0-control-plane",
                    title="0. Control Plane",
                ),
                screenshot,
            )
        ],
    )

    manifest = json.loads((tmp_path / "render-manifest.json").read_text())
    assert manifest["engine"] == "grafana-render-api"
    assert manifest["scope"] == {
        "workflow": "chembl_target",
        "pipeline": "chembl_target",
        "run_type": "backfill",
        "run_id": "b51986c6-870b-4457-aa70-baedac2710ad",
        "range_hours": 12,
    }
    assert manifest["render_results"][0]["status"] == "rendered"
    assert manifest["render_results"][0]["screenshot"] == (
        "bioetl-control-plane-v1.png"
    )


def test_rerender_writes_partial_manifest_before_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    records = [
        rerender_subject.DashboardRecord(
            uid="bioetl-ok",
            url="/d/bioetl-ok/ok",
            title="OK",
        ),
        rerender_subject.DashboardRecord(
            uid="bioetl-fails",
            url="/d/bioetl-fails/fails",
            title="Fails",
        ),
    ]
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda _config: records)

    def fake_render(
        record: rerender_subject.DashboardRecord,
        config: rerender_subject.RenderConfig,
    ) -> Path:
        if record.uid == "bioetl-fails":
            raise OSError("renderer returned 500")
        target = config.output_dir / f"{record.uid}.png"
        target.write_bytes(b"png")
        return target

    monkeypatch.setattr(rerender_subject, "_render_dashboard", fake_render)
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=30.0,
        selected_uids=(),
        fallback="none",
    )

    with pytest.raises(rerender_subject.RenderApiFailure):
        rerender_subject._render_via_api(config)

    manifest = json.loads((tmp_path / "render-manifest.json").read_text())
    statuses = {item["uid"]: item["status"] for item in manifest["render_results"]}
    assert statuses == {"bioetl-ok": "rendered", "bioetl-fails": "error"}
    assert "renderer returned 500" in manifest["render_results"][1]["error"]


def test_check_playwright_runtime_reports_missing_node(monkeypatch: Any) -> None:
    monkeypatch.setattr(rerender_subject, "_resolve_node_executable", lambda: None)

    ok, detail = rerender_subject.check_playwright_runtime()

    assert ok is False
    assert "Node.js is unavailable" in detail


def test_check_playwright_runtime_missing_module_points_to_bootstrap(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )

    class _Result:
        returncode = 1
        stdout = ""
        stderr = "Error: Cannot find module 'playwright'"

    monkeypatch.setattr(
        rerender_subject.subprocess,
        "run",
        lambda *args, **kwargs: _Result(),
    )

    ok, detail = rerender_subject.check_playwright_runtime()

    assert ok is False
    assert "setup_grafana_screenshot_runtime.sh" in detail
    assert "devDependencies" in detail


def test_check_playwright_runtime_times_out_probe(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )

    def raise_timeout(*_args: object, **_kwargs: object) -> object:
        raise rerender_subject.subprocess.TimeoutExpired(
            cmd=["node", "-e", "..."],
            timeout=1,
        )

    monkeypatch.setattr(rerender_subject.subprocess, "run", raise_timeout)

    ok, detail = rerender_subject.check_playwright_runtime(timeout_seconds=1)

    assert ok is False
    assert "timed out" in detail


def test_check_playwright_runtime_missing_shared_libs_points_to_system_packages(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )

    class _Result:
        returncode = 1
        stdout = ""
        stderr = (
            "chrome-headless-shell: error while loading shared libraries: "
            "libnspr4.so: cannot open shared object file"
        )

    monkeypatch.setattr(
        rerender_subject.subprocess,
        "run",
        lambda *args, **kwargs: _Result(),
    )

    ok, detail = rerender_subject.check_playwright_runtime()

    assert ok is False
    assert "libnspr4" in detail
    assert "shared libraries" in detail


def test_rerender_builds_playwright_env(tmp_path: Path) -> None:
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=("bioetl-control-plane-v1",),
        fallback="auto",
    )

    env = rerender_subject._playwright_env(config)

    assert env["GRAFANA_BASE_URL"] == "http://localhost:3000"
    assert env["GRAFANA_USERNAME"] == "admin"
    assert env["GRAFANA_PASSWORD"] == "changeme"
    assert env["GRAFANA_SCREENSHOT_OUTPUT_DIR"] == str(tmp_path)
    assert env["GRAFANA_SCREENSHOT_TIMEOUT_MS"] == "45000"
    assert env["GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS"] == "180000"
    assert env["GRAFANA_SCREENSHOT_UIDS"] == "bioetl-control-plane-v1"


def test_rerender_builds_playwright_env_with_sidecar_node_modules(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv(
        "BIOETL_PLAYWRIGHT_NODE_MODULES", "/tmp/bioetl-tools/runtime/node_modules"
    )
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    env = rerender_subject._playwright_env(config)

    assert (
        env["BIOETL_PLAYWRIGHT_NODE_MODULES"]
        == "/tmp/bioetl-tools/runtime/node_modules"
    )
    assert env["NODE_PATH"].startswith("/tmp/bioetl-tools/runtime/node_modules")


def test_rerender_builds_playwright_env_with_default_sidecar_runtime(
    monkeypatch: Any, tmp_path: Path
) -> None:
    node_modules = tmp_path / "runtime" / "node_modules"
    (node_modules / "playwright").mkdir(parents=True)
    (node_modules / "playwright" / "package.json").write_text("{}", encoding="utf-8")
    browsers = tmp_path / "browsers"
    browsers.mkdir()
    local_libs = (
        tmp_path
        / ".cache"
        / "grafana-screenshot-runtime"
        / "root"
        / "usr"
        / "lib"
        / "x86_64-linux-gnu"
    )
    local_libs.mkdir(parents=True)
    monkeypatch.delenv("BIOETL_PLAYWRIGHT_NODE_MODULES", raising=False)
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    monkeypatch.delenv("BIOETL_PLAYWRIGHT_LIBRARY_PATH", raising=False)
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        rerender_subject, "DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES", node_modules
    )
    monkeypatch.setattr(rerender_subject, "DEFAULT_TOOL_PLAYWRIGHT_BROWSERS", browsers)

    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    env = rerender_subject._playwright_env(config)

    assert env["BIOETL_PLAYWRIGHT_NODE_MODULES"] == str(node_modules)
    assert env["NODE_PATH"].startswith(str(node_modules))
    assert env["PLAYWRIGHT_BROWSERS_PATH"] == str(browsers)
    assert env["BIOETL_PLAYWRIGHT_LIBRARY_PATH"] == str(local_libs)
    assert env["LD_LIBRARY_PATH"].startswith(str(local_libs))


def test_rerender_builds_playwright_env_with_service_account_token(
    tmp_path: Path,
) -> None:
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="token-123",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    env = rerender_subject._playwright_env(config)

    assert env["GRAFANA_SERVICE_ACCOUNT_TOKEN"] == "token-123"


def test_screenshot_runtime_setup_scripts_keep_bootstrap_contract() -> None:
    shell_script = Path(
        "scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.sh"
    ).read_text(encoding="utf-8")
    powershell_script = Path(
        "scripts/ops/observability/grafana/setup_grafana_screenshot_runtime.ps1"
    ).read_text(encoding="utf-8")

    for content in (shell_script, powershell_script):
        assert "bioetl-control-plane-v1" in content
        assert "rerender-grafana" in content
        assert "Playwright" in content

    assert "npm ci --include=dev" in shell_script
    assert "npm_config_production=false" in shell_script
    assert "BIOETL_PLAYWRIGHT_NODE_MODULES" in shell_script
    assert "BIOETL_PLAYWRIGHT_LIBRARY_PATH" in shell_script
    assert "playwright-runtime" in shell_script
    assert "libasound2t64" in shell_script
    assert "ci --include=dev --no-bin-links" in powershell_script
    assert 'NPM_CONFIG_PRODUCTION = "false"' in powershell_script

    for package_name in ("libnspr4", "libnss3", "libasound2", "libxkbcommon0"):
        assert package_name in shell_script
    for library_name in ("libatk-bridge-2.0.so.0", "libXrandr.so.2"):
        assert library_name in shell_script


def test_playwright_screenshot_script_uses_multiple_panel_readiness_selectors() -> None:
    script = Path(
        "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
    ).read_text(encoding="utf-8")

    assert "countRenderedPanels" in script
    assert '[data-testid^="data-testid Panel header"]' in script
    assert '[data-testid*="Panel header"]' in script
    assert '[data-testid="Panel header"]' in script
    assert '[data-viz-panel-key^="panel-"]' in script
    assert "[data-panelid]" in script
    assert "renderedPanelCount" in script
    assert "renderedPanelSelector" in script


def test_rerender_playwright_fallback_streams_output_from_repo_root(
    monkeypatch: Any, tmp_path: Path
) -> None:
    script_path = tmp_path / "rerender_grafana_screenshots.cjs"
    script_path.write_text("// noop\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        rerender_subject, "_playwright_script_path", lambda: script_path
    )
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)

    def fake_run(command: list[str], **kwargs: object) -> _Result:
        captured["command"] = command
        captured["kwargs"] = kwargs
        return _Result()

    monkeypatch.setattr(rerender_subject.subprocess, "run", fake_run)

    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=45.0,
        selected_uids=(),
        fallback="auto",
    )

    result = rerender_subject._run_playwright_fallback(config)

    assert result == 0
    assert captured["command"] == [
        "/usr/bin/node",
        str(script_path),
        "--scope-query",
        "from=now-12h&to=now&timezone=UTC",
    ]
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert "capture_output" not in captured["kwargs"]
    assert captured["kwargs"]["env"]["GRAFANA_BASE_URL"] == "http://localhost:3000"


def test_rerender_resolves_node_from_repo_local_bin(
    monkeypatch: Any, tmp_path: Path
) -> None:
    node_path = tmp_path / "node_modules" / ".bin" / "node.exe"
    node_path.parent.mkdir(parents=True, exist_ok=True)
    node_path.write_text("", encoding="utf-8")

    monkeypatch.setattr(rerender_subject.shutil, "which", lambda _name: None)
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)

    resolved = rerender_subject._resolve_node_executable()

    assert resolved == str(node_path)


def test_rerender_falls_back_to_playwright_on_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda *_: [])
    monkeypatch.setattr(
        rerender_subject,
        "_render_via_api",
        lambda *_: (_ for _ in ()).throw(URLError("timed out")),
    )
    monkeypatch.setattr(rerender_subject, "_run_playwright_fallback", lambda *_: 0)

    result = rerender_subject.main(
        [
            "--output-dir",
            str(tmp_path),
            "--fallback",
            "auto",
        ]
    )

    assert result == 0


def test_live_audit_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "audit-live-grafana",
        expected_target="observability/grafana/audit_live_grafana_panels.py",
    )


def test_live_audit_reviewed_specs_cover_semantically_sensitive_panels() -> None:
    covered = {
        (spec.dashboard_uid, spec.panel_id): spec.title
        for spec in audit_subject.REVIEWED_PANEL_SPECS
    }

    assert (
        covered[("bioetl-control-plane-v1", 132)]
        == "Monitor: Manifest Write Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 133)]
        == "Monitor: Ledger Append Failure Ratio"
    )
    assert (
        covered[("bioetl-control-plane-v1", 892)]
        == "Monitor: Checkpoint Freshness Lag (seconds)"
    )
    assert covered[("bioetl-control-plane-v1", 9402)] == "ID"
    assert covered[("bioetl-control-plane-v1", 9403)] == "Processed Records"
    assert covered[("bioetl-dq-v2", 101)] == "Review: Latest Successful Data Timestamp"
    assert covered[("bioetl-dq-v2", 8)] == "Monitor: Worst Data Freshness Lag (seconds)"
    assert covered[("bioetl-dq-v2", 9402)] == "ID"
    assert covered[("bioetl-dq-v2", 9403)] == "Processed Records"
    assert (
        covered[("bioetl-silver-reject-explorer", 3)] == "Track Reject Rate vs Bronze"
    )
    assert covered[("bioetl-overview-v2", 9301)] == "Processed Records"
    assert covered[("bioetl-runtime", 9403)] == "Processed Records"
    assert covered[("bioetl-provider-health-v2", 9403)] == "Processed Records"
    assert covered[("bioetl-workflow-overview", 9403)] == "Processed Records"


def test_live_audit_classifies_prometheus_zero_and_nonzero_results() -> None:
    zero_payload = {
        "status": "success",
        "data": {"resultType": "vector", "result": [{"value": [1, "0"]}]},
    }
    nonzero_payload = {
        "status": "success",
        "data": {"resultType": "scalar", "result": [1, "5"]},
    }

    assert audit_subject._classify_prometheus_payload(zero_payload)[0] == "zero_result"
    assert (
        audit_subject._classify_prometheus_payload(nonzero_payload)[0]
        == "nonzero_result"
    )


def test_live_audit_treats_checkpoint_freshness_unknown_as_valid_unknown_state(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-control-plane-v1",
        panel_id=892,
        title="Monitor: Checkpoint Freshness Lag (seconds)",
        source_kind="http",
        semantic_kind="freshness",
    )
    panel = {
        "targets": [
            {"url": "/ops/control-plane/checkpoint-freshness?pipeline=${pipeline}"}
        ]
    }
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {"status": "UNKNOWN", "age_seconds": None},
    )

    result = audit_subject._audit_http_panel(
        spec,
        panel,
        config,
        app_base_url="http://localhost:8081",
    )

    assert result.classification == "unknown_result"
    assert result.status == "ok"


def test_live_audit_classifies_http_zero_state_and_nonzero() -> None:
    zero_payload = {"total": 0, "bronze_records": 0, "reject_ratio": 0.0}
    nonzero_payload = {"total": 2, "bronze_records": 10, "reject_ratio": 0.2}

    assert (
        audit_subject._classify_http_payload(zero_payload)[0]
        == "zero_state_unknown_denominator"
    )
    assert audit_subject._classify_http_payload(nonzero_payload)[0] == "nonzero_result"


def test_live_audit_classifies_http_freshness_zero_and_empty() -> None:
    zero_payload = {"status": "OK", "age_seconds": 0.0}
    empty_payload = {"status": "UNKNOWN", "age_seconds": None}

    assert (
        audit_subject._classify_http_freshness_payload(zero_payload)[0] == "zero_result"
    )
    assert (
        audit_subject._classify_http_freshness_payload(empty_payload)[0]
        == "unknown_result"
    )


def test_live_audit_parse_args_uses_grafana_env_defaults(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana.local:3000")
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    config = audit_subject._parse_args(
        [
            "--workflow",
            "chembl_target",
            "--run-id",
            "run-123",
            "--output",
            str(tmp_path / "audit.json"),
        ]
    )

    assert config.app_base_url == "http://localhost:8081"
    assert config.loki_base_url == "http://localhost:3100"
    assert config.tempo_base_url == "http://localhost:3200"
    assert config.grafana_base_url == "http://grafana.local:3000"
    assert config.grafana_username == "viewer"
    assert config.grafana_password == "secret"
    assert config.workflow == "chembl_target"
    assert config.run_id == "run-123"


def test_live_audit_substitutes_workflow_and_run_id_tokens() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "/ops/control-plane/identity-table?workflow=${workflow}&pipeline=${pipeline}"
        "&run_type=${run_type:csv}&run_id=${run_id}",
        config,
    )

    assert "workflow=chembl_target" in rendered
    assert "pipeline=chembl_target" in rendered
    assert "run_type=backfill" in rendered
    assert "run_id=run-123" in rendered


def test_live_audit_substitutes_grafana_rate_interval() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "rate(metric_bucket[$__rate_interval]) "
        "or rate(metric_bucket[${__rate_interval}])",
        config,
    )

    assert "$__rate_interval" not in rendered
    assert "${__rate_interval}" not in rendered
    assert rendered == "rate(metric_bucket[5m]) or rate(metric_bucket[5m])"


def test_live_audit_substitutes_hidden_workflow_context_tokens() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        'metric{pipeline=~"$pipeline_context",run_type=~"$run_type_context",'
        'provider=~"$provider_hint",step_kind=~"$step_kind",status=~"$step_status"}',
        config,
    )

    assert "$pipeline_context" not in rendered
    assert "$run_type_context" not in rendered
    assert "$provider_hint" not in rendered
    assert "$step_kind" not in rendered
    assert "$step_status" not in rendered
    assert 'pipeline=~"chembl_target"' in rendered
    assert 'run_type=~"backfill"' in rendered
    assert 'provider=~"chembl"' in rendered
    assert 'step_kind=~".*"' in rendered
    assert 'status=~".*"' in rendered


def test_live_audit_scopes_silver_reject_explorer_to_target_run_id() -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    rendered = audit_subject._substitute_dashboard_tokens(
        "/ops/quarantine/filtered-stats?pipeline=${pipeline}"
        "&run_id=${quarantine_run_id}&from=${__from:date:iso}",
        config,
    )

    assert "run_id=run-123" in rendered
    assert "${quarantine_run_id}" not in rendered


def test_live_audit_classifies_empty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 0, "limit": 50, "offset": 0}
    )

    assert classification == "zero_result"
    assert "zero rows" in detail


def test_live_audit_classifies_nonempty_filtered_records_by_row_count() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [{"payload_hash": "abc"}], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "nonempty_result"
    assert "returned rows" in detail


def test_live_audit_rejects_filtered_records_total_items_drift() -> None:
    classification, detail = audit_subject._classify_http_records_payload(
        {"items": [], "total": 1, "limit": 50, "offset": 0}
    )

    assert classification == "invalid_shape"
    assert "disagree" in detail


def test_live_audit_loki_panel_uses_query_range(monkeypatch: Any) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
        required=False,
    )
    panel = {"targets": [{"refId": "A", "expr": '{job="bioetl"}'}]}
    captured: dict[str, str] = {}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        captured["url"] = url
        return {"status": "success", "data": {"result": []}}

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert "/loki/api/v1/query_range?" in captured["url"]
    assert "start=" in captured["url"]
    assert "end=" in captured["url"]
    assert "limit=100" in captured["url"]
    assert result.status == "ok"
    assert result.classification == "expected_empty"
    assert "endpoint=query_range" in result.detail


def test_live_audit_effective_specs_include_generated_loki_and_tempo_coverage() -> None:
    specs = audit_subject.effective_panel_specs()
    keys = {
        (spec.dashboard_uid, spec.panel_id, spec.source_kind, spec.target_ref_id)
        for spec in specs
    }

    assert ("bioetl-runtime", 250, "loki", "A") in keys
    assert any(
        spec.source_kind == "tempo" and spec.dashboard_uid == "bioetl-runtime"
        for spec in specs
    )
    assert len(specs) > len(audit_subject.REVIEWED_PANEL_SPECS)


def test_live_audit_required_reviewed_specs_use_concrete_target_refs() -> None:
    missing_refs = [
        f"{spec.dashboard_uid}#{spec.panel_id}"
        for spec in audit_subject.effective_panel_specs()
        if spec.required
        and spec.source_kind in {"http", "prometheus"}
        and not spec.target_ref_id
    ]

    assert missing_refs == []


def test_dashboard_json_has_no_backup_artifacts_in_active_dashboard_tree() -> None:
    backup_files = sorted(Path("grafana/dashboards").glob("*.backup"))

    assert backup_files == []


def test_alerts_slo_dashboard_is_first_class_shipped_surface() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-alerts-slo.json").read_text(encoding="utf-8")
    )
    variables = {
        item.get("name") for item in dashboard.get("templating", {}).get("list", [])
    }

    assert dashboard["uid"] == "bioetl-alerts-slo"
    assert dashboard["title"] == "6. Alerts & SLO"
    assert {"workflow", "pipeline", "run_type"}.issubset(variables)
    assert "run_id" not in variables
    assert "ALERTS" in json.dumps(dashboard)


def test_silver_reject_explorer_keeps_shared_shell_context_outside_forensic_scope() -> (
    None
):
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-silver-reject-explorer.json").read_text(
            encoding="utf-8"
        )
    )
    variables = {
        item.get("name") for item in dashboard.get("templating", {}).get("list", [])
    }
    serialized = json.dumps(dashboard)

    assert {"pipeline", "run_type"}.issubset(variables)
    assert "workflow" not in variables
    assert "run_id" not in variables
    assert "var-workflow=$workflow" not in serialized
    assert "var-run_id=$run_id" not in serialized
    assert "var-quarantine_run_id=$run_id" not in serialized
    assert "quarantine_run_id remains the forensic row filter" in serialized


def test_silver_reject_explorer_generic_links_do_not_receive_primary_run_context() -> (
    None
):
    for path in Path("grafana/dashboards").glob("*.json"):
        if path.name == "bioetl-silver-reject-explorer.json":
            continue
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk(value: object) -> None:
            if isinstance(value, dict):
                for key, nested in value.items():
                    if key == "uid":
                        continue
                    walk(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    walk(nested)
                return
            if not isinstance(value, str):
                return
            if "bioetl-silver-reject-explorer" not in value or not value.startswith(
                "/d/"
            ):
                return
            assert "var-pipeline=" in value
            assert "var-run_type=" in value
            assert "var-workflow=" not in value
            assert "var-run_id=" not in value
            assert "var-quarantine_run_id=$run_id" not in value

        walk(dashboard)


def test_runtime_log_hygiene_trend_uses_aggregated_loki_range_queries() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-runtime.json").read_text(encoding="utf-8")
    )
    panel = next(panel for panel in dashboard["panels"] if panel.get("id") == 258)
    expressions = {target["refId"]: target["expr"] for target in panel["targets"]}

    assert expressions["A"].startswith("sum(count_over_time(")
    assert expressions["B"].startswith("sum(count_over_time(")
    assert "No data means" in panel["description"]


def test_prometheus_dashboard_panels_do_not_filter_on_run_id_labels() -> None:
    for path in Path("grafana/dashboards").glob("*.json"):
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for panel in panels:
                result.append(panel)
                nested = panel.get("panels")
                if isinstance(nested, list):
                    result.extend(walk_panels(nested))
            return result

        for panel in walk_panels(dashboard.get("panels", [])):
            for target in panel.get("targets", []) or []:
                expr = target.get("expr")
                if not isinstance(expr, str):
                    continue
                assert "run_id" not in expr, (
                    f"{path}:{panel.get('id')} must keep run_id out of "
                    "Prometheus/LogQL metric labels"
                )


def test_run_id_independent_metric_panels_disclose_scope() -> None:
    scope_terms = (
        "selected-range",
        "global",
        "current",
        "range",
        "not filtered",
        "workflow",
        "provider",
        "pipeline",
        "status",
        "alert",
        "slo",
        "freshness",
        "scope",
        "selected",
    )
    missing_scope: list[str] = []
    for path in Path("grafana/dashboards").glob("*.json"):
        dashboard = json.loads(path.read_text(encoding="utf-8"))

        def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for panel in panels:
                result.append(panel)
                nested = panel.get("panels")
                if isinstance(nested, list):
                    result.extend(walk_panels(nested))
            return result

        for panel in walk_panels(dashboard.get("panels", [])):
            for target in panel.get("targets", []) or []:
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                text = (
                    f"{panel.get('title', '')} {panel.get('description', '')}".lower()
                )
                if not any(term in text for term in scope_terms):
                    missing_scope.append(
                        f"{path}:{panel.get('id')}:{panel.get('title')}"
                    )

    assert missing_scope == []


def test_workflow_status_titles_make_selected_range_scope_visible() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-workflow-overview.json").read_text(
            encoding="utf-8"
        )
    )
    titles = {panel.get("id"): panel.get("title") for panel in dashboard["panels"]}

    assert titles[9401] == "Status"
    assert titles[9404] == "Pipeline Status"


def test_live_audit_isolates_non_required_panel_execution_failures(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
        required=False,
    )
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))
    monkeypatch.setattr(audit_subject, "_find_panel", lambda _spec: {})
    monkeypatch.setattr(
        audit_subject,
        "_audit_loki_panel",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("timed out")),
    )

    results = audit_subject.run_audit(config)

    assert len(results) == 1
    assert results[0].status == "ok"
    assert results[0].classification == "blocked_unavailable"


def test_live_audit_normalizes_docker_gateway_to_localhost() -> None:
    assert (
        audit_subject._normalize_host_access_url("http://host.docker.internal:8081")
        == "http://localhost:8081"
    )


def test_live_audit_adds_zero_bind_fallback_for_localhost() -> None:
    assert (
        audit_subject._zero_bind_access_url("http://localhost:8081")
        == "http://0.0.0.0:8081"
    )
    assert (
        audit_subject._zero_bind_access_url("http://127.0.0.1:8081")
        == "http://0.0.0.0:8081"
    )
    assert audit_subject._zero_bind_access_url("http://example.test:8081") is None


def test_live_audit_resolves_http_backend_from_datasource_candidates(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: "http://host.docker.internal:8081",
    )

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        if url == "http://localhost:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert audit_subject._resolve_app_base_url(config) == "http://localhost:8081"


def test_live_audit_resolves_http_backend_through_grafana_datasource_proxy(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: None,
    )

    def fake_request_json(
        url: str, *, auth_header: str, timeout_seconds: float
    ) -> object:
        captured["url"] = url
        captured["auth_header"] = auth_header
        assert timeout_seconds == config.request_timeout_seconds
        return {"status": "ok"}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_request_json", fake_request_json)
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    assert (
        audit_subject._resolve_app_base_url(config)
        == "http://localhost:3000/api/datasources/proxy/uid/quarantine-explorer"
    )
    assert captured["url"].endswith(
        "/api/datasources/proxy/uid/quarantine-explorer/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_live_audit_strips_userinfo_before_authenticated_proxy_request(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://admin:changeme@localhost:3000/api/datasources/proxy/uid/quarantine-explorer",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="ignored",
        grafana_password="ignored",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    captured: dict[str, str] = {}

    def fake_request_json(
        url: str, *, auth_header: str, timeout_seconds: float
    ) -> object:
        captured["url"] = url
        captured["auth_header"] = auth_header
        return {"status": "ok"}

    monkeypatch.setattr(audit_subject, "_request_json", fake_request_json)

    payload = audit_subject._fetch_json_with_optional_auth(
        f"{config.app_base_url}/health/live",
        config=config,
        timeout_seconds=5,
    )

    assert payload == {"status": "ok"}
    assert captured["url"] == (
        "http://localhost:3000/api/datasources/proxy/uid/"
        "quarantine-explorer/health/live"
    )
    assert captured["auth_header"].startswith("Basic ")


def test_live_audit_resolves_zero_bind_backend_when_localhost_is_unreachable(
    monkeypatch: Any,
) -> None:
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )

    monkeypatch.setattr(
        audit_subject,
        "_discover_http_datasource_url",
        lambda *_args, **_kwargs: None,
    )

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert timeout_seconds == config.request_timeout_seconds
        if url == "http://0.0.0.0:8081/health/live":
            return {"status": "ok"}
        raise OSError(url)

    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)
    monkeypatch.setattr(
        audit_subject,
        "_request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("proxy down")),
    )

    assert audit_subject._resolve_app_base_url(config) == "http://0.0.0.0:8081"


def test_grafana_audit_preflight_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "check-grafana-audit-preflight",
        expected_target="observability/grafana/check_grafana_dashboard_audit_preflight.py",
    )


def test_grafana_audit_preflight_parser_uses_grafana_env_defaults(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setenv("GRAFANA_USERNAME", "viewer")
    monkeypatch.setenv("GRAFANA_PASSWORD", "secret")

    parser = preflight_subject._build_parser()
    args = parser.parse_args(
        ["--screenshot-dir", str(tmp_path), "--json", "--skip-screenshot-check"]
    )

    assert args.grafana_username == "viewer"
    assert args.grafana_password == "secret"
    assert args.screenshot_dir == tmp_path
    assert args.json is True
    assert args.skip_screenshot_check is True


def test_grafana_audit_preflight_render_auth_reports_unauthorized(
    monkeypatch: Any,
) -> None:
    def raise_unauthorized(*_args: object, **_kwargs: object) -> object:
        raise HTTPError(
            url="http://localhost:3000/api/frontend/settings",
            code=401,
            msg="Unauthorized",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(rerender_subject, "_request_json", raise_unauthorized)

    result = preflight_subject._check_grafana_render_auth(
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
    )

    assert result.name == "grafana-render-auth"
    assert result.status == "error"
    assert "Grafana auth failed" in result.detail


def test_grafana_audit_preflight_playwright_runtime_surfaces_probe_detail(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        rerender_subject,
        "check_playwright_runtime",
        lambda *_args, **_kwargs: (
            False,
            "Playwright browser executable is missing",
        ),
    )

    result = preflight_subject._check_playwright_runtime()

    assert result.name == "playwright-runtime"
    assert result.status == "error"
    assert "browser executable is missing" in result.detail


def test_grafana_audit_preflight_expanded_row_capture_requires_playwright() -> None:
    result = preflight_subject._check_expanded_row_capture(
        preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="error",
            detail="missing browser runtime",
        )
    )

    assert result.name == "expanded-row-capture"
    assert result.status == "error"
    assert "missing browser runtime" in result.detail


def test_grafana_audit_cycle_parser_exposes_backend_boolean_flag() -> None:
    parser = cycle_subject._build_parser()

    default_args = parser.parse_args([])
    disabled_args = parser.parse_args(
        [
            "--no-ensure-observability-backend",
            "--no-refresh-observability-backend",
            "--no-render-filled-only",
        ]
    )

    assert default_args.ensure_observability_backend is True
    assert default_args.refresh_observability_backend is True
    assert default_args.render_filled_only is True
    assert disabled_args.ensure_observability_backend is False
    assert disabled_args.refresh_observability_backend is False
    assert disabled_args.render_filled_only is False


def test_grafana_audit_preflight_detects_stale_screenshot(tmp_path: Path) -> None:
    dashboard_path = tmp_path / "bioetl-control-plane-v1.json"
    screenshot_dir = tmp_path / "screens"
    screenshot_dir.mkdir()
    screenshot_path = screenshot_dir / "bioetl-control-plane-v1.png"
    manifest_path = screenshot_dir / "render-manifest.json"
    dashboard_path.write_text('{"uid":"bioetl-control-plane-v1"}\n', encoding="utf-8")
    screenshot_path.write_bytes(b"png")
    manifest_path.write_text("{}\n", encoding="utf-8")
    os.utime(screenshot_path, (1, 1))
    os.utime(dashboard_path, (2, 2))

    result = preflight_subject._check_screenshot_artifacts(screenshot_dir)

    assert result.status == "error"
    assert "stale dashboard screenshots" in result.detail


def test_grafana_audit_preflight_run_checks_collects_ok_results(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]),
            status="ok",
            detail=f"{kwargs['url']} reachable",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: preflight_subject.PreflightCheck(
            name="grafana-render-auth",
            status="ok",
            detail="frontend settings auth probe succeeded",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="ok",
            detail="playwright ready",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8081",
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_screenshot_artifacts",
        lambda *args, **kwargs: preflight_subject.PreflightCheck(
            name="screenshots",
            status="ok",
            detail="screens current",
        ),
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "grafana-render-auth",
        "prometheus",
        "playwright-runtime",
        "expanded-row-capture",
        "quarantine-explorer",
        "screenshots",
    ]
    assert all(check.status == "ok" for check in checks)


def test_grafana_audit_preflight_can_skip_screenshot_check(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        preflight_subject,
        "_check_http_json",
        lambda **kwargs: preflight_subject.PreflightCheck(
            name=str(kwargs["name"]),
            status="ok",
            detail="ok",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_grafana_render_auth",
        lambda **_kwargs: preflight_subject.PreflightCheck(
            name="grafana-render-auth",
            status="ok",
            detail="frontend settings auth probe succeeded",
        ),
    )
    monkeypatch.setattr(
        preflight_subject,
        "_check_playwright_runtime",
        lambda *_args, **_kwargs: preflight_subject.PreflightCheck(
            name="playwright-runtime",
            status="ok",
            detail="playwright ready",
        ),
    )
    monkeypatch.setattr(
        audit_subject,
        "_resolve_app_base_url",
        lambda *_args, **_kwargs: "http://localhost:8081",
    )
    called = False

    def fake_screenshot_check(
        _path: Path, *args, **kwargs
    ) -> preflight_subject.PreflightCheck:
        nonlocal called
        called = True
        return preflight_subject.PreflightCheck(
            name="screenshots",
            status="ok",
            detail="screens current",
        )

    monkeypatch.setattr(
        preflight_subject,
        "_check_screenshot_artifacts",
        fake_screenshot_check,
    )

    checks = preflight_subject.run_checks(
        grafana_base_url="http://localhost:3000",
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        grafana_username="admin",
        grafana_password="changeme",
        timeout_seconds=5.0,
        screenshot_dir=tmp_path,
        include_screenshot_check=False,
    )

    assert [check.name for check in checks] == [
        "grafana",
        "grafana-render-auth",
        "prometheus",
        "playwright-runtime",
        "expanded-row-capture",
        "quarantine-explorer",
    ]
    assert called is False


def test_grafana_audit_cycle_router_exposes_command() -> None:
    assert_router_python_command(
        ops_router,
        "run-grafana-audit-cycle",
        expected_target="observability/grafana/run_grafana_dashboard_audit_cycle.py",
    )


def test_grafana_audit_cycle_runs_preflight_rerender_and_live_audit(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2", "bioetl-runtime"),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--grafana-username",
            "admin",
            "--grafana-password",
            "changeme",
        ]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "rerender",
        "rerender",
        "preflight",
        "audit",
    ]
    assert "--skip-screenshot-check" in calls[0][1]
    assert "--skip-screenshot-check" not in calls[3][1]
    assert "--uids" in calls[1][1]
    assert "--fallback" in calls[1][1]
    assert calls[1][1][calls[1][1].index("--fallback") + 1] == "none"
    assert "--fallback" in calls[2][1]
    assert calls[2][1][calls[2][1].index("--fallback") + 1] == "playwright"
    assert any("render-api" in item for item in calls[1][1])
    assert str(tmp_path) in calls[2][1]
    assert "--screenshot-uids" in calls[3][1]
    assert "http://127.0.0.1:8081" in calls[0][1]
    assert "http://127.0.0.1:8081" in calls[3][1]


def test_grafana_audit_cycle_stops_on_service_preflight_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 1,
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append("rerender") or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append("audit") or 0,
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 1
    assert calls == ["preflight"]


def test_grafana_audit_cycle_stops_when_backend_cannot_be_ensured(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: (
            calls.append("ensure")
            or _backend_result(
                backend_available=False,
                message="bind failed",
                status="failed",
            )
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_reuse_existing_backend_if_healthy",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_start_managed_observability_backend",
        lambda **_kwargs: cycle_subject.BackendEnsureOutcome(
            result=_backend_result(
                backend_available=False,
                message="managed failed",
                status="failed",
            ),
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_find_available_local_port",
        lambda: 18081,
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 0,
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 1
    assert calls == ["ensure", "ensure"]
    assert "preflight" not in calls


def test_grafana_audit_cycle_stops_when_filled_dashboard_discovery_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append("preflight") or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: (_ for _ in ()).throw(
            OSError("audit backend unavailable")
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_load_cached_filled_dashboard_uids",
        lambda _config: (_ for _ in ()).throw(FileNotFoundError("no cache")),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append("rerender") or 0,
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 1
    assert calls == ["preflight"]


def test_grafana_audit_cycle_uses_cached_filled_dashboards_after_timeout(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda _port: True,
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "run_audit",
        lambda _config: (_ for _ in ()).throw(OSError("timed out")),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_load_cached_filled_dashboard_uids",
        lambda _config: ("bioetl-control-plane-v1", "bioetl-dq-v2"),
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "rerender",
        "rerender",
        "preflight",
        "audit",
    ]
    assert "--uids" in calls[1][1]
    assert "bioetl-control-plane-v1" in calls[1][1]
    assert "bioetl-dq-v2" in calls[1][1]


def test_grafana_audit_cycle_can_disable_filled_dashboard_filtering(
    monkeypatch: Any, tmp_path: Path
) -> None:
    rerender_argv: list[str] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(backend_available=True),
    )
    monkeypatch.setattr(cycle_subject.preflight, "main", lambda argv: 0)
    monkeypatch.setattr(cycle_subject.live_audit, "main", lambda argv: 0)
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: rerender_argv.extend(list(argv)) or 0,
    )

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--no-render-filled-only",
        ]
    )

    assert result == 0
    assert "--uids" not in rerender_argv


def test_grafana_audit_cycle_retries_backend_on_fallback_port(
    monkeypatch: Any, tmp_path: Path
) -> None:
    ensured_ports: list[int] = []
    calls: list[tuple[str, list[str]]] = []

    def fake_ensure(**kwargs: Any) -> SimpleNamespace:
        port = int(kwargs["port"])
        ensured_ports.append(port)
        if len(ensured_ports) == 1:
            return _backend_result(
                backend_available=False,
                health_url=f"http://127.0.0.1:{port}/health",
                message=(
                    "Existing backend is missing required audit capabilities and "
                    f"could not be restarted on port {port}."
                ),
                status="failed",
            )
        return _backend_result(
            backend_available=True,
            health_url=f"http://127.0.0.1:{port}/health",
            message="ok",
            status="started",
        )

    monkeypatch.setattr(
        cycle_subject, "ensure_observability_backend_started", fake_ensure
    )
    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: False
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend_required_paths",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )

    result = cycle_subject.main(
        ["--screenshot-dir", str(tmp_path), "--no-refresh-observability-backend"]
    )

    assert result == 0
    assert ensured_ports == [8081, 18081]
    assert "http://127.0.0.1:18081" in calls[0][1]
    assert "http://127.0.0.1:18081" in calls[3][1]
    assert "http://127.0.0.1:18081" in calls[4][1]


def test_grafana_audit_cycle_reuses_existing_backend_when_fallback_start_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: False
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend_required_paths",
        lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(
        cycle_subject,
        "probe_observability_backend",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=False,
            health_url="http://127.0.0.1:18081/health",
            message="Detached backend did not become ready at http://127.0.0.1:18081/health.",
            status="failed",
        ),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )

    result = cycle_subject.main(["--screenshot-dir", str(tmp_path)])

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "rerender",
        "rerender",
        "preflight",
        "audit",
    ]
    assert "http://127.0.0.1:8081" in calls[0][1]
    assert "http://127.0.0.1:8081" in calls[3][1]
    assert "http://127.0.0.1:8081" in calls[4][1]


def test_grafana_audit_cycle_uses_managed_backend_when_detached_backend_fails(
    monkeypatch: Any, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        cycle_subject, "drop_listening_backend_on_port", lambda _port: True
    )
    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=False,
            health_url="http://127.0.0.1:8081/health",
            message="Detached backend did not become ready",
            status="failed",
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "_reuse_existing_backend_if_healthy",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(cycle_subject, "_find_available_local_port", lambda: 18081)
    monkeypatch.setattr(
        cycle_subject,
        "_start_managed_observability_backend",
        lambda **_kwargs: cycle_subject.BackendEnsureOutcome(
            result=cycle_subject.ObservabilityBackendEnsureResult(
                status="started",
                health_url="http://127.0.0.1:8081/health",
                message="Managed backend started.",
            ),
            managed_process=MagicMock(poll=lambda: 0),
        ),
    )
    monkeypatch.setattr(
        cycle_subject.preflight,
        "main",
        lambda argv: calls.append(("preflight", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: ("bioetl-dq-v2",),
    )
    monkeypatch.setattr(
        cycle_subject.rerender,
        "main",
        lambda argv: calls.append(("rerender", list(argv))) or 0,
    )
    monkeypatch.setattr(
        cycle_subject.live_audit,
        "main",
        lambda argv: calls.append(("audit", list(argv))) or 0,
    )

    result = cycle_subject.main(["--screenshot-dir", str(tmp_path)])

    assert result == 0
    assert [name for name, _argv in calls] == [
        "preflight",
        "rerender",
        "rerender",
        "preflight",
        "audit",
    ]
    assert "http://127.0.0.1:8081" in calls[0][1]


def test_grafana_audit_cycle_can_disable_backend_refresh(
    monkeypatch: Any, tmp_path: Path
) -> None:
    dropped: list[int] = []

    monkeypatch.setattr(
        cycle_subject,
        "ensure_observability_backend_started",
        lambda **_kwargs: _backend_result(
            backend_available=True,
            health_url="http://127.0.0.1:8081/health",
            message="ok",
            status="reused",
        ),
    )
    monkeypatch.setattr(
        cycle_subject,
        "drop_listening_backend_on_port",
        lambda port: dropped.append(int(port)) or True,
    )
    monkeypatch.setattr(cycle_subject.preflight, "main", lambda argv: 0)
    monkeypatch.setattr(
        cycle_subject,
        "_discover_filled_dashboard_uids",
        lambda _config, *, app_base_url: (),
    )
    monkeypatch.setattr(cycle_subject.rerender, "main", lambda argv: 0)
    monkeypatch.setattr(cycle_subject.live_audit, "main", lambda argv: 0)

    result = cycle_subject.main(
        [
            "--screenshot-dir",
            str(tmp_path),
            "--no-refresh-observability-backend",
        ]
    )

    assert result == 0
    assert dropped == []


def test_live_audit_writes_report(monkeypatch: Any, tmp_path: Path) -> None:
    output_path = tmp_path / "live-panel-audit.json"
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="All",
        pipeline="chembl_target",
        run_type="incremental",
        run_id="-",
        range_hours=24,
        output_path=output_path,
    )
    results = [
        audit_subject.AuditResult(
            dashboard_uid="bioetl-dq-v2",
            panel_id=101,
            title="Review: Latest Successful Data Timestamp",
            source_kind="prometheus",
            semantic_kind="freshness",
            status="ok",
            classification="nonzero_result",
            detail="ok",
            query_preview="max(...)",
        )
    ]

    audit_subject._write_report(config, results)

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["config"]["pipeline"] == "chembl_target"
    assert payload["results"][0]["panel_id"] == 101
