"""Rerender Grafana dashboard screenshots through the Grafana render API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib import parse
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://localhost:3000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "changeme"
DEFAULT_OUTPUT_DIR = Path("reports/observability/grafana/screenshots")
DEFAULT_WIDTH = 1600
DEFAULT_HEIGHT = 2200
DEFAULT_THEME = "dark"
DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES = Path(
    "/tmp/bioetl-tools/playwright-runtime/node_modules"
)
DEFAULT_TOOL_PLAYWRIGHT_BROWSERS = Path("/tmp/playwright-browsers")
LOCAL_PLAYWRIGHT_LIB_DIR = Path(
    ".cache/grafana-screenshot-runtime/root/usr/lib/x86_64-linux-gnu"
)
DEFAULT_MIN_PLAYWRIGHT_SCREENSHOT_BYTES = 100_000


@dataclass(frozen=True)
class RenderConfig:
    base_url: str
    username: str
    password: str
    service_account_token: str
    output_dir: Path
    width: int
    height: int
    timeout_seconds: float
    selected_uids: tuple[str, ...]
    fallback: str
    theme: str = DEFAULT_THEME
    workflow: str = ""
    pipeline: str = ""
    run_type: str = ""
    run_id: str = ""
    range_hours: int = 12
    expand_collapsed_rows: bool = True


@dataclass(frozen=True)
class DashboardRecord:
    uid: str
    url: str
    title: str


@dataclass(frozen=True)
class DashboardRenderResult:
    uid: str
    url: str
    title: str
    status: str
    screenshot: str | None = None
    error: str | None = None


class RenderApiFailure(RuntimeError):
    """Raised after writing a partial render manifest for failed dashboards."""


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return f"Basic {token}"


def _auth_headers(config: RenderConfig) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.service_account_token:
        headers["Authorization"] = f"Bearer {config.service_account_token}"
    else:
        headers["Authorization"] = _auth_header(config.username, config.password)
    return headers


def _request_json(
    url: str, *, headers: dict[str, str], timeout_seconds: float
) -> object:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_binary(
    url: str, *, headers: dict[str, str], timeout_seconds: float
) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _grafana_slugify(title: str) -> str:
    return parse.quote(
        "-".join(
            chunk
            for chunk in "".join(
                char.lower() if char.isalnum() else "-" for char in title.strip()
            ).split("-")
            if chunk
        )
        or "dashboard",
        safe="",
    )


def _dashboard_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "grafana" / "dashboards"


def _describe_grafana_auth_failure(config: RenderConfig) -> str:
    auth_mode = (
        "service-account token"
        if config.service_account_token
        else f"basic auth for {config.username!r}"
    )
    return (
        "Grafana auth failed for dashboard rendering. Verify GRAFANA_BASE_URL and "
        f"the configured {auth_mode}. If the live instance uses different local "
        "credentials, reload repo env via scripts/ops/support/load_repo_env.sh or "
        "pass --username/--password explicitly."
    )


def _render_failure_hint(config: RenderConfig) -> str:
    settings_url = f"{config.base_url}/api/frontend/settings"
    try:
        payload = _request_json(
            settings_url,
            headers=_auth_headers(config),
            timeout_seconds=config.timeout_seconds,
        )
    except HTTPError as exc:
        if exc.code in {401, 403}:
            return _describe_grafana_auth_failure(config)
        return (
            "Grafana render API failed while probing frontend settings. Verify "
            "grafana-image-renderer health and, if needed, use the Playwright "
            "fallback after installing project-local playwright dependencies."
        )
    except (URLError, json.JSONDecodeError, RuntimeError):
        return (
            "Grafana render API failed. Verify grafana-image-renderer health and, "
            "if needed, use the Playwright fallback after installing project-local "
            "playwright dependencies."
        )
    if not isinstance(payload, dict):
        return (
            "Grafana render API failed and frontend settings were not readable. "
            "Verify grafana-image-renderer or use the Playwright fallback."
        )
    renderer_available = payload.get("rendererAvailable")
    renderer_version = payload.get("rendererVersion")
    return (
        "Grafana render API failed. "
        f"frontend.settings rendererAvailable={renderer_available!r}, "
        f"rendererVersion={renderer_version!r}. "
        "Verify grafana-image-renderer logs plus docker-compose.monitoring.yml "
        "remote renderer settings: GF_RENDERING_RENDERER_TOKEN must match "
        "AUTH_TOKEN, browser flags must use BROWSER_FLAGS, and the renderer "
        "image must be pinned. If the render route still returns 500, use the "
        "Playwright fallback after installing project-local "
        "playwright dependencies."
    )


def _render_failure_message(
    config: RenderConfig,
    *,
    prefix: str,
    auto_fallback: bool,
) -> str:
    """Build a user-facing failure message without blocking auto fallback."""
    if auto_fallback:
        return (
            f"{prefix}. Grafana render API failed. Falling back to Playwright "
            "screenshot capture."
        )
    return f"{prefix}. {_render_failure_hint(config)}"


def _parse_args(argv: list[str] | None) -> RenderConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Render shipped Grafana dashboards into reproducible local screenshots "
            "under reports/observability/grafana/screenshots."
        )
    )
    parser.add_argument(
        "--base-url",
        default=_read_env("GRAFANA_BASE_URL", DEFAULT_BASE_URL),
        help="Grafana base URL. Defaults to GRAFANA_BASE_URL or http://localhost:3000.",
    )
    parser.add_argument(
        "--username",
        default=_read_env("GRAFANA_USERNAME", DEFAULT_USERNAME),
        help="Grafana username. Defaults to GRAFANA_USERNAME or admin.",
    )
    parser.add_argument(
        "--password",
        default=_read_env("GRAFANA_PASSWORD", DEFAULT_PASSWORD),
        help="Grafana password. Defaults to GRAFANA_PASSWORD or changeme.",
    )
    parser.add_argument(
        "--service-account-token",
        default=_read_env("GRAFANA_SERVICE_ACCOUNT_TOKEN", ""),
        help=(
            "Optional Grafana service-account token. When set, render/auth probes "
            "use Bearer auth instead of username/password."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Screenshot output directory.",
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument(
        "--theme",
        choices=("dark", "light"),
        default=DEFAULT_THEME,
        help="Explicit Grafana color theme for reproducible render evidence.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request timeout for search/render requests.",
    )
    parser.add_argument(
        "--uids",
        nargs="*",
        default=(),
        help="Optional whitelist of dashboard UIDs to render.",
    )
    parser.add_argument(
        "--fallback",
        choices=("auto", "playwright", "none"),
        default="auto",
        help=(
            "Fallback strategy when Grafana render API fails. "
            "'auto' uses Playwright if available, 'playwright' forces the "
            "browser path, 'none' disables fallback."
        ),
    )
    parser.add_argument("--var-workflow", default="")
    parser.add_argument("--var-pipeline", default="")
    parser.add_argument("--var-run-type", default="")
    parser.add_argument("--var-run-id", default="")
    parser.add_argument("--range-hours", type=int, default=12)
    parser.add_argument(
        "--expand-collapsed-rows",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Expand every collapsed row before terminal-state validation. "
            "Enabled by default for full-surface audit evidence."
        ),
    )
    args = parser.parse_args(argv)
    return RenderConfig(
        base_url=args.base_url.rstrip("/"),
        username=args.username,
        password=args.password,
        service_account_token=args.service_account_token,
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        timeout_seconds=args.timeout_seconds,
        selected_uids=tuple(str(uid) for uid in args.uids),
        fallback=args.fallback,
        theme=args.theme,
        workflow=str(args.var_workflow).strip(),
        pipeline=str(args.var_pipeline).strip(),
        run_type=str(args.var_run_type).strip(),
        run_id=str(args.var_run_id).strip(),
        range_hours=max(int(args.range_hours), 1),
        expand_collapsed_rows=bool(args.expand_collapsed_rows),
    )


def _load_dashboards(config: RenderConfig) -> list[DashboardRecord]:
    items: list[DashboardRecord] = []
    for dashboard_path in sorted(_dashboard_dir().glob("*.json")):
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Could not read local dashboard definition {dashboard_path}: {exc}"
            ) from exc
        uid = payload.get("uid")
        title = payload.get("title")
        if not isinstance(uid, str) or not uid.strip():
            continue
        if config.selected_uids and uid not in config.selected_uids:
            continue
        items.append(
            DashboardRecord(
                uid=uid,
                url=f"/d/{uid}/{_grafana_slugify(title if isinstance(title, str) else uid)}",
                title=title if isinstance(title, str) else uid,
            )
        )
    return sorted(items, key=lambda item: item.uid)


def _scope_query_params(config: RenderConfig) -> dict[str, str]:
    params: dict[str, str] = {
        "from": f"now-{config.range_hours}h",
        "to": "now",
        "timezone": "UTC",
        "theme": config.theme,
    }
    if config.workflow:
        params["var-workflow"] = config.workflow
    if config.pipeline:
        params["var-pipeline"] = config.pipeline
    if config.run_type:
        params["var-run_type"] = config.run_type
    if config.run_id:
        params["var-run_id"] = config.run_id
        if config.run_id != "-":
            params["var-quarantine_run_id"] = config.run_id
    return params


def _render_dashboard(record: DashboardRecord, config: RenderConfig) -> Path:
    render_path = "/render" + record.url
    query = urlencode(
        {
            "width": config.width,
            "height": config.height,
            "tz": "UTC",
            "timeout": max(int(config.timeout_seconds), 1),
            **_scope_query_params(config),
        }
    )
    render_url = f"{config.base_url}{render_path}?{query}"
    target = config.output_dir / f"{record.uid}.png"
    target.write_bytes(
        _download_binary(
            render_url,
            headers=_auth_headers(config),
            timeout_seconds=config.timeout_seconds,
        )
    )
    return target


def _write_manifest(
    config: RenderConfig,
    *,
    rendered: list[tuple[DashboardRecord, Path]],
    results: list[DashboardRenderResult] | None = None,
) -> None:
    render_results = results or [
        DashboardRenderResult(
            uid=record.uid,
            url=record.url,
            title=record.title,
            status="rendered",
            screenshot=str(path.relative_to(config.output_dir)),
        )
        for record, path in rendered
    ]
    actual_viewports = {record.uid: _png_dimensions(path) for record, path in rendered}
    manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "base_url": config.base_url,
        "engine": "grafana-render-api",
        "width": config.width,
        "height": config.height,
        "requested": {
            "viewport": {"width": config.width, "height": config.height},
            "theme": config.theme,
        },
        "actual": {
            "viewports": {
                uid: ({"width": size[0], "height": size[1]} if size else None)
                for uid, size in actual_viewports.items()
            },
            "themes": {record.uid: "unverified" for record, _path in rendered},
        },
        "terminal_state_validation": {
            "status": "not-checked",
            "reason": (
                "Grafana Render API captures pixels but cannot prove panel terminal "
                "states; use --fallback playwright for auditable evidence."
            ),
        },
        "selected_uids": list(config.selected_uids),
        "scope": {
            "workflow": config.workflow,
            "pipeline": config.pipeline,
            "run_type": config.run_type,
            "run_id": config.run_id,
            "range_hours": config.range_hours,
        },
        "dashboards": [
            {
                **asdict(record),
                "screenshot": str(path.relative_to(config.output_dir)),
            }
            for record, path in rendered
        ],
        "render_results": [asdict(result) for result in render_results],
    }
    (config.output_dir / "render-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    """Return PNG IHDR dimensions without requiring an image dependency."""
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _playwright_script_path() -> Path:
    return Path(__file__).with_suffix(".cjs")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _path_has_playwright_package(path: Path) -> bool:
    return (path / "playwright" / "package.json").exists()


def _default_playwright_node_modules() -> str:
    configured = os.getenv("BIOETL_PLAYWRIGHT_NODE_MODULES", "").strip()
    if configured:
        return configured
    repo_node_modules = _repo_root() / "node_modules"
    if _path_has_playwright_package(repo_node_modules):
        return str(repo_node_modules)
    if _path_has_playwright_package(DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES):
        return str(DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES)
    return ""


def _default_playwright_browsers_path() -> str:
    configured = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured:
        return configured
    if DEFAULT_TOOL_PLAYWRIGHT_BROWSERS.exists():
        return str(DEFAULT_TOOL_PLAYWRIGHT_BROWSERS)
    return ""


def _default_playwright_library_path() -> str:
    configured = os.getenv("BIOETL_PLAYWRIGHT_LIBRARY_PATH", "").strip()
    if configured:
        return configured
    candidate = _repo_root() / LOCAL_PLAYWRIGHT_LIB_DIR
    if candidate.exists():
        return str(candidate)
    return ""


def _prepend_path_env(env: dict[str, str], name: str, value: str) -> None:
    if not value:
        return
    current_value = env.get(name, "").strip()
    paths = [item for item in current_value.split(os.pathsep) if item]
    if value not in paths:
        env[name] = f"{value}{os.pathsep}{current_value}" if current_value else value


def _apply_playwright_runtime_env(env: dict[str, str]) -> None:
    extra_node_modules = _default_playwright_node_modules()
    if extra_node_modules:
        env["BIOETL_PLAYWRIGHT_NODE_MODULES"] = extra_node_modules
        _prepend_path_env(env, "NODE_PATH", extra_node_modules)

    browsers_path = _default_playwright_browsers_path()
    if browsers_path:
        env["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path

    library_path = _default_playwright_library_path()
    if library_path:
        env["BIOETL_PLAYWRIGHT_LIBRARY_PATH"] = library_path
        _prepend_path_env(env, "LD_LIBRARY_PATH", library_path)


def _resolve_node_executable() -> str | None:
    direct = shutil.which("node")
    if direct:
        return direct

    repo_root = _repo_root()
    candidates = [
        repo_root / "node_modules" / ".bin" / "node",
        repo_root / "node_modules" / ".bin" / "node.cmd",
        repo_root / "node_modules" / ".bin" / "node.exe",
        Path("C:/Program Files/nodejs/node.exe"),
        Path("C:/Program Files (x86)/nodejs/node.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def _playwright_env(config: RenderConfig) -> dict[str, str]:
    env = os.environ.copy()
    env["GRAFANA_BASE_URL"] = config.base_url
    env["GRAFANA_USERNAME"] = config.username
    env["GRAFANA_PASSWORD"] = config.password
    if config.service_account_token:
        env["GRAFANA_SERVICE_ACCOUNT_TOKEN"] = config.service_account_token
    env["GRAFANA_SCREENSHOT_OUTPUT_DIR"] = str(config.output_dir)
    env["GRAFANA_SCREENSHOT_WIDTH"] = str(config.width)
    env["GRAFANA_SCREENSHOT_HEIGHT"] = str(config.height)
    env["GRAFANA_SCREENSHOT_THEME"] = config.theme
    env["GRAFANA_SCREENSHOT_TIMEOUT_MS"] = str(int(config.timeout_seconds * 1000))
    env["GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS"] = str(
        max(int(config.timeout_seconds * 1000), 180000)
    )
    env["GRAFANA_SCREENSHOT_SETTLE_MS"] = os.environ.get(
        "GRAFANA_SCREENSHOT_SETTLE_MS", "12000"
    )
    env["GRAFANA_SCREENSHOT_EXPAND_COLLAPSED_ROWS"] = (
        "true" if config.expand_collapsed_rows else "false"
    )
    if config.selected_uids:
        env["GRAFANA_SCREENSHOT_UIDS"] = ",".join(config.selected_uids)
    scope_query = urlencode(_scope_query_params(config))
    if scope_query:
        env["GRAFANA_SCREENSHOT_SCOPE_QUERY"] = scope_query
    _apply_playwright_runtime_env(env)
    return env


def _run_playwright_process(config: RenderConfig) -> int:
    script_path = _playwright_script_path()
    if not script_path.exists():
        print(f"Playwright fallback script not found: {script_path}")
        return 1
    node_path = _resolve_node_executable()
    if node_path is None:
        print(
            "Playwright fallback requires Node.js. Checked PATH, "
            "repo-local node_modules/.bin, and standard Windows nodejs install paths."
        )
        return 1
    node_command = [node_path, str(script_path)]
    node_command.extend(
        [
            "--width",
            str(config.width),
            "--height",
            str(config.height),
            "--theme",
            config.theme,
        ]
    )
    scope_query = urlencode(_scope_query_params(config))
    if scope_query:
        node_command.extend(["--scope-query", scope_query])
    try:
        result = subprocess.run(
            node_command,
            check=False,
            cwd=str(_repo_root()),
            env=_playwright_env(config),
            timeout=_playwright_process_timeout_seconds(config),
        )
    except subprocess.TimeoutExpired as exc:
        print(
            "Playwright fallback timed out after "
            f"{exc.timeout:.0f}s while rendering selected dashboards."
        )
        return 1
    except OSError as exc:
        print(f"Playwright fallback failed to launch: {exc}")
        return 1
    return result.returncode


def _playwright_process_timeout_seconds(config: RenderConfig) -> float:
    """Return an end-to-end budget longer than every browser capture stage."""
    capture_seconds = max(config.timeout_seconds, 180.0)
    return max((4.0 * config.timeout_seconds) + capture_seconds + 90.0, 300.0)


def _read_playwright_manifest(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Could not read Playwright render manifest {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Playwright render manifest {path} is not a JSON object")
    return payload


def _write_merged_playwright_manifest(
    config: RenderConfig, manifests: list[dict[str, Any]]
) -> None:
    dashboards: list[dict[str, Any]] = []
    for manifest in manifests:
        manifest_dashboards = manifest.get("dashboards", [])
        if isinstance(manifest_dashboards, list):
            dashboards.extend(
                item for item in manifest_dashboards if isinstance(item, dict)
            )

    scope_query = urlencode(_scope_query_params(config))
    capture_timeout_ms = max(int(config.timeout_seconds * 1000), 180000)
    terminal_statuses = [
        manifest.get("terminal_state_validation", {}).get("status")
        for manifest in manifests
        if isinstance(manifest.get("terminal_state_validation"), dict)
    ]
    terminal_status = (
        "ok"
        if len(terminal_statuses) == len(manifests)
        and all(status == "ok" for status in terminal_statuses)
        else "error"
    )
    merged = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "engine": "playwright",
        "base_url": config.base_url,
        "scope_query": scope_query,
        "timeout_ms": int(config.timeout_seconds * 1000),
        "capture_timeout_ms": capture_timeout_ms,
        "requested": {
            "viewport": {"width": config.width, "height": config.height},
            "theme": config.theme,
        },
        "actual": {
            "viewports": {
                str(item["uid"]): item.get("actualViewport")
                for item in dashboards
                if isinstance(item.get("uid"), str)
            },
            "themes": {
                str(item["uid"]): item.get("actualTheme")
                for item in dashboards
                if isinstance(item.get("uid"), str)
            },
        },
        "terminal_state_validation": {
            "status": terminal_status,
            "dashboards": {
                str(item["uid"]): item.get("terminalStateValidation", {}).get(
                    "status", "missing"
                )
                for item in dashboards
                if isinstance(item.get("uid"), str)
                and isinstance(item.get("terminalStateValidation"), dict)
            },
        },
        "expand_collapsed_rows": config.expand_collapsed_rows,
        "dashboards": dashboards,
    }
    (config.output_dir / "render-manifest.json").write_text(
        json.dumps(merged, indent=2) + "\n",
        encoding="utf-8",
    )


def _playwright_min_screenshot_bytes() -> int:
    raw_value = os.getenv("GRAFANA_SCREENSHOT_MIN_BYTES", "").strip()
    if not raw_value:
        return DEFAULT_MIN_PLAYWRIGHT_SCREENSHOT_BYTES
    try:
        return max(int(raw_value), 0)
    except ValueError:
        return DEFAULT_MIN_PLAYWRIGHT_SCREENSHOT_BYTES


def _playwright_manifest_has_suspicious_screenshot(
    config: RenderConfig, manifest: dict[str, Any]
) -> bool:
    min_bytes = _playwright_min_screenshot_bytes()
    if min_bytes <= 0:
        return False

    dashboards = manifest.get("dashboards", [])
    if not isinstance(dashboards, list):
        return False

    for dashboard in dashboards:
        if not isinstance(dashboard, dict):
            continue
        rendered_count = dashboard.get("renderedPanelCount", 0)
        if not isinstance(rendered_count, int) or rendered_count <= 0:
            continue
        file_name = dashboard.get("file") or dashboard.get("screenshot")
        if not isinstance(file_name, str) or not file_name:
            continue
        screenshot_path = config.output_dir / file_name
        try:
            screenshot_size = screenshot_path.stat().st_size
        except OSError:
            continue
        if screenshot_size < min_bytes:
            print(
                "Playwright screenshot looks suspiciously small despite "
                f"{rendered_count} rendered panel marker(s): "
                f"{screenshot_path} ({screenshot_size} bytes < {min_bytes})."
            )
            return True
    return False


def _run_playwright_fallback(config: RenderConfig) -> int:
    dashboards = _load_dashboards(config)
    if len(dashboards) <= 1:
        return _run_playwright_process(config)

    manifests: list[dict[str, Any]] = []
    for dashboard in dashboards:
        single_config = replace(config, selected_uids=(dashboard.uid,))
        result = _run_playwright_process(single_config)
        if result != 0:
            return result
        manifest = _read_playwright_manifest(config.output_dir / "render-manifest.json")
        if _playwright_manifest_has_suspicious_screenshot(config, manifest):
            print(
                "Retrying isolated Playwright render once for "
                f"{dashboard.uid} after suspicious screenshot capture."
            )
            time.sleep(2.0)
            result = _run_playwright_process(single_config)
            if result != 0:
                return result
            manifest = _read_playwright_manifest(
                config.output_dir / "render-manifest.json"
            )
        manifests.append(manifest)

    _write_merged_playwright_manifest(config, manifests)
    return 0


def _playwright_runtime_failure_detail(raw_detail: str) -> str:
    detail = raw_detail.strip() or "unknown Playwright runtime failure"
    setup_hint = (
        "Run `bash scripts/ops/observability/grafana/"
        "setup_grafana_screenshot_runtime.sh` to install repo-local "
        "Playwright devDependencies and Chromium runtime."
    )
    if "Cannot find module 'playwright'" in detail:
        return (
            "Playwright npm package is missing from repo-local node_modules. "
            f"{setup_hint} Original probe error: {detail}"
        )
    if (
        "Executable doesn't exist" in detail
        or "browser executable is missing" in detail
    ):
        return (
            "Playwright Chromium browser runtime is missing. "
            f"{setup_hint} Original probe error: {detail}"
        )
    if "error while loading shared libraries" in detail:
        return (
            "Playwright could resolve Chromium but the host is missing required "
            "shared libraries such as libnspr4/libnss3/libasound2. "
            "Install the standard headless Chromium runtime packages, then rerun "
            "the setup script. Original probe error: "
            f"{detail}"
        )
    return f"Playwright runtime probe failed: {detail}"


def check_playwright_runtime(timeout_seconds: float = 30.0) -> tuple[bool, str]:
    node_path = _resolve_node_executable()
    if node_path is None:
        return (
            False,
            "Node.js is unavailable; Playwright fallback cannot launch browser capture.",
        )
    try:
        env = os.environ.copy()
        _apply_playwright_runtime_env(env)
        result = subprocess.run(
            [
                node_path,
                "-e",
                (
                    "const { chromium } = require('playwright');"
                    "(async () => {"
                    " const browser = await chromium.launch({ headless: true });"
                    " process.stdout.write(chromium.executablePath());"
                    " await browser.close();"
                    "})().catch((error) => {"
                    " console.error(String(error && error.message ? error.message : error));"
                    " process.exit(1);"
                    "});"
                ),
            ],
            check=False,
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
            env=env,
            timeout=max(timeout_seconds, 1.0),
        )
    except subprocess.TimeoutExpired as exc:
        return (
            False,
            "Playwright runtime probe timed out after "
            f"{exc.timeout:.0f}s while launching Chromium.",
        )
    except OSError as exc:
        return False, f"Playwright runtime probe failed to launch Node.js: {exc}"
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        if not detail:
            detail = f"exit={result.returncode}"
        return False, _playwright_runtime_failure_detail(detail)
    executable = result.stdout.strip()
    if not executable:
        return False, "Playwright runtime probe returned an empty Chromium path."
    if not Path(executable).exists():
        return (
            False,
            "Playwright browser executable is missing: "
            f"{executable}. Run `bash scripts/ops/observability/grafana/"
            "setup_grafana_screenshot_runtime.sh` or "
            "`PLAYWRIGHT_BROWSERS_PATH=... node node_modules/playwright/cli.js "
            "install chromium`.",
        )
    return True, f"Playwright Chromium available at {executable}"


def _render_via_api(config: RenderConfig) -> None:
    dashboards = _load_dashboards(config)
    if not dashboards:
        raise RuntimeError("No dashboards matched the current render selection")

    rendered: list[tuple[DashboardRecord, Path]] = []
    results: list[DashboardRenderResult] = []
    failures: list[str] = []
    for record in dashboards:
        try:
            target = _render_dashboard(record, config)
        except HTTPError as exc:
            detail = f"HTTP {exc.code} {exc.reason}"
        except URLError as exc:
            detail = f"URL error: {exc.reason}"
        except OSError as exc:
            detail = f"Render request failed: {exc}"
        else:
            rendered.append((record, target))
            results.append(
                DashboardRenderResult(
                    uid=record.uid,
                    url=record.url,
                    title=record.title,
                    status="rendered",
                    screenshot=str(target.relative_to(config.output_dir)),
                )
            )
            print(f"rendered {record.uid} -> {target}")
            continue

        failures.append(f"{record.uid}: {detail}")
        results.append(
            DashboardRenderResult(
                uid=record.uid,
                url=record.url,
                title=record.title,
                status="error",
                error=detail,
            )
        )
        print(f"failed {record.uid}: {detail}")

    _write_manifest(config, rendered=rendered, results=results)
    if failures:
        raise RenderApiFailure(
            "Grafana Render API failed for dashboards: " + "; ".join(failures)
        )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if config.fallback == "playwright":
            return _run_playwright_fallback(config)
        _render_via_api(config)
    except RenderApiFailure as exc:
        print(
            _render_failure_message(
                config,
                prefix=str(exc),
                auto_fallback=config.fallback == "auto",
            )
        )
        if config.fallback == "auto":
            return _run_playwright_fallback(config)
        return 1
    except HTTPError as exc:
        if exc.code == 500:
            print(
                _render_failure_message(
                    config,
                    prefix=f"HTTP error: {exc.code} {exc.reason}",
                    auto_fallback=config.fallback == "auto",
                )
            )
        else:
            print(f"HTTP error: {exc.code} {exc.reason}")
        if config.fallback == "auto":
            return _run_playwright_fallback(config)
        return 1
    except OSError as exc:
        print(
            _render_failure_message(
                config,
                prefix=f"Render request failed: {exc}",
                auto_fallback=config.fallback == "auto",
            )
        )
        if config.fallback == "auto":
            return _run_playwright_fallback(config)
        return 1
    except URLError as exc:
        print(f"URL error: {exc.reason}")
        if config.fallback == "auto":
            print("Falling back to Playwright screenshot capture.")
            return _run_playwright_fallback(config)
        return 1
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
