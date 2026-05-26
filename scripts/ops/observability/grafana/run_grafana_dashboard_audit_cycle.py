#!/usr/bin/env python3
"""Run the canonical Grafana dashboard audit cycle."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit
from scripts.ops.observability.grafana import (
    check_grafana_dashboard_audit_preflight as preflight,
)
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender,
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
        config.app_base_url,
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


def _run_live_audit(config: AuditCycleConfig) -> int:
    return live_audit.main(
        [
            "--prometheus-base-url",
            config.prometheus_base_url,
            "--app-base-url",
            config.app_base_url,
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
