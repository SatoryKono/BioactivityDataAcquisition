#!/usr/bin/env python3
"""Check whether the local stack is ready for a full Grafana dashboard audit."""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from urllib import error, request

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[4]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_screenshots,
)

DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_GRAFANA_USERNAME = "admin"
DEFAULT_GRAFANA_PASSWORD = "changeme"
DEFAULT_TIMEOUT_SECONDS = 5.0
DEFAULT_SCREENSHOT_DIR = Path("reports/observability/grafana/screenshots")
_DASHBOARD_DIR = Path("grafana/dashboards")


@dataclass(frozen=True)
class PreflightCheck:
    """One preflight readiness verdict."""

    name: str
    status: str
    detail: str


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _fetch_json(url: str, timeout_seconds: float) -> object:
    with request.urlopen(url, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def _check_http_json(
    *,
    name: str,
    url: str,
    timeout_seconds: float,
) -> PreflightCheck:
    try:
        payload = _fetch_json(url, timeout_seconds)
    except error.HTTPError as exc:
        return PreflightCheck(
            name=name,
            status="error",
            detail=f"{url} returned HTTP {exc.code}",
        )
    except Exception as exc:  # pragma: no cover - exercised by callers
        return PreflightCheck(name=name, status="error", detail=f"{url} failed: {exc}")
    if not isinstance(payload, dict):
        return PreflightCheck(
            name=name,
            status="error",
            detail=f"{url} did not return a JSON object",
        )
    return PreflightCheck(name=name, status="ok", detail=f"{url} reachable")


def _check_grafana_render_auth(
    *,
    grafana_base_url: str,
    grafana_username: str,
    grafana_password: str,
    timeout_seconds: float,
) -> PreflightCheck:
    config = rerender_screenshots.RenderConfig(
        base_url=grafana_base_url.rstrip("/"),
        username=grafana_username,
        password=grafana_password,
        service_account_token=_read_env("GRAFANA_SERVICE_ACCOUNT_TOKEN", ""),
        output_dir=DEFAULT_SCREENSHOT_DIR,
        width=rerender_screenshots.DEFAULT_WIDTH,
        height=rerender_screenshots.DEFAULT_HEIGHT,
        timeout_seconds=timeout_seconds,
        selected_uids=(),
        fallback="auto",
    )
    try:
        rerender_screenshots._request_json(  # noqa: SLF001
            f"{config.base_url}/api/frontend/settings",
            headers=rerender_screenshots._auth_headers(config),  # noqa: SLF001
            timeout_seconds=timeout_seconds,
        )
    except error.HTTPError as exc:
        detail = (
            rerender_screenshots._describe_grafana_auth_failure(config)  # noqa: SLF001
            if exc.code in {401, 403}
            else f"{config.base_url}/api/frontend/settings returned HTTP {exc.code}"
        )
        return PreflightCheck(
            name="grafana-render-auth",
            status="error",
            detail=detail,
        )
    except Exception as exc:  # pragma: no cover - exercised by callers
        return PreflightCheck(
            name="grafana-render-auth",
            status="error",
            detail=f"frontend settings probe failed: {exc}",
        )
    return PreflightCheck(
        name="grafana-render-auth",
        status="ok",
        detail="frontend settings auth probe succeeded",
    )


def _check_playwright_runtime() -> PreflightCheck:
    ok, detail = rerender_screenshots.check_playwright_runtime()
    return PreflightCheck(
        name="playwright-runtime",
        status="ok" if ok else "error",
        detail=detail,
    )


def _expected_dashboard_screenshot_pairs(
    screenshot_dir: Path,
    *,
    selected_uids: tuple[str, ...] = (),
) -> list[tuple[Path, Path, str]]:
    pairs: list[tuple[Path, Path, str]] = []
    for dashboard_path in sorted(_DASHBOARD_DIR.glob("*.json")):
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            # Keep preflight resilient when one dashboard JSON is malformed.
            continue
        uid = payload.get("uid")
        if not isinstance(uid, str) or not uid.strip():
            continue
        if selected_uids and uid not in selected_uids:
            continue
        screenshot_path = screenshot_dir / f"{uid}.png"
        pairs.append((dashboard_path, screenshot_path, uid))
    return pairs


def _check_screenshot_artifacts(
    screenshot_dir: Path,
    *,
    selected_uids: tuple[str, ...] = (),
) -> PreflightCheck:
    manifest_path = screenshot_dir / "render-manifest.json"
    if not manifest_path.exists():
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=f"missing manifest: {manifest_path}",
        )

    stale: list[str] = []
    missing: list[str] = []
    for dashboard_path, screenshot_path, uid in _expected_dashboard_screenshot_pairs(
        screenshot_dir,
        selected_uids=selected_uids,
    ):
        if not screenshot_path.exists():
            missing.append(uid)
            continue
        if screenshot_path.stat().st_mtime < dashboard_path.stat().st_mtime:
            stale.append(uid)

    if stale:
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=f"stale dashboard screenshots for: {', '.join(stale)}",
        )
    if missing:
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=f"missing dashboard screenshots for: {', '.join(missing)}",
        )
    return PreflightCheck(
        name="screenshots",
        status="ok",
        detail=f"{manifest_path} and all dashboard PNGs are current",
    )


def run_checks(
    *,
    grafana_base_url: str,
    prometheus_base_url: str,
    app_base_url: str,
    grafana_username: str,
    grafana_password: str,
    timeout_seconds: float,
    screenshot_dir: Path,
    include_screenshot_check: bool = True,
    screenshot_uids: tuple[str, ...] = (),
) -> list[PreflightCheck]:
    checks = [
        _check_http_json(
            name="grafana",
            url=f"{grafana_base_url.rstrip('/')}/api/health",
            timeout_seconds=timeout_seconds,
        ),
        _check_grafana_render_auth(
            grafana_base_url=grafana_base_url,
            grafana_username=grafana_username,
            grafana_password=grafana_password,
            timeout_seconds=timeout_seconds,
        ),
        _check_http_json(
            name="prometheus",
            url=f"{prometheus_base_url.rstrip('/')}/api/v1/status/runtimeinfo",
            timeout_seconds=timeout_seconds,
        ),
        _check_playwright_runtime(),
    ]

    try:
        resolved_app_base_url = live_audit._resolve_app_base_url(  # noqa: SLF001
            live_audit.AuditConfig(
                prometheus_base_url=prometheus_base_url.rstrip("/"),
                app_base_url=app_base_url.rstrip("/"),
                grafana_base_url=grafana_base_url.rstrip("/"),
                grafana_username=grafana_username,
                grafana_password=grafana_password,
                workflow=live_audit.DEFAULT_WORKFLOW,
                pipeline=live_audit.DEFAULT_PIPELINE,
                run_type=live_audit.DEFAULT_RUN_TYPE,
                run_id=live_audit.DEFAULT_RUN_ID,
                range_hours=live_audit.DEFAULT_RANGE_HOURS,
                output_path=live_audit.DEFAULT_OUTPUT_PATH,
            )
        )
        checks.append(
            PreflightCheck(
                name="quarantine-explorer",
                status="ok",
                detail=(
                    f"canonical health probe reachable via {resolved_app_base_url}"
                ),
            )
        )
    except Exception as exc:  # pragma: no cover - exercised by callers
        checks.append(
            PreflightCheck(
                name="quarantine-explorer",
                status="error",
                detail=str(exc),
            )
        )

    if include_screenshot_check:
        checks.append(
            _check_screenshot_artifacts(
                screenshot_dir,
                selected_uids=screenshot_uids,
            )
        )
    return checks


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Check whether Grafana, Prometheus, Quarantine Explorer, and local "
            "screenshot artifacts are ready for a full dashboard audit."
        )
    )
    parser.add_argument(
        "--grafana-base-url",
        default=DEFAULT_GRAFANA_BASE_URL,
        help="Grafana base URL. Default: http://localhost:3000",
    )
    parser.add_argument(
        "--grafana-username",
        default=_read_env("GRAFANA_USERNAME", DEFAULT_GRAFANA_USERNAME),
        help="Grafana username used for datasource discovery.",
    )
    parser.add_argument(
        "--grafana-password",
        default=_read_env("GRAFANA_PASSWORD", DEFAULT_GRAFANA_PASSWORD),
        help="Grafana password used for datasource discovery.",
    )
    parser.add_argument(
        "--prometheus-base-url",
        default=DEFAULT_PROMETHEUS_BASE_URL,
        help="Prometheus base URL. Default: http://localhost:9090",
    )
    parser.add_argument(
        "--app-base-url",
        default=DEFAULT_APP_BASE_URL,
        help="Preferred Quarantine Explorer base URL. Default: http://localhost:8081",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-endpoint timeout.",
    )
    parser.add_argument(
        "--screenshot-dir",
        type=Path,
        default=DEFAULT_SCREENSHOT_DIR,
        help="Directory with render-manifest.json and dashboard PNGs.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full result as JSON.",
    )
    parser.add_argument(
        "--skip-screenshot-check",
        action="store_true",
        help="Skip local PNG/manifest freshness validation.",
    )
    parser.add_argument(
        "--screenshot-uids",
        nargs="*",
        default=(),
        help="Optional whitelist of dashboard UIDs whose screenshots must be current.",
    )
    return parser


def _format_text(checks: Iterable[PreflightCheck]) -> str:
    return "\n".join(
        f"{check.name}: status={check.status} detail={check.detail}" for check in checks
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    checks = run_checks(
        grafana_base_url=args.grafana_base_url,
        prometheus_base_url=args.prometheus_base_url,
        app_base_url=args.app_base_url,
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        timeout_seconds=args.timeout_seconds,
        screenshot_dir=args.screenshot_dir,
        include_screenshot_check=not args.skip_screenshot_check,
        screenshot_uids=tuple(str(uid) for uid in args.screenshot_uids),
    )

    if args.json:
        print(json.dumps({"checks": [asdict(check) for check in checks]}, indent=2))
    else:
        print(_format_text(checks))

    return 0 if all(check.status == "ok" for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default
