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
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://localhost:3000"
DEFAULT_OUTPUT_DIR = Path("reports/observability/grafana/screenshots")
DEFAULT_WIDTH = 1600
DEFAULT_HEIGHT = 2200
DEFAULT_TIMEOUT_SECONDS = 120.0


@dataclass(frozen=True)
class RenderConfig:
    base_url: str
    username: str
    password: str
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


def _request_json(url: str, *, auth_header: str, timeout_seconds: float) -> object:
    request = Request(url, headers={"Authorization": auth_header})
    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _download_binary(url: str, *, auth_header: str, timeout_seconds: float) -> bytes:
    request = Request(url, headers={"Authorization": auth_header})
    with urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _render_failure_hint(config: RenderConfig) -> str:
    settings_url = f"{config.base_url}/api/frontend/settings"
    try:
        payload = _request_json(
            settings_url,
            auth_header=_auth_header(config.username, config.password),
            timeout_seconds=config.timeout_seconds,
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
        default=_read_env("GRAFANA_USERNAME", "admin"),
        help="Grafana username. Defaults to GRAFANA_USERNAME or admin.",
    )
    parser.add_argument(
        "--password",
        default=_read_env("GRAFANA_PASSWORD", "admin"),
        help="Grafana password. Defaults to GRAFANA_PASSWORD or admin.",
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
        output_dir=args.output_dir,
        width=args.width,
        height=args.height,
        timeout_seconds=args.timeout_seconds,
        selected_uids=tuple(str(uid) for uid in args.uids),
        fallback=args.fallback,
    )


def _load_dashboards(config: RenderConfig) -> list[DashboardRecord]:
    search_url = f"{config.base_url}/api/search?type=dash-db"
    payload = _request_json(
        search_url,
        auth_header=_auth_header(config.username, config.password),
        timeout_seconds=config.timeout_seconds,
    )
    if not isinstance(payload, list):
        raise RuntimeError("Grafana search API returned unexpected payload")

    items: list[DashboardRecord] = []
    for item in cast(list[object], payload):
        if not isinstance(item, dict):
            continue
        uid = item.get("uid")
        url = item.get("url")
        title = item.get("title")
        if not isinstance(uid, str) or not isinstance(url, str):
            continue
        if config.selected_uids and uid not in config.selected_uids:
            continue
        items.append(
            DashboardRecord(
                uid=uid,
                url=url,
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
            auth_header=_auth_header(config.username, config.password),
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


def _playwright_env(config: RenderConfig) -> dict[str, str]:
    env = os.environ.copy()
    env["GRAFANA_BASE_URL"] = config.base_url
    env["GRAFANA_USERNAME"] = config.username
    env["GRAFANA_PASSWORD"] = config.password
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
    node_path = shutil.which("node")
    if node_path is None:
        print("Playwright fallback requires 'node' on PATH.")
        return 1
    node_command = ["node", str(script_path)]
    try:
        result = subprocess.run(
            node_command,
            check=False,
            capture_output=True,
            text=True,
            env=_playwright_env(config),
        )
    except OSError as exc:
        print(f"Playwright fallback failed to launch: {exc}")
        return 1
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode


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
