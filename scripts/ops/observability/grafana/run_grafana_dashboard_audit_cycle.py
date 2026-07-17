#!/usr/bin/env python3
"""Run the canonical Grafana dashboard audit cycle."""

from __future__ import annotations

import argparse
import hashlib
import json
import socket
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
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

from bioetl.infrastructure.storage.support.atomic_ops import atomic_write_text
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    DEFAULT_HEALTH_SERVER_PORT,
    DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
    ObservabilityBackendEnsureResult,
    _build_detached_backend_env,
    build_detached_backend_log_path,
    build_observability_backend_health_url,
    drop_listening_backend_on_port,
    ensure_observability_backend_started,
    probe_observability_backend,
    probe_observability_backend_required_paths,
    wait_for_observability_backend_ready,
    wait_for_observability_backend_required_paths_ready,
)

DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_SCREENSHOT_DIR = Path("reports/observability/grafana/screenshots")
DEFAULT_GATE_OUTPUT_PATH = Path(
    "reports/observability/grafana/dashboard-release-gates.json"
)
SHIPPED_DASHBOARD_DIR = (
    Path(__file__).resolve().parents[4] / "grafana" / "dashboards"
).resolve()
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
    gate_output_path: Path
    semantic_output_path: Path
    occurrence_id: str
    preflight_timeout_seconds: float
    render_timeout_seconds: float
    ensure_observability_backend: bool
    refresh_observability_backend: bool
    render_filled_only: bool
    observability_backend_port: int
    pipeline: str
    run_type: str
    workflow: str
    run_id: str
    range_hours: int


@dataclass(frozen=True)
class BackendEnsureOutcome:
    result: ObservabilityBackendEnsureResult
    managed_process: subprocess.Popen[bytes] | None = None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the canonical Grafana dashboard audit cycle: service preflight, "
            "Playwright expanded-row screenshot refresh, screenshot freshness "
            "re-check, then live panel audit."
        )
    )
    parser.add_argument("--grafana-base-url", default=DEFAULT_GRAFANA_BASE_URL)
    parser.add_argument(
        "--grafana-username",
        default=preflight._read_env(
            "GRAFANA_USERNAME", preflight.DEFAULT_GRAFANA_USERNAME
        ),
    )
    parser.add_argument(
        "--grafana-password",
        default=preflight._read_env(
            "GRAFANA_PASSWORD", preflight.DEFAULT_GRAFANA_PASSWORD
        ),
    )
    parser.add_argument("--prometheus-base-url", default=DEFAULT_PROMETHEUS_BASE_URL)
    parser.add_argument("--app-base-url", default=DEFAULT_APP_BASE_URL)
    parser.add_argument("--screenshot-dir", type=Path, default=DEFAULT_SCREENSHOT_DIR)
    parser.add_argument(
        "--gate-output",
        type=Path,
        default=None,
        help=(
            "Write independently reviewable semantic/render gate evidence. "
            "When omitted with a non-default screenshot directory, the gate is "
            "written beside that directory so tests cannot contaminate the "
            "canonical repository report."
        ),
    )
    parser.add_argument(
        "--semantic-output",
        type=Path,
        default=None,
        help="Path for the occurrence-bound live semantic audit artifact.",
    )
    parser.add_argument(
        "--occurrence-id",
        default=None,
        help="Stable identifier shared by semantic, render, and gate artifacts.",
    )
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
    parser.add_argument("--workflow", default=live_audit.DEFAULT_WORKFLOW)
    parser.add_argument("--run-id", default=live_audit.DEFAULT_RUN_ID)
    parser.add_argument("--range-hours", type=int, default=DEFAULT_RANGE_HOURS)
    return parser


def _parse_args(argv: list[str] | None) -> AuditCycleConfig:
    args = _build_parser().parse_args(argv)
    gate_output = args.gate_output
    if gate_output is None:
        gate_output = (
            DEFAULT_GATE_OUTPUT_PATH
            if args.screenshot_dir == DEFAULT_SCREENSHOT_DIR
            else args.screenshot_dir / "dashboard-release-gates.json"
        )
    semantic_output = args.semantic_output
    if semantic_output is None:
        semantic_output = (
            live_audit.DEFAULT_OUTPUT_PATH
            if args.screenshot_dir == DEFAULT_SCREENSHOT_DIR
            else args.screenshot_dir / "live-panel-audit.json"
        )
    return AuditCycleConfig(
        grafana_base_url=args.grafana_base_url.rstrip("/"),
        grafana_username=args.grafana_username,
        grafana_password=args.grafana_password,
        prometheus_base_url=args.prometheus_base_url.rstrip("/"),
        app_base_url=args.app_base_url.rstrip("/"),
        screenshot_dir=args.screenshot_dir,
        gate_output_path=gate_output,
        semantic_output_path=semantic_output,
        occurrence_id=str(args.occurrence_id or uuid.uuid4()),
        preflight_timeout_seconds=args.preflight_timeout_seconds,
        render_timeout_seconds=args.render_timeout_seconds,
        ensure_observability_backend=args.ensure_observability_backend,
        refresh_observability_backend=args.refresh_observability_backend,
        render_filled_only=args.render_filled_only,
        observability_backend_port=args.observability_backend_port,
        pipeline=args.pipeline,
        run_type=args.run_type,
        workflow=args.workflow,
        run_id=args.run_id,
        range_hours=args.range_hours,
    )


def _run_preflight(
    config: AuditCycleConfig,
    *,
    app_base_url: str,
    include_screenshot_check: bool,
    include_render_checks: bool = True,
    include_semantic_checks: bool = True,
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
    if not include_render_checks:
        argv.append("--skip-render-checks")
    if not include_semantic_checks:
        argv.append("--skip-semantic-checks")
    return preflight.main(argv)


def _write_gate_report(
    config: AuditCycleConfig,
    *,
    semantic_status: str,
    render_status: str,
    semantic_detail: str,
    render_detail: str,
) -> bool:
    output_path = _resolve_gate_output_path(config.gate_output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    semantic_source = _artifact_descriptor(
        config.semantic_output_path,
        occurrence_id=config.occurrence_id,
        kind="semantic",
    )
    render_source = _artifact_descriptor(
        config.screenshot_dir / "render-manifest.json",
        occurrence_id=config.occurrence_id,
        kind="render",
    )
    semantic_effective = (
        semantic_status
        if semantic_source["validated"]
        and semantic_source["terminal_status"] == semantic_status
        else "fail"
    )
    render_effective = (
        render_status
        if render_source["validated"]
        and render_source["terminal_status"] == render_status
        else "fail"
    )
    release_passed = semantic_effective == "pass" and render_effective == "pass"
    payload = {
        "schema_version": 2,
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "occurrence_id": config.occurrence_id,
        "source_identity": _git_identity(),
        "scope": {
            "workflow": config.workflow,
            "pipeline": config.pipeline,
            "run_type": config.run_type,
            "run_id": config.run_id,
            "range_hours": config.range_hours,
        },
        "dashboard_semantic_gate": {
            "status": semantic_effective,
            "claimed_status": semantic_status,
            "detail": semantic_detail,
            "source_artifact": semantic_source,
        },
        "dashboard_render_gate": {
            "status": render_effective,
            "claimed_status": render_status,
            "detail": render_detail,
            "source_artifact": render_source,
        },
        "release_passed": release_passed,
    }
    atomic_write_text(
        output_path,
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
    )
    return release_passed


def _git_identity() -> dict[str, str]:
    repo_root = Path(__file__).resolve().parents[4]

    def resolve(revision: str) -> str:
        try:
            completed = subprocess.run(
                ["git", "rev-parse", revision],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "unavailable"
        value = completed.stdout.strip()
        return value if completed.returncode == 0 and value else "unavailable"

    return {"commit": resolve("HEAD"), "tree": resolve("HEAD^{tree}")}


def _artifact_descriptor(
    path: Path,
    *,
    occurrence_id: str,
    kind: str,
) -> dict[str, object]:
    resolved = path.expanduser().resolve()
    descriptor: dict[str, object] = {
        "path": str(resolved),
        "exists": resolved.is_file(),
        "sha256": None,
        "generated_at": None,
        "occurrence_id": None,
        "occurrence_match": False,
        "terminal_status": "fail",
        "dashboard_scope": [],
        "validated": False,
        "manifest_structure_complete": False,
    }
    if not resolved.is_file():
        return descriptor
    try:
        raw = resolved.read_bytes()
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return descriptor
    if not isinstance(payload, dict):
        return descriptor
    descriptor["sha256"] = hashlib.sha256(raw).hexdigest()
    descriptor["generated_at"] = payload.get("generated_at")
    observed_occurrence = str(payload.get("occurrence_id") or "")
    descriptor["occurrence_id"] = observed_occurrence
    descriptor["occurrence_match"] = observed_occurrence == occurrence_id
    if kind == "semantic":
        gate = payload.get("semantic_gate")
        status = str(gate.get("status") or "fail") if isinstance(gate, dict) else "fail"
        descriptor["terminal_status"] = status
        results = payload.get("results")
        if isinstance(results, list):
            descriptor["dashboard_scope"] = sorted(
                {
                    f"{item.get('dashboard_uid')}#{item.get('panel_id')}"
                    for item in results
                    if isinstance(item, dict)
                    and item.get("dashboard_uid")
                    and item.get("panel_id") is not None
                }
            )
    elif kind == "render":
        terminal = payload.get("terminal_state_validation")
        dashboards = payload.get("dashboards")
        terminal_ok = isinstance(terminal, dict) and terminal.get("status") == "ok"
        rendered = (
            isinstance(dashboards, list)
            and bool(dashboards)
            and all(
                isinstance(item, dict) and item.get("renderStatus") == "rendered"
                for item in dashboards
            )
        )
        panel_scope: set[str] = set()
        panel_scope_complete = isinstance(dashboards, list) and bool(dashboards)
        if isinstance(dashboards, list):
            for item in dashboards:
                if not isinstance(item, dict) or not item.get("uid"):
                    panel_scope_complete = False
                    continue
                terminal_validation = item.get("terminalStateValidation")
                if (
                    not isinstance(terminal_validation, dict)
                    or terminal_validation.get("status") != "ok"
                ):
                    panel_scope_complete = False
                    continue
                panel_states = terminal_validation.get("panelStates")
                if not isinstance(panel_states, list) or not panel_states:
                    panel_scope_complete = False
                    continue
                for panel_state in panel_states:
                    panel_id = (
                        panel_state.get("id") if isinstance(panel_state, dict) else None
                    )
                    if panel_id is None:
                        panel_scope_complete = False
                        continue
                    panel_scope.add(f"{item['uid']}#{panel_id}")
        descriptor["dashboard_scope"] = sorted(panel_scope)
        descriptor["terminal_status"] = (
            "pass"
            if terminal_ok and rendered and panel_scope_complete and panel_scope
            else "fail"
        )
    descriptor["validated"] = bool(
        descriptor["occurrence_match"]
        and descriptor["generated_at"]
        and descriptor["sha256"]
        and descriptor["dashboard_scope"]
    )
    return descriptor


def _resolve_gate_output_path(output_path: Path) -> Path:
    resolved = output_path.expanduser().resolve()
    if resolved == SHIPPED_DASHBOARD_DIR or resolved.is_relative_to(
        SHIPPED_DASHBOARD_DIR
    ):
        raise ValueError(
            "Grafana audit gate evidence must not overwrite shipped dashboard JSON: "
            f"{output_path}"
        )
    return resolved


def _run_rerender(config: AuditCycleConfig, *, screenshot_uids: tuple[str, ...]) -> int:
    common_argv = [
        "--base-url",
        config.grafana_base_url,
        "--username",
        config.grafana_username,
        "--password",
        config.grafana_password,
        "--timeout-seconds",
        str(config.render_timeout_seconds),
        "--var-workflow",
        config.workflow,
        "--var-pipeline",
        config.pipeline,
        "--var-run-type",
        config.run_type,
        "--var-run-id",
        config.run_id,
        "--range-hours",
        str(config.range_hours),
        "--occurrence-id",
        config.occurrence_id,
    ]
    if screenshot_uids:
        common_argv.extend(["--uids", *screenshot_uids])

    render_api_argv = [
        *common_argv,
        "--output-dir",
        str(config.screenshot_dir / "render-api"),
        "--fallback",
        "none",
    ]
    render_api_status = rerender.main(render_api_argv)
    if render_api_status != 0:
        print(
            "grafana-audit-cycle: Render API screenshot side-artifact failed; "
            "continuing with canonical Playwright expanded-row capture."
        )

    playwright_argv = [
        *common_argv,
        "--output-dir",
        str(config.screenshot_dir),
        "--fallback",
        "playwright",
    ]
    return rerender.main(playwright_argv)


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


def _start_managed_observability_backend(
    *,
    port: int,
    required_probe_paths: tuple[str, ...],
) -> BackendEnsureOutcome:
    health_url = build_observability_backend_health_url(host="127.0.0.1", port=port)
    repo_root = Path(__file__).resolve().parents[4]
    log_path = build_detached_backend_log_path(port)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write("")
    kwargs: dict[str, object] = {
        "cwd": str(repo_root),
        "env": _build_detached_backend_env(),
        "stdin": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        kwargs["creationflags"] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0))
    with log_path.open("ab") as log_handle:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "bioetl",
                "quarantine",
                "serve",
                "--host",
                "0.0.0.0",
                "--port",
                str(port),
            ],
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            **kwargs,
        )
    ready = wait_for_observability_backend_ready(health_url)
    required_ready = ready and wait_for_observability_backend_required_paths_ready(
        health_url,
        required_probe_paths=required_probe_paths,
        timeout_seconds=DEFAULT_OBSERVABILITY_BACKEND_REQUIRED_PATHS_READY_TIMEOUT_SECONDS,
    )
    if required_ready:
        print(
            "grafana-audit-cycle: managed observability backend is ready at "
            f"{health_url}"
        )
        return BackendEnsureOutcome(
            result=ObservabilityBackendEnsureResult(
                status="started",
                health_url=health_url,
                pid=getattr(process, "pid", None),
                command=(sys.executable, "-m", "bioetl", "quarantine", "serve"),
                message=f"Managed observability backend started at {health_url}.",
            ),
            managed_process=process,
        )
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)
    return BackendEnsureOutcome(
        result=ObservabilityBackendEnsureResult(
            status="failed",
            health_url=health_url,
            pid=getattr(process, "pid", None),
            command=(sys.executable, "-m", "bioetl", "quarantine", "serve"),
            message=f"Managed observability backend did not become ready at {health_url}.",
        ),
        managed_process=None,
    )


def _ensure_backend(config: AuditCycleConfig) -> BackendEnsureOutcome:
    required_probe_paths = (
        "/ops/control-plane/checkpoint-freshness?"
        f"pipeline={config.pipeline}&run_type={config.run_type}&run_id={config.run_id}",
    )
    if config.ensure_observability_backend and config.refresh_observability_backend:
        refreshed = drop_listening_backend_on_port(config.observability_backend_port)
        if not refreshed:
            reused_existing = _reuse_existing_backend_if_healthy(
                config,
                required_probe_paths=required_probe_paths,
            )
            if reused_existing is not None:
                return BackendEnsureOutcome(result=reused_existing)
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
                return BackendEnsureOutcome(result=fallback_result)
            reused_existing = _reuse_existing_backend_if_healthy(
                config,
                required_probe_paths=required_probe_paths,
            )
            if reused_existing is not None:
                return BackendEnsureOutcome(result=reused_existing)
            managed = _start_managed_observability_backend(
                port=config.observability_backend_port,
                required_probe_paths=required_probe_paths,
            )
            if managed.result.backend_available:
                return managed
            managed = _start_managed_observability_backend(
                port=fallback_port,
                required_probe_paths=required_probe_paths,
            )
            return managed
    result = ensure_observability_backend_started(
        enabled=config.ensure_observability_backend,
        port=config.observability_backend_port,
        required_probe_paths=required_probe_paths,
    )
    if result.backend_available or not config.ensure_observability_backend:
        return BackendEnsureOutcome(result=result)

    reused_existing = _reuse_existing_backend_if_healthy(
        config,
        required_probe_paths=required_probe_paths,
    )
    if reused_existing is not None:
        return BackendEnsureOutcome(result=reused_existing)

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
            f"pipeline={config.pipeline}&run_type={config.run_type}&run_id={config.run_id}",
        ),
    )
    if fallback_result.backend_available:
        print(
            "grafana-audit-cycle: observability backend fallback is ready at "
            f"{fallback_result.health_url}"
        )
        return BackendEnsureOutcome(result=fallback_result)
    reused_existing = _reuse_existing_backend_if_healthy(
        config,
        required_probe_paths=required_probe_paths,
    )
    if reused_existing is not None:
        return BackendEnsureOutcome(result=reused_existing)
    managed = _start_managed_observability_backend(
        port=config.observability_backend_port,
        required_probe_paths=required_probe_paths,
    )
    if managed.result.backend_available:
        return managed
    managed = _start_managed_observability_backend(
        port=fallback_port,
        required_probe_paths=required_probe_paths,
    )
    return managed


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
            "--workflow",
            config.workflow,
            "--pipeline",
            config.pipeline,
            "--run-type",
            config.run_type,
            "--run-id",
            config.run_id,
            "--range-hours",
            str(config.range_hours),
            "--output",
            str(config.semantic_output_path),
            "--occurrence-id",
            config.occurrence_id,
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
    payload = json.loads(config.semantic_output_path.read_text(encoding="utf-8"))
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
                loki_base_url=live_audit.DEFAULT_LOKI_BASE_URL,
                tempo_base_url=live_audit.DEFAULT_TEMPO_BASE_URL,
                grafana_base_url=config.grafana_base_url,
                grafana_username=config.grafana_username,
                grafana_password=config.grafana_password,
                workflow=config.workflow,
                pipeline=config.pipeline,
                run_type=config.run_type,
                run_id=config.run_id,
                range_hours=config.range_hours,
                output_path=config.semantic_output_path,
                occurrence_id=config.occurrence_id,
            )
        )
        filled = _filled_dashboard_uids_from_results(results)
        source = "live discovery"
    except (
        FileNotFoundError,
        LookupError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
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
    managed_backend_process: subprocess.Popen[bytes] | None = None

    try:
        print("grafana-audit-cycle: ensure observability backend")
        backend_outcome = _ensure_backend(config)
        backend_result = backend_outcome.result
        managed_backend_process = backend_outcome.managed_process
        backend_ready = (
            not config.ensure_observability_backend or backend_result.backend_available
        )
        if not backend_ready:
            print(
                "grafana-audit-cycle: observability backend is not ready "
                f"({backend_result.message or backend_result.status})"
            )
        app_base_url = (
            _app_base_url_from_health_url(backend_result.health_url)
            if backend_result.health_url
            else config.app_base_url
        )

        print("grafana-audit-cycle: semantic preflight")
        semantic_preflight_status = (
            _run_preflight(
                config,
                app_base_url=app_base_url,
                include_screenshot_check=False,
                include_render_checks=False,
            )
            if backend_ready
            else 1
        )

        screenshot_uids: tuple[str, ...] = ()
        semantic_status_code = 1
        if backend_ready:
            print("grafana-audit-cycle: discover filled dashboards")
            try:
                screenshot_uids = _discover_filled_dashboard_uids(
                    config,
                    app_base_url=app_base_url,
                )
            except (
                FileNotFoundError,
                LookupError,
                OSError,
                TypeError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
                print(f"grafana-audit-cycle: filled-dashboard discovery failed ({exc})")

            print("grafana-audit-cycle: live panel semantic gate")
            try:
                semantic_status_code = _run_live_audit(
                    config,
                    app_base_url=app_base_url,
                )
            except Exception as exc:  # pragma: no cover - fail-closed runtime boundary
                print(f"grafana-audit-cycle: live panel audit failed ({exc})")
        else:
            print(
                "grafana-audit-cycle: semantic discovery/audit skipped because "
                "the required backend is unavailable"
            )
        semantic_status = (
            "pass"
            if backend_ready
            and semantic_preflight_status == 0
            and semantic_status_code == 0
            else "fail"
        )
        semantic_detail = (
            "Semantic preflight and live panel audit passed."
            if semantic_status == "pass"
            else "Semantic preflight or live panel audit reported blocking results."
        )

        print("grafana-audit-cycle: rerender screenshots")
        try:
            rerender_status = _run_rerender(
                config,
                screenshot_uids=screenshot_uids,
            )
        except Exception as exc:  # pragma: no cover - fail-closed runtime boundary
            print(f"grafana-audit-cycle: screenshot rerender failed ({exc})")
            rerender_status = 1

        screenshot_preflight_status = 1
        if rerender_status == 0:
            print("grafana-audit-cycle: render-only preflight")
            screenshot_preflight_status = _run_preflight(
                config,
                app_base_url=app_base_url,
                include_screenshot_check=True,
                include_semantic_checks=False,
                screenshot_uids=screenshot_uids,
            )
        render_status = (
            "pass"
            if rerender_status == 0 and screenshot_preflight_status == 0
            else "fail"
        )
        render_detail = (
            "Screenshot render and manifest contract passed."
            if render_status == "pass"
            else "Screenshot rerender or render-only preflight failed."
        )

        release_passed = _write_gate_report(
            config,
            semantic_status=semantic_status,
            render_status=render_status,
            semantic_detail=semantic_detail,
            render_detail=render_detail,
        )
        return 0 if release_passed else 1
    finally:
        if (
            managed_backend_process is not None
            and managed_backend_process.poll() is None
        ):
            managed_backend_process.terminate()
            try:
                managed_backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                managed_backend_process.kill()
                managed_backend_process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
