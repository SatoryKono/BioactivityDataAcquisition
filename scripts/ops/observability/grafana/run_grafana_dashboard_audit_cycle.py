#!/usr/bin/env python3
"""Run the canonical Grafana dashboard audit cycle."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[4]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
    src_root_str = str(repo_root / "src")
    if src_root_str not in sys.path:
        sys.path.insert(0, src_root_str)

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    DEFAULT_HEALTH_SERVER_PORT,
    ensure_observability_backend_started,
)

DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_SCREENSHOT_DIR = Path("reports/observability/grafana/screenshots")
DEFAULT_PREFLIGHT_TIMEOUT_SECONDS = 5.0
DEFAULT_RENDER_TIMEOUT_SECONDS = 60.0
DEFAULT_PIPELINE = live_audit.DEFAULT_PIPELINE
DEFAULT_RUN_TYPE = live_audit.DEFAULT_RUN_TYPE
DEFAULT_RANGE_HOURS = live_audit.DEFAULT_RANGE_HOURS


@dataclass(frozen=True)
class AuditCycleConfig:
    grafana_base_url: str
    grafana_username: str
    grafana_password: str
    prometheus_base_url: str
    app_base_url: str
    screenshot_dir: Path
    preflight_timeout_seconds: float
    render_timeout_seconds: float
    ensure_observability_backend: bool
    observability_backend_port: int
    pipeline: str
    run_type: str
    range_hours: int


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the canonical Grafana dashboard audit cycle: service preflight, "
            "screenshot refresh, screenshot freshness re-check, then live panel audit."
        )
    )
    parser.add_argument("--grafana-base-url", default=DEFAULT_GRAFANA_BASE_URL)
    parser.add_argument(
        "--grafana-username",
        default=preflight._read_env("GRAFANA_USERNAME", preflight.DEFAULT_GRAFANA_USERNAME),  # noqa: SLF001
    )
    parser.add_argument(
        "--grafana-password",
        default=preflight._read_env("GRAFANA_PASSWORD", preflight.DEFAULT_GRAFANA_PASSWORD),  # noqa: SLF001
    )
    parser.add_argument("--prometheus-base-url", default=DEFAULT_PROMETHEUS_BASE_URL)
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument("--screenshot-dir", type=Path, default=DEFAULT_SCREENSHOT_DIR)
    parser.add_argument(
        "--preflight-timeout-seconds",
        type=float,
        default=DEFAULT_PREFLIGHT_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--render-timeout-seconds",
        type=float,
        default=DEFAULT_RENDER_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--ensure-observability-backend",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Auto-start or reuse a detached Quarantine Explorer backend before audit.",
    )
    parser.add_argument(
        "--observability-backend-port",
        type=int,
        default=DEFAULT_HEALTH_SERVER_PORT,
        help="Port for the detached Quarantine Explorer backend.",
    )
    parser.add_argument("--pipeline", default=DEFAULT_PIPELINE)
    parser.add_argument("--run-type", default=DEFAULT_RUN_TYPE)
    parser.add_argument("--range-hours", type=int, default=DEFAULT_RANGE_HOURS)
    return parser


def _parse_args(argv: list[str] | None) -> AuditCycleConfig:
    args = _build_parser().parse_args(argv)
    return AuditCycleConfig(
        grafana_base_url=args.grafana_base_url.rstrip("/"),
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        prometheus_base_url=args.prometheus_base_url.rstrip("/"),
        app_base_url=args.app_base_url.rstrip("/"),
        screenshot_dir=args.screenshot_dir,
        preflight_timeout_seconds=args.preflight_timeout_seconds,
        render_timeout_seconds=args.render_timeout_seconds,
        ensure_observability_backend=args.ensure_observability_backend,
        observability_backend_port=args.observability_backend_port,
        pipeline=args.pipeline,
        run_type=args.run_type,
        range_hours=args.range_hours,
    )


def _run_preflight(config: AuditCycleConfig, *, include_screenshot_check: bool) -> int:
    argv = [
        "--grafana-base-url",
        config.grafana_base_url,
        "--grafana-username",
        config.grafana_username,
        "--grafana-password",
        config.grafana_password,
        "--prometheus-base-url",
        config.prometheus_base_url,
        "--app-base-url",
        f"http://127.0.0.1:{config.observability_backend_port}",
        "--timeout-seconds",
        str(config.preflight_timeout_seconds),
        "--screenshot-dir",
        str(config.screenshot_dir),
    ]
    if not include_screenshot_check:
        argv.append("--skip-screenshot-check")
    return preflight.main(argv)


def _run_rerender(config: AuditCycleConfig) -> int:
    return rerender.main(
        [
            "--base-url",
            config.grafana_base_url,
            "--username",
            config.grafana_username,
            "--password",
            config.grafana_password,
            "--output-dir",
            str(config.screenshot_dir),
            "--timeout-seconds",
            str(config.render_timeout_seconds),
            "--fallback",
            "auto",
        ]
    )


def _ensure_backend(config: AuditCycleConfig) -> int:
    result = ensure_observability_backend_started(
        enabled=config.ensure_observability_backend,
        port=config.observability_backend_port,
    )
    if config.ensure_observability_backend and not result.backend_available:
        print(
            "grafana-audit-cycle: observability backend is not ready "
            f"({result.message or result.status})"
        )
        return 1
    return 0


def _run_live_audit(config: AuditCycleConfig) -> int:
    return live_audit.main(
        [
            "--prometheus-base-url",
            config.prometheus_base_url,
            "--app-base-url",
            f"http://127.0.0.1:{config.observability_backend_port}",
            "--grafana-base-url",
            config.grafana_base_url,
            "--grafana-username",
            config.grafana_username,
            "--grafana-password",
            config.grafana_password,
            "--pipeline",
            config.pipeline,
            "--run-type",
            config.run_type,
            "--range-hours",
            str(config.range_hours),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)

    print("grafana-audit-cycle: ensure observability backend")
    backend_status = _ensure_backend(config)
    if backend_status != 0:
        return backend_status

    print("grafana-audit-cycle: preflight (services only)")
    preflight_status = _run_preflight(config, include_screenshot_check=False)
    if preflight_status != 0:
        return preflight_status

    print("grafana-audit-cycle: rerender screenshots")
    rerender_status = _run_rerender(config)
    if rerender_status != 0:
        return rerender_status

    print("grafana-audit-cycle: preflight (services + screenshot freshness)")
    screenshot_preflight_status = _run_preflight(config, include_screenshot_check=True)
    if screenshot_preflight_status != 0:
        return screenshot_preflight_status

    print("grafana-audit-cycle: live panel audit")
    return _run_live_audit(config)


if __name__ == "__main__":
    raise SystemExit(main())
