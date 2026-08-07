# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_subject,
)

pytestmark = pytest.mark.repo_backed


def test_rerender_has_no_committed_default_password() -> None:
    assert rerender_subject.DEFAULT_PASSWORD == ""


def test_rerender_password_resolution_uses_supported_env_order(
    monkeypatch: Any,
) -> None:
    for name in (
        "GF_SECURITY_ADMIN_PASSWORD",
        "GRAFANA_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    assert rerender_subject._resolve_grafana_password() == ""

    monkeypatch.setenv("GRAFANA_PASSWORD", "grafana-password")
    assert rerender_subject._resolve_grafana_password() == "grafana-password"
    monkeypatch.setenv("GF_SECURITY_ADMIN_PASSWORD", "gf-security-password")
    assert rerender_subject._resolve_grafana_password() == "gf-security-password"


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
        [
            "--output-dir",
            str(tmp_path),
            "--width",
            "1024",
            "--height",
            "1800",
            "--theme",
            "light",
            "--uids",
            "bioetl-dq-v2",
        ]
    )

    assert config.base_url == "http://grafana.local:3000"
    assert config.username == "viewer"
    assert config.password == "secret"
    assert config.service_account_token == "grafana-token"
    assert config.output_dir == tmp_path
    assert config.selected_uids == ("bioetl-dq-v2",)
    assert config.fallback == "auto"
    assert config.width == 1024
    assert config.height == 1800
    assert config.theme == "light"
    assert config.expand_collapsed_rows is True

    collapsed_config = rerender_subject._parse_args(["--no-expand-collapsed-rows"])
    assert collapsed_config.expand_collapsed_rows is False


def test_rerender_accepts_additional_dashboard_variables(tmp_path: Path) -> None:
    config = rerender_subject._parse_args(
        [
            "--output-dir",
            str(tmp_path),
            "--var",
            "provider=chembl",
            "--var",
            "stage=All",
        ]
    )

    assert config.variables == (("provider", "chembl"), ("stage", "All"))
    params = rerender_subject._scope_query_params(config)
    assert params["var-provider"] == "chembl"
    assert params["var-stage"] == "All"


def test_rerender_rejects_invalid_or_conflicting_dashboard_variables() -> None:
    with pytest.raises(SystemExit):
        rerender_subject._parse_args(["--var", "bad-name=value"])
    with pytest.raises(SystemExit):
        rerender_subject._parse_args(
            ["--var", "provider=chembl", "--var", "provider=pubchem"]
        )


def test_rerender_rejects_conflict_with_dedicated_scope_option(
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
        fallback="none",
        pipeline="chembl_assay",
        variables=(("pipeline", "pubchem_compound"),),
    )

    with pytest.raises(ValueError, match="conflicts with a dedicated scope option"):
        rerender_subject._scope_query_params(config)


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


def test_playwright_fallback_prepares_inner_scroll_before_screenshot() -> None:
    """Fallback screenshots must capture Grafana's scroll-container layout."""
    script = Path(
        "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
    ).read_text(encoding="utf-8")

    assert "setDashboardScrollPosition(page, 0)" in script
    assert "dashboardCaptureMetrics(page)" in script
    assert "prepareDashboardForCapture(page, dashboard, index, total)" in script
    assert "height: MAX_CAPTURE_VIEWPORT_HEIGHT" in script
    assert "dashboard.captureHeight = desiredHeight" in script
    assert "screenshotOptions.clip" in script
    assert script.index(
        "const viewportChanged = await prepareDashboardForCapture("
    ) < script.index("await page.screenshot(screenshotOptions)")


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
        selected_uids=("bioetl-dq-v2",),
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


def test_rerender_api_forwards_timeout_to_grafana_render_endpoint(
    monkeypatch: Any, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    def fake_download(
        url: str, *, headers: dict[str, str], timeout_seconds: float
    ) -> bytes:
        captured["url"] = url
        captured["headers"] = headers
        captured["timeout_seconds"] = timeout_seconds
        return b"png"

    monkeypatch.setattr(rerender_subject, "_download_binary", fake_download)
    config = rerender_subject.RenderConfig(
        base_url="http://localhost:3000",
        username="admin",
        password="changeme",
        service_account_token="",
        output_dir=tmp_path,
        width=1600,
        height=2200,
        timeout_seconds=123.0,
        selected_uids=(),
        fallback="none",
        workflow="chembl_baseline",
        pipeline="chembl_assay",
        run_type="backfill",
        run_id="run-123",
        range_hours=12,
    )

    target = rerender_subject._render_dashboard(
        rerender_subject.DashboardRecord(
            uid="bioetl-workflow-overview",
            url="/d/bioetl-workflow-overview/5-workflow",
            title="5. Workflow",
        ),
        config,
    )

    query = parse_qs(urlparse(str(captured["url"])).query)
    assert target == tmp_path / "bioetl-workflow-overview.png"
    assert target.read_bytes() == b"png"
    assert captured["timeout_seconds"] == 123.0
    assert query["timeout"] == ["123"]
    assert query["width"] == ["1600"]
    assert query["height"] == ["2200"]
    assert query["theme"] == ["dark"]
    assert query["var-run_id"] == ["run-123"]
    assert query["var-quarantine_run_id"] == ["run-123"]


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
    assert manifest["requested"] == {
        "viewport": {"width": 1600, "height": 2200},
        "theme": "dark",
        "capture_surface": "full",
        "kiosk_mode": "off",
        "browser_zoom": 100,
    }
    assert manifest["terminal_state_validation"]["status"] == "not-checked"
    assert manifest["scope"] == {
        "workflow": "chembl_target",
        "pipeline": "chembl_target",
        "run_type": "backfill",
        "run_id": "b51986c6-870b-4457-aa70-baedac2710ad",
        "range_hours": 12,
        "variables": {},
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
    assert env["GRAFANA_SCREENSHOT_WIDTH"] == "1600"
    assert env["GRAFANA_SCREENSHOT_HEIGHT"] == "2200"
    assert env["GRAFANA_SCREENSHOT_THEME"] == "dark"
    assert env["GRAFANA_SCREENSHOT_TIMEOUT_MS"] == "45000"
    assert env["GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS"] == "180000"
    assert env["GRAFANA_SCREENSHOT_SETTLE_MS"] == "12000"
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
        selected_uids=("bioetl-dq-v2",),
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
    # Force the tool defaults path: ignore host-local AppData installs.
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
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
    assert "BIOETL_PLAYWRIGHT_PREFER_ISOLATED_RUNTIME" in shell_script
    assert '[[ "${REPO_ROOT}" == /mnt/* ]]' in shell_script
    assert "playwright-runtime" in shell_script
    assert "-type f -o -type l" in shell_script
    assert "ldconfig_output=" in shell_script
    assert '$2 != "(none)"' in shell_script
    assert "grep -Eq 'Candidate: [^(none)]'" not in shell_script
    for package_name in (
        "libatk-bridge2.0-0t64",
        "libatk1.0-0t64",
        "libcups2t64",
        "libasound2t64",
    ):
        assert package_name in shell_script
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
    assert "waitForDashboardContent" in script
    assert "materializeLazyPanels" in script
    assert "settleDashboardAfterViewportChange" in script
    assert script.index("await settleDashboardAfterViewportChange") < script.index(
        "dashboard.terminalStateValidation = await validateDashboardTerminalStates"
    )
    assert "window.scrollTo" in script
    assert "chromium.launch" in script
    assert "headless: true" in script
    assert "page = await context.newPage();" in script
    assert "await page.close();" in script
    assert "GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS" in script
    assert "--expand-collapsed-rows" in script
    assert (
        "const networkIdleTimeoutMs = Math.max(3000, Math.min(CONFIG.timeoutMs, 15000))"
        in script
    )
    assert "requiredNonRowPanels" in script
    assert "validateDashboardTerminalStates" in script
    assert "terminalStateValidation" in script
    assert "requiredTerminalPanelIds" in script
    assert "Math.min(CONFIG.timeoutMs, 60000)" in script
    assert 'refresh: "off"' in script
    assert 'classification: "contradictory"' in script
    assert 'classification: "valid-empty"' in script
    assert "screenshotEvidence" in script
    assert "sha256" in script


def test_playwright_terminal_state_extraction_uses_panel_local_content() -> None:
    script = Path(
        "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
    ).read_text(encoding="utf-8")

    assert '[data-griditem-key="grid-item-${panelId}"]' in script
    assert '[data-testid="data-testid panel content"]' in script
    assert '[class*="panel-loading-bar"]' in script
    assert "hasVisibleMarker(surface, loadingSelector, true)" in script
    assert "hasVisibleMarker(surface, errorSelector, true)" in script
    assert "hasVisibleMarker(content.element, visualSelector)" in script
    assert "cloneNode(true)" not in script
    assert "header.remove()" not in script


def test_playwright_terminal_classifier_uses_leading_state_tokens() -> None:
    node_path = rerender_subject._resolve_node_executable()
    if node_path is None:
        pytest.skip("Node.js is unavailable")
    script_path = Path(
        "scripts/ops/observability/grafana/rerender_grafana_screenshots.cjs"
    ).resolve()
    program = """
const { classifyPanelTerminalEvidence: classify } = require(process.argv[1]);
const cases = [
  ["ERROR — no backend health payload; blank or loading is forbidden", "explicit-error"],
  ["VALID EMPTY — if an error marker is present, treat it as QUERY/DATASOURCE ERROR", "valid-empty"],
  ["UNKNOWN", "incomplete"],
  ["Not resolved — no identity rows", "incomplete"],
  ["TELEMETRY ABSENT · check scrape", "telemetry-absent"],
  ["NO MATCHING SCOPE · reset filters", "not-applicable"],
];
for (const [bodyText, expected] of cases) {
  const actual = classify({
    type: "stat",
    bodyText,
    hasLoadingMarker: false,
    hasErrorIcon: false,
    hasVisualEvidence: false,
  }).classification;
  if (actual !== expected) throw new Error(`${bodyText}: ${actual} != ${expected}`);
}
const contradictory = classify({
  type: "table",
  bodyText: cases[1][0],
  hasLoadingMarker: false,
  hasErrorIcon: true,
  hasVisualEvidence: false,
}).classification;
if (contradictory !== "contradictory") throw new Error(contradictory);
const renderedWithResidualMarker = classify({
  type: "stat",
  bodyText: "0",
  hasLoadingMarker: true,
  hasErrorIcon: false,
  hasVisualEvidence: true,
}).classification;
if (renderedWithResidualMarker !== "healthy") throw new Error(renderedWithResidualMarker);
const markerWithoutEvidence = classify({
  type: "stat",
  bodyText: "",
  hasLoadingMarker: true,
  hasErrorIcon: false,
  hasVisualEvidence: false,
}).classification;
if (markerWithoutEvidence !== "loading") throw new Error(markerWithoutEvidence);
"""
    env = os.environ.copy()
    rerender_subject._apply_playwright_runtime_env(env)

    # Classifier path must not load Playwright. Bound the subprocess so a
    # regression to eager require("playwright") fails fast instead of hanging
    # the whole unit suite (pytest-timeout thread mode cannot always kill it).
    try:
        result = subprocess.run(
            [node_path, "-e", program, str(script_path)],
            check=False,
            capture_output=True,
            text=True,
            cwd=Path.cwd(),
            env=env,
            timeout=15,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(
            "Node classifier probe timed out; the .cjs module likely loads "
            f"Playwright at import time. stdout={exc.stdout!r} stderr={exc.stderr!r}"
        )

    assert result.returncode == 0, result.stderr


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
        selected_uids=("bioetl-dq-v2",),
        fallback="auto",
    )

    result = rerender_subject._run_playwright_process(config)

    assert result == 0
    assert captured["command"] == [
        "/usr/bin/node",
        str(script_path),
        "--width",
        "1600",
        "--height",
        "2200",
        "--theme",
        "dark",
        "--capture-surface",
        "full",
        "--kiosk-mode",
        "off",
        "--browser-zoom",
        "100",
        "--scope-query",
        "from=now-12h&to=now&timezone=UTC&theme=dark",
    ]
    assert captured["kwargs"]["check"] is False
    # Playwright uses a local temp cwd by default (GDrive repo cwd can hang Chromium).
    import tempfile

    assert captured["kwargs"]["cwd"] == tempfile.gettempdir()
    assert "capture_output" not in captured["kwargs"]
    assert captured["kwargs"]["env"]["GRAFANA_BASE_URL"] == "http://localhost:3000"
    assert captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_UIDS"] == "bioetl-dq-v2"
    assert (
        captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS"] == "true"
    )
    assert captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_CAPTURE_SURFACE"] == "full"
    assert captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_KIOSK_MODE"] == "off"
    assert captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_BROWSER_ZOOM"] == "100"
    assert captured["kwargs"]["timeout"] == (
        rerender_subject._playwright_process_timeout_seconds(config)
    )
    assert captured["kwargs"]["timeout"] > 180.0
