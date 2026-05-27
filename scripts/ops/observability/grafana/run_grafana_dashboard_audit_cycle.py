#!/usr/bin/env python3
"""Run the canonical Grafana dashboard audit cycle."""

from __future__ import annotations

import argparse
import json
import socket
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
    ObservabilityBackendEnsureResult,
    build_observability_backend_health_url,
    drop_listening_backend_on_port,
    ensure_observability_backend_started,
    probe_observability_backend,
    probe_observability_backend_required_paths,
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
    refresh_observability_backend: bool
    render_filled_only: bool
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
        "--refresh-observability-backend",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Force-refresh the detached Quarantine Explorer backend before audit so "
            "the cycle does not reuse stale route handlers from an older process."
        ),
    )
    parser.add_argument(
        "--render-filled-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Render screenshots only for dashboards that return reviewed live evidence "
            "during the discovery pass."
        ),
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
        refresh_observability_backend=args.refresh_observability_backend,
        render_filled_only=args.render_filled_only,
        observability_backend_port=args.observability_backend_port,
        pipeline=args.pipeline,
        run_type=args.run_type,
        range_hours=args.range_hours,
    )


def _run_preflight(
    config: AuditCycleConfig,
    *,
    app_base_url: str,
    include_screenshot_check: bool,
    screenshot_uids: tuple[str, ...] = (),
) -> int:
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
        app_base_url,
        "--timeout-seconds",
        str(config.preflight_timeout_seconds),
        "--screenshot-dir",
        str(config.screenshot_dir),
    ]
    if not include_screenshot_check:
        argv.append("--skip-screenshot-check")
    elif screenshot_uids:
        argv.extend(["--screenshot-uids", *screenshot_uids])
    return preflight.main(argv)


def _run_rerender(config: AuditCycleConfig, *, screenshot_uids: tuple[str, ...]) -> int:
    argv = [
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
    if screenshot_uids:
        argv.extend(["--uids", *screenshot_uids])
    return rerender.main(argv)


def _app_base_url_from_health_url(health_url: str) -> str:
    if health_url.endswith("/health"):
        return health_url[: -len("/health")]
    return health_url.rstrip("/")


def _find_available_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _reuse_existing_backend_if_healthy(
    config: AuditCycleConfig,
    *,
    required_probe_paths: tuple[str, ...],
) -> ObservabilityBackendEnsureResult | None:
    existing_health_url = build_observability_backend_health_url(
        host="127.0.0.1",
        port=config.observability_backend_port,
    )
    if probe_observability_backend_required_paths(
        existing_health_url,
        required_probe_paths=required_probe_paths,
    ):
        print(
            "grafana-audit-cycle: existing observability backend on "
            f"{config.observability_backend_port} already exposes required "
            "audit capabilities; reusing it"
        )
        return ObservabilityBackendEnsureResult(
            status="reused",
            health_url=existing_health_url,
            message=(
                "Existing backend could not be refreshed in place but already "
                "exposes required audit capabilities."
            ),
        )
    if not probe_observability_backend(existing_health_url):
        return None
    print(
        "grafana-audit-cycle: fresh observability backend could not be started; "
        f"continuing with health-reachable backend on {config.observability_backend_port}"
    )
    return ObservabilityBackendEnsureResult(
        status="reused",
        health_url=existing_health_url,
        message=(
            "Fresh detached backend could not be started; continuing with the "
            "existing health-reachable backend even though required audit "
            "capabilities were not revalidated."
        ),
    )


def _ensure_backend(config: AuditCycleConfig) -> ObservabilityBackendEnsureResult:
    required_probe_paths = (
        "/ops/control-plane/checkpoint-freshness?"
        f"pipeline={config.pipeline}&run_type={config.run_type}&run_id=-",
    )
    if config.ensure_observability_backend and config.refresh_observability_backend:
        refreshed = drop_listening_backend_on_port(config.observability_backend_port)
        if not refreshed:
            reused_existing = _reuse_existing_backend_if_healthy(
                config,
                required_probe_paths=required_probe_paths,
            )
            if reused_existing is not None:
                return reused_existing
            fallback_port = _find_available_local_port()
            print(
                "grafana-audit-cycle: could not refresh observability backend in place; "
                f"starting on fallback port {fallback_port}"
            )
            fallback_result = ensure_observability_backend_started(
                enabled=True,
                port=fallback_port,
                required_probe_paths=required_probe_paths,
            )
            if fallback_result.backend_available:
                print(
                    "grafana-audit-cycle: observability backend fallback is ready at "
                    f"{fallback_result.health_url}"
                )
                return fallback_result
            reused_existing = _reuse_existing_backend_if_healthy(
                config,
                required_probe_paths=required_probe_paths,
            )
            if reused_existing is not None:
                return reused_existing
            return fallback_result
    result = ensure_observability_backend_started(
        enabled=config.ensure_observability_backend,
        port=config.observability_backend_port,
        required_probe_paths=required_probe_paths,
    )
    if result.backend_available or not config.ensure_observability_backend:
        return result

    reused_existing = _reuse_existing_backend_if_healthy(
        config,
        required_probe_paths=required_probe_paths,
    )
    if reused_existing is not None:
        return reused_existing

    fallback_port = _find_available_local_port()
    print(
        "grafana-audit-cycle: retrying observability backend on fallback port "
        f"{fallback_port}"
    )
    fallback_result = ensure_observability_backend_started(
        enabled=True,
        port=fallback_port,
        required_probe_paths=(
            "/ops/control-plane/checkpoint-freshness?"
            f"pipeline={config.pipeline}&run_type={config.run_type}&run_id=-",
        ),
    )
    if fallback_result.backend_available:
        print(
            "grafana-audit-cycle: observability backend fallback is ready at "
            f"{fallback_result.health_url}"
        )
        return fallback_result
    reused_existing = _reuse_existing_backend_if_healthy(
        config,
        required_probe_paths=required_probe_paths,
    )
    if reused_existing is not None:
        return reused_existing
    return fallback_result


def _run_live_audit(config: AuditCycleConfig, *, app_base_url: str) -> int:
    return live_audit.main(
        [
            "--prometheus-base-url",
            config.prometheus_base_url,
            "--app-base-url",
            app_base_url,
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


def _filled_dashboard_uids_from_results(
    results: list[live_audit.AuditResult],
) -> tuple[str, ...]:
    filled = sorted(
        {
            result.dashboard_uid
            for result in results
            if result.status == "ok" and result.classification != "empty_result"
        }
    )
    return tuple(filled)


def _load_cached_filled_dashboard_uids(config: AuditCycleConfig) -> tuple[str, ...]:
    payload = json.loads(live_audit.DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))
    report_config = payload.get("config")
    if not isinstance(report_config, dict):
        raise ValueError("live-panel-audit cache missing config object")
    if report_config.get("pipeline") != config.pipeline:
        raise ValueError("live-panel-audit cache pipeline does not match current run")
    if report_config.get("run_type") != config.run_type:
        raise ValueError("live-panel-audit cache run_type does not match current run")
    results_payload = payload.get("results")
    if not isinstance(results_payload, list):
        raise ValueError("live-panel-audit cache missing results list")
    results: list[live_audit.AuditResult] = []
    for item in results_payload:
        if not isinstance(item, dict):
            raise ValueError("live-panel-audit cache has non-object result entry")
        results.append(live_audit.AuditResult(**item))
    return _filled_dashboard_uids_from_results(results)


def _discover_filled_dashboard_uids(
    config: AuditCycleConfig,
    *,
    app_base_url: str,
) -> tuple[str, ...]:
    if not config.render_filled_only:
        return ()

    try:
        results = live_audit.run_audit(
            live_audit.AuditConfig(
                prometheus_base_url=config.prometheus_base_url,
                app_base_url=app_base_url,
                grafana_base_url=config.grafana_base_url,
                grafana_username=config.grafana_username,
                grafana_password=config.grafana_password,
                pipeline=config.pipeline,
                run_type=config.run_type,
                range_hours=config.range_hours,
                output_path=live_audit.DEFAULT_OUTPUT_PATH,
            )
        )
        filled = _filled_dashboard_uids_from_results(results)
        source = "live discovery"
    except (FileNotFoundError, LookupError, OSError, ValueError, json.JSONDecodeError) as exc:
        filled = _load_cached_filled_dashboard_uids(config)
        source = f"cached live-panel-audit.json after discovery failure ({exc})"
    print(
        "grafana-audit-cycle: filled dashboards for rerender -> "
        + (", ".join(filled) if filled else "none")
        + f" [{source}]"
    )
    return tuple(filled)


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)

    print("grafana-audit-cycle: ensure observability backend")
    backend_result = _ensure_backend(config)
    if config.ensure_observability_backend and not backend_result.backend_available:
        print(
            "grafana-audit-cycle: observability backend is not ready "
            f"({backend_result.message or backend_result.status})"
        )
        return 1
    app_base_url = _app_base_url_from_health_url(backend_result.health_url)

    print("grafana-audit-cycle: preflight (services only)")
    preflight_status = _run_preflight(
        config,
        app_base_url=app_base_url,
        include_screenshot_check=False,
    )
    if preflight_status != 0:
        return preflight_status

    print("grafana-audit-cycle: discover filled dashboards")
    try:
        screenshot_uids = _discover_filled_dashboard_uids(
            config,
            app_base_url=app_base_url,
        )
    except (FileNotFoundError, LookupError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"grafana-audit-cycle: filled-dashboard discovery failed ({exc})")
        return 1

    print("grafana-audit-cycle: rerender screenshots")
    rerender_status = _run_rerender(config, screenshot_uids=screenshot_uids)
    if rerender_status != 0:
        return rerender_status

    print("grafana-audit-cycle: preflight (services + screenshot freshness)")
    screenshot_preflight_status = _run_preflight(
        config,
        app_base_url=app_base_url,
        include_screenshot_check=True,
        screenshot_uids=screenshot_uids,
    )
    if screenshot_preflight_status != 0:
        return screenshot_preflight_status

    print("grafana-audit-cycle: live panel audit")
    return _run_live_audit(config, app_base_url=app_base_url)


if __name__ == "__main__":
    raise SystemExit(main())
