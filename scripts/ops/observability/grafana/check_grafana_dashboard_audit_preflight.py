#!/usr/bin/env python3
"""Check whether the local stack is ready for a full Grafana dashboard audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
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
        rerender_screenshots._request_json(
            f"{config.base_url}/api/frontend/settings",
            headers=rerender_screenshots._auth_headers(config),
            timeout_seconds=timeout_seconds,
        )
    except error.HTTPError as exc:
        detail = (
            rerender_screenshots._describe_grafana_auth_failure(config)
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


def _check_playwright_runtime(
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> PreflightCheck:
    ok, detail = rerender_screenshots.check_playwright_runtime(timeout_seconds)
    return PreflightCheck(
        name="playwright-runtime",
        status="ok" if ok else "error",
        detail=detail,
    )


def _check_expanded_row_capture(playwright_check: PreflightCheck) -> PreflightCheck:
    """Report whether the full-audit screenshot path can expand collapsed rows."""
    script_path = Path(__file__).resolve().parent / "rerender_grafana_screenshots.cjs"
    if playwright_check.status != "ok":
        return PreflightCheck(
            name="expanded-row-capture",
            status="error",
            detail=(
                "Playwright expanded-row capture is unavailable because "
                f"{playwright_check.name} failed: {playwright_check.detail}"
            ),
        )
    try:
        script = script_path.read_text(encoding="utf-8")
    except OSError as exc:
        return PreflightCheck(
            name="expanded-row-capture",
            status="error",
            detail=f"Playwright renderer script is not readable: {exc}",
        )
    if (
        "expandCollapsedRows" not in script
        or "collapsedRowTitles" not in script
        or "materializeLazyPanels" not in script
    ):
        return PreflightCheck(
            name="expanded-row-capture",
            status="error",
            detail=(
                "Playwright renderer does not advertise collapsed-row expansion "
                "and lazy-panel materialization; "
                "Render API-only evidence is not full-surface UX evidence."
            ),
        )
    return PreflightCheck(
        name="expanded-row-capture",
        status="ok",
        detail=(
            "Playwright renderer expands collapsed dashboard rows by default for "
            "full-state audits and materializes lazy-rendered panels."
        ),
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


def _read_render_manifest(manifest_path: Path) -> tuple[dict[str, object] | None, str]:
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"could not read render manifest {manifest_path}: {exc}"
    if not isinstance(payload, dict):
        return None, f"render manifest {manifest_path} is not a JSON object"
    return payload, ""


def _required_non_row_panel_ids(panels: object) -> tuple[int, ...]:
    panel_ids: list[int] = []
    if not isinstance(panels, list):
        return ()
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        if panel.get("type") == "row":
            panel_ids.extend(_required_non_row_panel_ids(panel.get("panels")))
            continue
        panel_id = panel.get("id")
        if isinstance(panel_id, int):
            panel_ids.append(panel_id)
    return tuple(panel_ids)


def _expected_panel_ids_by_uid(
    pairs: Iterable[tuple[Path, Path, str]],
) -> tuple[dict[str, tuple[int, ...]], str | None]:
    expected: dict[str, tuple[int, ...]] = {}
    for dashboard_path, _screenshot_path, uid in pairs:
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {}, f"could not read dashboard panel contract {dashboard_path}: {exc}"
        if not isinstance(payload, dict):
            return {}, f"dashboard panel contract {dashboard_path} is not an object"
        panel_ids = _required_non_row_panel_ids(payload.get("panels"))
        if len(panel_ids) != len(set(panel_ids)):
            return {}, f"dashboard {uid} contains duplicate non-row panel IDs"
        expected[uid] = panel_ids
    return expected, None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_manifest_render_contract(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    expected_panel_ids: dict[str, tuple[int, ...]] | None = None,
    screenshot_dir: Path | None = None,
) -> str | None:
    requested = manifest.get("requested")
    if not isinstance(requested, dict):
        return "render manifest is missing requested viewport/theme evidence"
    requested_viewport = requested.get("viewport")
    requested_theme = requested.get("theme")
    if not isinstance(requested_viewport, dict):
        return "render manifest requested.viewport is missing"
    requested_width = requested_viewport.get("width")
    requested_height = requested_viewport.get("height")
    if (
        not isinstance(requested_width, int)
        or requested_width <= 0
        or not isinstance(requested_height, int)
        or requested_height <= 0
    ):
        return "render manifest requested.viewport must contain positive width/height"
    if requested_theme not in {"dark", "light"}:
        return "render manifest requested.theme must be dark or light"
    if manifest.get("expand_collapsed_rows") is not True:
        return "render manifest must prove expand_collapsed_rows=true"

    terminal_validation = manifest.get("terminal_state_validation")
    if not isinstance(terminal_validation, dict):
        return "render manifest is missing terminal_state_validation"
    if terminal_validation.get("status") != "ok":
        return (
            "render manifest terminal_state_validation did not pass: "
            f"status={terminal_validation.get('status')!r}"
        )

    dashboard_payload = manifest.get("dashboards")
    if not isinstance(dashboard_payload, list):
        return "render manifest dashboards must be a list"
    dashboards = {
        item.get("uid"): item
        for item in dashboard_payload
        if isinstance(item, dict) and isinstance(item.get("uid"), str)
    }
    for uid in expected_uids:
        dashboard = dashboards.get(uid)
        if not isinstance(dashboard, dict):
            return f"render manifest is missing dashboard evidence for {uid}"
        if dashboard.get("renderStatus") != "rendered":
            return (
                f"render manifest dashboard {uid} is not rendered: "
                f"status={dashboard.get('renderStatus')!r}"
            )
        actual_viewport = dashboard.get("actualViewport")
        if not isinstance(actual_viewport, dict):
            return f"render manifest dashboard {uid} lacks actualViewport"
        actual_width = actual_viewport.get("width")
        actual_height = actual_viewport.get("height")
        if actual_width != requested_width:
            return (
                f"render manifest dashboard {uid} width drift: "
                f"requested={requested_width!r} actual={actual_width!r}"
            )
        if not isinstance(actual_height, int) or actual_height <= 0:
            return f"render manifest dashboard {uid} has invalid actual height"
        if dashboard.get("actualTheme") != requested_theme:
            return (
                f"render manifest dashboard {uid} theme drift: "
                f"requested={requested_theme!r} "
                f"actual={dashboard.get('actualTheme')!r}"
            )

        dashboard_terminal = dashboard.get("terminalStateValidation")
        if not isinstance(dashboard_terminal, dict):
            return f"render manifest dashboard {uid} lacks terminal panel evidence"
        if dashboard_terminal.get("status") != "ok":
            return f"render manifest dashboard {uid} terminal validation failed"
        panel_states = dashboard_terminal.get("panelStates")
        if not isinstance(panel_states, list) or not panel_states:
            return f"render manifest dashboard {uid} has no required panel states"
        allowed_terminal_states = {
            "healthy",
            "explicit-error",
            "valid-empty",
            "telemetry-absent",
            "not-applicable",
            "incomplete",
        }
        invalid_states = [
            state
            for state in panel_states
            if not isinstance(state, dict)
            or state.get("classification") not in allowed_terminal_states
        ]
        if invalid_states:
            panel_ids = ", ".join(
                str(state.get("id")) if isinstance(state, dict) else "unknown"
                for state in invalid_states
            )
            return (
                f"render manifest dashboard {uid} contains non-terminal or "
                f"contradictory required panel(s): {panel_ids}"
            )

        if expected_panel_ids is not None:
            expected_ids = expected_panel_ids.get(uid)
            if expected_ids is None:
                return f"dashboard panel contract is missing for {uid}"
            actual_ids = [
                state.get("id") for state in panel_states if isinstance(state, dict)
            ]
            if any(not isinstance(panel_id, int) for panel_id in actual_ids):
                return f"render manifest dashboard {uid} has non-integer panel IDs"
            if len(actual_ids) != len(set(actual_ids)):
                return f"render manifest dashboard {uid} repeats panel evidence"
            if set(actual_ids) != set(expected_ids):
                missing_ids = sorted(set(expected_ids) - set(actual_ids))
                extra_ids = sorted(set(actual_ids) - set(expected_ids))
                return (
                    f"render manifest dashboard {uid} panel coverage drift: "
                    f"missing={missing_ids} extra={extra_ids}"
                )
            if dashboard_terminal.get("requiredPanelCount") != len(expected_ids):
                return f"render manifest dashboard {uid} requiredPanelCount drift"
            if dashboard_terminal.get("checkedPanelCount") != len(expected_ids):
                return f"render manifest dashboard {uid} checkedPanelCount drift"

        if uid == "bioetl-silver-reject-explorer":
            backend_health = next(
                (
                    state
                    for state in panel_states
                    if isinstance(state, dict) and state.get("id") == 13
                ),
                None,
            )
            if not isinstance(backend_health, dict):
                return "Silver Backend Health panel 13 terminal evidence is missing"
            if backend_health.get("classification") not in {
                "healthy",
                "explicit-error",
                "valid-empty",
            }:
                return (
                    "Silver Backend Health panel 13 is not terminal: "
                    f"{backend_health.get('classification')!r}"
                )

        if screenshot_dir is not None:
            file_name = dashboard.get("file")
            evidence = dashboard.get("screenshotEvidence")
            if file_name != f"{uid}.png" or not isinstance(evidence, dict):
                return f"render manifest dashboard {uid} lacks bound PNG evidence"
            if evidence.get("file") != file_name:
                return f"render manifest dashboard {uid} PNG filename drift"
            screenshot_path = screenshot_dir / file_name
            try:
                screenshot_size = screenshot_path.stat().st_size
            except OSError as exc:
                return f"render manifest dashboard {uid} PNG is unreadable: {exc}"
            dimensions = rerender_screenshots._png_dimensions(screenshot_path)
            if dimensions is None:
                return f"render manifest dashboard {uid} screenshot is not a valid PNG"
            if dimensions[0] != requested_width or dimensions[1] <= 0:
                return (
                    f"render manifest dashboard {uid} PNG dimensions drift: "
                    f"requested_width={requested_width} actual={dimensions}"
                )
            if evidence.get("bytes") != screenshot_size:
                return f"render manifest dashboard {uid} PNG byte-size drift"
            if (
                evidence.get("width") != dimensions[0]
                or evidence.get("height") != dimensions[1]
            ):
                return f"render manifest dashboard {uid} PNG IHDR evidence drift"
            if evidence.get("sha256") != _sha256(screenshot_path):
                return f"render manifest dashboard {uid} PNG sha256 drift"
    return None


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
    pairs = _expected_dashboard_screenshot_pairs(
        screenshot_dir,
        selected_uids=selected_uids,
    )
    expected_panel_ids, panel_contract_error = _expected_panel_ids_by_uid(pairs)
    if panel_contract_error:
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=panel_contract_error,
        )
    for dashboard_path, screenshot_path, uid in pairs:
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
    manifest, manifest_error = _read_render_manifest(manifest_path)
    if manifest is None:
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=manifest_error,
        )
    contract_error = _validate_manifest_render_contract(
        manifest,
        expected_uids=tuple(uid for _dashboard, _screenshot, uid in pairs),
        expected_panel_ids=expected_panel_ids,
        screenshot_dir=screenshot_dir,
    )
    if contract_error:
        return PreflightCheck(
            name="screenshots",
            status="error",
            detail=contract_error,
        )
    return PreflightCheck(
        name="screenshots",
        status="ok",
        detail=(
            f"{manifest_path} and all dashboard PNGs are current; requested/actual "
            "viewport, theme, and required panel terminal states are verified"
        ),
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
    playwright_check = _check_playwright_runtime(timeout_seconds)
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
        playwright_check,
        _check_expanded_row_capture(playwright_check),
    ]

    try:
        resolved_app_base_url = live_audit._resolve_app_base_url(
            live_audit.AuditConfig(
                prometheus_base_url=prometheus_base_url.rstrip("/"),
                app_base_url=app_base_url.rstrip("/"),
                loki_base_url=live_audit.DEFAULT_LOKI_BASE_URL,
                tempo_base_url=live_audit.DEFAULT_TEMPO_BASE_URL,
                grafana_base_url=grafana_base_url.rstrip("/"),
                grafana_username=grafana_username,
                grafana_password=grafana_password,
                workflow=live_audit.DEFAULT_WORKFLOW,
                pipeline=live_audit.DEFAULT_PIPELINE,
                run_type=live_audit.DEFAULT_RUN_TYPE,
                run_id=live_audit.DEFAULT_RUN_ID,
                range_hours=live_audit.DEFAULT_RANGE_HOURS,
                output_path=live_audit.DEFAULT_OUTPUT_PATH,
                request_timeout_seconds=timeout_seconds,
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
            "Check whether Grafana, Prometheus, Quarantine Explorer, Playwright "
            "expanded-row capture, and local screenshot artifacts are ready for "
            "a full dashboard audit."
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
