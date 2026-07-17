from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import audit_live_grafana_panels as audit_subject
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
    }
    assert manifest["terminal_state_validation"]["status"] == "not-checked"
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
    assert "-type f -o -type l" in shell_script
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
    assert "const browser = await chromium.launch({ headless: true });" in script
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
    assert "bioetl-silver-reject-explorer" in script
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

    result = subprocess.run(
        [node_path, "-e", program, str(script_path)],
        check=False,
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        env=env,
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
        "--scope-query",
        "from=now-12h&to=now&timezone=UTC&theme=dark",
    ]
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["cwd"] == str(tmp_path)
    assert "capture_output" not in captured["kwargs"]
    assert captured["kwargs"]["env"]["GRAFANA_BASE_URL"] == "http://localhost:3000"
    assert captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_UIDS"] == "bioetl-dq-v2"
    assert (
        captured["kwargs"]["env"]["GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS"] == "true"
    )
    assert captured["kwargs"]["timeout"] == (
        rerender_subject._playwright_process_timeout_seconds(config)
    )
    assert captured["kwargs"]["timeout"] > 180.0


def test_rerender_playwright_fallback_splits_and_merges_multi_dashboard_runs(
    monkeypatch: Any, tmp_path: Path
) -> None:
    script_path = tmp_path / "rerender_grafana_screenshots.cjs"
    script_path.write_text("// noop\n", encoding="utf-8")
    calls: list[str] = []

    class _Result:
        returncode = 0

    monkeypatch.setattr(
        rerender_subject, "_playwright_script_path", lambda: script_path
    )
    monkeypatch.setattr(
        rerender_subject, "_resolve_node_executable", lambda: "/usr/bin/node"
    )
    monkeypatch.setattr(rerender_subject, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        rerender_subject,
        "_load_dashboards",
        lambda _config: [
            rerender_subject.DashboardRecord(
                uid="bioetl-provider-health-v2",
                url="/d/bioetl-provider-health-v2/3-provider-health",
                title="3. Provider Health",
            ),
            rerender_subject.DashboardRecord(
                uid="bioetl-runtime",
                url="/d/bioetl-runtime/2-runtime",
                title="2. Runtime",
            ),
        ],
    )

    def fake_run(command: list[str], **kwargs: object) -> _Result:
        env = kwargs["env"]
        assert isinstance(env, dict)
        uid = str(env["GRAFANA_SCREENSHOT_UIDS"])
        calls.append(uid)
        png = (
            b"\x89PNG\r\n\x1a\n"
            + b"\x00\x00\x00\rIHDR"
            + (1600).to_bytes(4, "big")
            + (2200).to_bytes(4, "big")
        )
        (tmp_path / f"{uid}.png").write_bytes(png)
        (tmp_path / "render-manifest.json").write_text(
            json.dumps(
                {
                    "engine": "playwright",
                    "terminal_state_validation": {"status": "ok"},
                    "dashboards": [
                        {
                            "uid": uid,
                            "title": uid,
                            "file": f"{uid}.png",
                            "renderedPanelCount": 1,
                            "renderStatus": "rendered",
                            "actualViewport": {"width": 1600, "height": 2200},
                            "actualTheme": "dark",
                            "screenshotEvidence": {
                                "file": f"{uid}.png",
                                "bytes": len(png),
                                "width": 1600,
                                "height": 2200,
                                "sha256": "test-digest",
                            },
                            "terminalStateValidation": {
                                "status": "ok",
                                "panelStates": [{"id": 1, "classification": "healthy"}],
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
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
    assert calls == ["bioetl-provider-health-v2", "bioetl-runtime"]
    merged = json.loads((tmp_path / "render-manifest.json").read_text())
    assert merged["engine"] == "playwright"
    assert [item["uid"] for item in merged["dashboards"]] == calls
    assert merged["requested"] == {
        "viewport": {"width": 1600, "height": 2200},
        "theme": "dark",
    }
    assert merged["terminal_state_validation"]["status"] == "ok"


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


def test_rerender_auto_fallback_skips_frontend_probe_on_render_failure(
    monkeypatch: Any, tmp_path: Path
) -> None:
    monkeypatch.setattr(rerender_subject, "_load_dashboards", lambda *_: [])
    monkeypatch.setattr(
        rerender_subject,
        "_render_via_api",
        lambda *_: (_ for _ in ()).throw(URLError("timed out")),
    )
    monkeypatch.setattr(rerender_subject, "_run_playwright_fallback", lambda *_: 0)

    def fail_if_probed(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("frontend settings probe should be skipped")

    monkeypatch.setattr(rerender_subject, "_request_json", fail_if_probed)

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
    assert covered[("bioetl-dq-v2", 8)] == (
        "Time Range · Worst Freshness Age (hours; SLA 24/72)"
    )
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


@pytest.mark.parametrize(
    ("panel_id", "title", "expr"),
    [
        (
            8,
            "Time Range · Worst Freshness Age (hours; SLA 24/72)",
            "(max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds"
            '{pipeline=~"$pipeline"}[$__range]), 0))) / 3600',
        ),
        (
            101,
            "Review: Latest Successful Data Timestamp",
            "max(max_over_time(bioetl_data_freshness_seconds"
            '{pipeline=~"$pipeline"}[$__range])) * 1000',
        ),
    ],
)
def test_live_audit_treats_missing_freshness_as_explicit_telemetry_gap(
    monkeypatch: Any,
    panel_id: int,
    title: str,
    expr: str,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-dq-v2",
        panel_id=panel_id,
        title=title,
        source_kind="prometheus",
        semantic_kind="freshness",
    )
    panel = {"targets": [{"expr": expr}]}
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="smoke",
        pipeline="chembl_activity",
        run_type="incremental",
        run_id="audit-run",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        },
    )

    result = audit_subject._audit_prometheus_panel(spec, panel, config)

    assert result.status == "ok"
    assert result.classification == "telemetry_missing"
    assert "UNKNOWN" in result.detail


def test_live_audit_default_timeout_covers_bounded_loki_range_queries() -> None:
    assert audit_subject.DEFAULT_REQUEST_TIMEOUT_SECONDS == 15.0
    assert audit_subject.MAX_LOKI_RANGE_HOURS == 1


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


def test_semantic_gate_maps_unknown_denominator_to_review_required(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-silver-reject-explorer",
        panel_id=3,
        title="Track Reject Rate vs Bronze",
        source_kind="http",
        semantic_kind="http_summary",
        target_ref_id="A",
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification="zero_state_unknown_denominator",
        detail="fixture",
        query_preview="fixture",
        target_ref_id=spec.target_ref_id,
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "review_required"
    assert evidence["review_count"] == 1
    assert evidence["panel_outcomes"][0]["canonical_classification"] == (
        "unknown_result"
    )
    assert evidence["panel_outcomes"][0]["decision"] == "review"


def test_semantic_gate_treats_unregistered_classification_as_review_required(
    monkeypatch: Any,
) -> None:
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=250,
        title="Inspect Warning Logs",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    result = audit_subject.AuditResult(
        dashboard_uid=spec.dashboard_uid,
        panel_id=spec.panel_id,
        title=spec.title,
        source_kind=spec.source_kind,
        semantic_kind=spec.semantic_kind,
        status="ok",
        classification="unregistered_fixture_state",
        detail="fixture",
        query_preview="fixture",
        target_ref_id=spec.target_ref_id,
    )
    monkeypatch.setattr(audit_subject, "effective_panel_specs", lambda: (spec,))

    evidence = audit_subject.semantic_gate_evidence([result])

    assert evidence["status"] == "review_required"
    assert evidence["review_count"] == 1
    assert evidence["unregistered_classification_policy"] == "review_required"
    assert evidence["panel_outcomes"][0]["decision"] == "review"


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
    panel = {
        "targets": [
            {
                "refId": "A",
                "expr": 'count_over_time({job="bioetl"}[$__range])',
            }
        ]
    }
    captured: dict[str, str] = {}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert 0 < timeout_seconds <= config.request_timeout_seconds
        captured["url"] = url
        return {"status": "success", "data": {"result": []}}

    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert "/loki/api/v1/query_range?" in captured["url"]
    assert "start=" in captured["url"]
    assert "end=" in captured["url"]
    assert "limit=100" in captured["url"]
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["query"] == ['count_over_time({job="bioetl"}[1h])']
    assert int(query["end"][0]) - int(query["start"][0]) == 3_600_000_000_000
    assert result.status == "ok"
    assert result.classification == "expected_empty"
    assert "endpoint=query_range" in result.detail
    assert "range_hours=1" in result.detail


def test_live_audit_loki_instant_panel_uses_bounded_query_endpoint(
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
        workflow="chembl_target",
        pipeline="chembl_target",
        run_type="backfill",
        run_id="run-123",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    spec = audit_subject.PanelAuditSpec(
        dashboard_uid="bioetl-runtime",
        panel_id=257,
        title="Inspect Top Warning Events by Event / Logger / Range",
        source_kind="loki",
        semantic_kind="loki_query",
        target_ref_id="A",
    )
    panel = {
        "targets": [
            {
                "refId": "A",
                "expr": 'count_over_time({job="bioetl"}[$__range])',
                "instant": True,
            }
        ]
    }
    captured: dict[str, str] = {}

    def fake_fetch_json(url: str, *, timeout_seconds: float) -> object:
        assert 0 < timeout_seconds <= config.request_timeout_seconds
        captured["url"] = url
        return {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"event": "warning"}, "value": [1, "1"]}],
            },
        }

    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")
    monkeypatch.setattr(audit_subject, "_fetch_json", fake_fetch_json)

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert "/loki/api/v1/query?" in captured["url"]
    assert "/query_range?" not in captured["url"]
    query = parse_qs(urlparse(captured["url"]).query)
    assert query["query"] == ['count_over_time({job="bioetl"}[1h])']
    assert "time" in query
    assert "start" not in query
    assert "end" not in query
    assert result.status == "ok"
    assert result.classification == "nonempty_result"
    assert "endpoint=query" in result.detail


def test_live_audit_loki_panel_fails_when_total_latency_exceeds_budget(
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
    )
    panel = {"targets": [{"refId": "A", "expr": '{job="bioetl"}'}]}
    monotonic_values = iter((100.0, 100.2, 115.2))

    monkeypatch.setattr(audit_subject, "monotonic", lambda: next(monotonic_values))
    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")
    monkeypatch.setattr(
        audit_subject,
        "_fetch_json",
        lambda *_args, **_kwargs: {
            "status": "success",
            "data": {"resultType": "streams", "result": []},
        },
    )

    result = audit_subject._audit_loki_panel(spec, panel, config)

    assert result.status == "error"
    assert result.classification == "timeout_budget_exceeded"
    assert "budget_seconds=15.000" in result.detail


def test_live_audit_loki_fixtures_execute_positive_and_empty_paths(
    monkeypatch: Any,
) -> None:
    fixture_path = Path("tests/fixtures/grafana/loki_runtime_panel_events.jsonl")
    fixtures = {
        item["kind"]: item
        for item in (
            json.loads(line)
            for line in fixture_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    config = audit_subject.AuditConfig(
        prometheus_base_url="http://localhost:9090",
        app_base_url="http://localhost:8081",
        loki_base_url="http://localhost:3100",
        tempo_base_url="http://localhost:3200",
        grafana_base_url="http://localhost:3000",
        grafana_username="admin",
        grafana_password="changeme",
        workflow="chembl_activity",
        pipeline="chembl_activity",
        run_type="backfill",
        run_id="fixture-run",
        range_hours=24,
        output_path=Path("reports/observability/grafana/live-panel-audit.json"),
    )
    monkeypatch.setattr(audit_subject, "_fetch_text", lambda *_args, **_kwargs: "ready")

    positive_cases = (("warning", 250), ("warning", 257), ("malformed", 251))
    for kind, panel_id in positive_cases:
        spec = audit_subject.PanelAuditSpec(
            dashboard_uid="bioetl-runtime",
            panel_id=panel_id,
            title=f"fixture-panel-{panel_id}",
            source_kind="loki",
            semantic_kind="loki_query",
            target_ref_id="A",
        )
        panel = audit_subject._find_panel(spec)
        panel_result = fixtures[kind]["panel_results"][str(panel_id)]
        monkeypatch.setattr(
            audit_subject,
            "_fetch_json",
            lambda *_args, _panel_result=panel_result, **_kwargs: {
                "status": "success",
                "data": _panel_result,
            },
        )

        result = audit_subject._audit_loki_panel(spec, panel, config)

        assert result.status == "ok"
        assert result.classification == "nonempty_result"

    for panel_id in fixtures["empty"]["expected_panel_ids"]:
        spec = audit_subject.PanelAuditSpec(
            dashboard_uid="bioetl-runtime",
            panel_id=panel_id,
            title=f"fixture-panel-{panel_id}",
            source_kind="loki",
            semantic_kind="loki_query",
            target_ref_id="A",
        )
        panel = audit_subject._find_panel(spec)
        panel_result = fixtures["empty"]["panel_results"][str(panel_id)]
        monkeypatch.setattr(
            audit_subject,
            "_fetch_json",
            lambda *_args, _panel_result=panel_result, **_kwargs: {
                "status": "success",
                "data": _panel_result,
            },
        )

        result = audit_subject._audit_loki_panel(spec, panel, config)

        assert result.status == "ok"
        assert result.classification == "expected_empty"


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


def test_live_audit_requires_curated_runtime_loki_panels() -> None:
    required_loki_panel_ids = {
        spec.panel_id
        for spec in audit_subject.effective_panel_specs()
        if spec.dashboard_uid == "bioetl-runtime"
        and spec.source_kind == "loki"
        and spec.required
    }

    assert required_loki_panel_ids == {250, 251, 257}


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

    def walk_panels(panels: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for panel in panels:
            result.append(panel)
            nested = panel.get("panels")
            if isinstance(nested, list):
                result.extend(walk_panels(nested))
        return result

    panel = next(
        panel for panel in walk_panels(dashboard["panels"]) if panel.get("id") == 258
    )
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
