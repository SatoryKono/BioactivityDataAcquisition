"""Rerender Grafana dashboard screenshots through the Grafana render API."""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
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
DEFAULT_TIMEOUT_SECONDS = 120.0


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


@dataclass(frozen=True)
class DashboardRecord:
    uid: str
    url: str
    title: str


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def _auth_headers(config: RenderConfig) -> dict[str, str]:
    headers = {"Accept": "application/json"}
    if config.service_account_token:
        headers["Authorization"] = f"Bearer {config.service_account_token}"
    else:
        headers["Authorization"] = _auth_header(config.username, config.password)
    return headers


def _request_json(url: str, *, headers: dict[str, str], timeout_seconds: float) -> object:
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
                char.lower() if char.isalnum() else "-"
                for char in title.strip()
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
    except (HTTPError, URLError, json.JSONDecodeError, RuntimeError):
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
        "Verify grafana-image-renderer logs; if the render route still returns "
        "500, use the Playwright fallback after installing project-local "
        "playwright dependencies."
    )


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


def _render_dashboard(record: DashboardRecord, config: RenderConfig) -> Path:
    render_path = "/render" + record.url
    query = urlencode(
        {
            "width": config.width,
            "height": config.height,
            "tz": "UTC",
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
) -> None:
    manifest = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "base_url": config.base_url,
        "width": config.width,
        "height": config.height,
        "selected_uids": list(config.selected_uids),
        "dashboards": [
            {
                **asdict(record),
                "screenshot": str(path.relative_to(config.output_dir)),
            }
            for record, path in rendered
        ],
    }
    (config.output_dir / "render-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _playwright_script_path() -> Path:
    return Path(__file__).with_suffix(".cjs")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


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
    env["GRAFANA_SCREENSHOT_TIMEOUT_MS"] = str(int(config.timeout_seconds * 1000))
    env["GRAFANA_SCREENSHOT_CAPTURE_TIMEOUT_MS"] = str(
        max(int(config.timeout_seconds * 1000), 180000)
    )
    if config.selected_uids:
        env["GRAFANA_SCREENSHOT_UIDS"] = ",".join(config.selected_uids)
    return env


def _run_playwright_fallback(config: RenderConfig) -> int:
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
    try:
        result = subprocess.run(
            node_command,
            check=False,
            cwd=str(_repo_root()),
            env=_playwright_env(config),
        )
    except OSError as exc:
        print(f"Playwright fallback failed to launch: {exc}")
        return 1
    return result.returncode


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
    if "Executable doesn't exist" in detail or "browser executable is missing" in detail:
        return (
            "Playwright Chromium browser runtime is missing. "
            f"{setup_hint} Original probe error: {detail}"
        )
    return f"Playwright runtime probe failed: {detail}"


def check_playwright_runtime() -> tuple[bool, str]:
    node_path = _resolve_node_executable()
    if node_path is None:
        return (
            False,
            "Node.js is unavailable; Playwright fallback cannot launch browser capture.",
        )
    try:
        result = subprocess.run(
            [
                node_path,
                "-e",
                (
                    "const { chromium } = require('playwright');"
                    "process.stdout.write(chromium.executablePath());"
                ),
            ],
            check=False,
            cwd=str(_repo_root()),
            capture_output=True,
            text=True,
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
    for record in dashboards:
        target = _render_dashboard(record, config)
        rendered.append((record, target))
        print(f"rendered {record.uid} -> {target}")
    _write_manifest(config, rendered=rendered)


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    config.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if config.fallback == "playwright":
            return _run_playwright_fallback(config)
        _render_via_api(config)
    except HTTPError as exc:
        if exc.code == 500:
            print(
                f"HTTP error: {exc.code} {exc.reason}. {_render_failure_hint(config)}"
            )
        else:
            print(f"HTTP error: {exc.code} {exc.reason}")
        if config.fallback == "auto":
            print("Falling back to Playwright screenshot capture.")
            return _run_playwright_fallback(config)
        return 1
    except OSError as exc:
        print(f"Render request failed: {exc}. {_render_failure_hint(config)}")
        if config.fallback == "auto":
            print("Falling back to Playwright screenshot capture.")
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
