#!/usr/bin/env python3
"""Check whether the local stack is ready for a full Grafana dashboard audit."""

from __future__ import annotations

# NOSONAR - S1192: *.json pattern is intentional for dashboard file discovery
DASHBOARD_FILE_PATTERN = "*.json"

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib import error, request

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[4]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

from scripts.ops.observability.grafana import audit_live_grafana_panels as live_audit
from scripts.ops.observability.grafana import (
    rerender_grafana_screenshots as rerender_screenshots,
)
from scripts.ops.runtime.docker import docker_runtime_preflight as runtime_preflight
from bioetl.application.services.run_reports.source_identity import (
    IDENTITY_STATE_ALIGNED,
    IDENTITY_STATE_FOREIGN,
    IDENTITY_STATE_INVALID,
    IDENTITY_STATE_MISSING,
    RUNTIME_SOURCE_ID_ENV,
    RuntimeSourceIdentityResolutionResult,
    compare_runtime_source_identity,
    load_repository_source_environment,
    resolve_runtime_source_identity,
)

DEFAULT_GRAFANA_BASE_URL = "http://localhost:3000"
DEFAULT_PROMETHEUS_BASE_URL = "http://localhost:9090"
DEFAULT_OPS_HTTP_BASE_URL = "http://localhost:8000"
DEFAULT_APP_BASE_URL = "http://localhost:8081"
DEFAULT_GRAFANA_USERNAME = "admin"
# Never ship a default password. Prefer env / service-account token.
DEFAULT_GRAFANA_PASSWORD = ""
DEFAULT_TIMEOUT_SECONDS = 5.0
# Chromium launch on cold Windows/WSL hosts often exceeds the short HTTP probe budget.
DEFAULT_PLAYWRIGHT_PROBE_TIMEOUT_SECONDS = 60.0
DEFAULT_SCREENSHOT_DIR = Path("reports/observability/grafana/screenshots")
_DASHBOARD_DIR = Path("grafana/dashboards")
_REPO_ROOT = Path(__file__).resolve().parents[4]

# Distinct non-zero outcomes so operators can separate readiness classes.
EXIT_OK = 0
EXIT_GENERIC = 1
EXIT_GRAFANA_HEALTH = 2
EXIT_RENDER_AUTH = 3
EXIT_PLAYWRIGHT = 4
EXIT_EXPANDED_ROW = 5
EXIT_PROMETHEUS = 6
EXIT_QUARANTINE = 7
EXIT_SCREENSHOTS = 8
EXIT_CREDENTIALS = 9
EXIT_BIOETL_TARGET = 10
EXIT_BIOETL_SOURCE = 11
EXIT_OPS_HTTP_BOOTSTRAP = 12
QUARANTINE_EXPLORER_UID = "bioetl-silver-reject-explorer"
OPS_HTTP_DATASOURCE_UID = "bioetl-ops-http"
GRAFANA_BOOTSTRAP_STATUS_PATH = "/var/lib/grafana/bioetl-bootstrap-status.json"
_RUNTIME_SOURCE_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_MIN_PANEL_BODY_FONT_PX = 16.0
_MIN_PANEL_TITLE_FONT_PX = 14.0 * 4.0 / 3.0
_MIN_GRAFANA_BODY_FONT_PX = 12.0
_MIN_GRAFANA_PANEL_TITLE_FONT_PX = 14.0


@dataclass(frozen=True)
class PreflightCheck:
    """One preflight readiness verdict."""

    name: str
    status: str
    detail: str


def _read_env(name: str, default: str = "") -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _resolve_grafana_password() -> str:
    """Resolve Grafana password from supported runtime env only (no committed default)."""
    for name in (
        "GF_SECURITY_ADMIN_PASSWORD",
        "GRAFANA_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        value = _read_env(name)
        if value:
            return value
    return ""


def _resolve_grafana_username() -> str:
    for name in ("GRAFANA_USERNAME", "GF_SECURITY_ADMIN_USER"):
        value = _read_env(name)
        if value:
            return value
    return DEFAULT_GRAFANA_USERNAME


def _resolve_expected_runtime_source_identity() -> (
    RuntimeSourceIdentityResolutionResult
):
    """Resolve the expected identity with the canonical source precedence."""
    root = Path(__file__).resolve().parents[4]
    contract_path = root / "configs/quality/docker_runtime_contracts.yaml"
    payload = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return resolve_runtime_source_identity()
    identity_contract = payload.get("dashboard_data_plane", {}).get(
        "source_identity", {}
    )
    if not isinstance(identity_contract, dict):
        return resolve_runtime_source_identity()
    environment_name = str(
        identity_contract.get("environment_name") or RUNTIME_SOURCE_ID_ENV
    )
    repository_environment = load_repository_source_environment(
        root,
        names=(environment_name,),
        process_environment=os.environ,
    )
    environment = runtime_preflight.dashboard_source_environment(
        root,
        payload,
        process_environment=os.environ,
        repository_environment=repository_environment,
    )
    return resolve_runtime_source_identity(
        computed_identity=environment.get(environment_name),
        process_environment=os.environ,
        repository_environment=repository_environment,
        environment_name=environment_name,
        label_name=str(identity_contract.get("label_name") or ""),
    )


def _resolve_expected_runtime_source_id() -> str:
    """Backward-compatible digest-only wrapper for existing call sites."""
    return _resolve_expected_runtime_source_identity().value or ""


def _has_grafana_auth_material(*, username: str, password: str) -> bool:
    # Username is part of the call-site auth pair; presence is token or password.
    _ = username
    token = _read_env("GRAFANA_SERVICE_ACCOUNT_TOKEN")
    return bool(token) or bool(password)


def _fetch_json(url: str, timeout_seconds: float) -> object:
    from scripts.engineering.common.repo_paths import ensure_local_http_url

    safe_url = ensure_local_http_url(url)
    with request.urlopen(safe_url, timeout=timeout_seconds) as response:
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
    # HTTP/API probes can stay short; Chromium launch needs a floor timeout.
    playwright_timeout = max(
        float(timeout_seconds),
        DEFAULT_PLAYWRIGHT_PROBE_TIMEOUT_SECONDS,
    )
    ok, detail = rerender_screenshots.check_playwright_runtime(playwright_timeout)
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


def _quarantine_explorer_is_applicable() -> bool:
    """Return whether a shipped dashboard still requires the retired HTTP UI."""
    for dashboard_path in _DASHBOARD_DIR.glob(DASHBOARD_FILE_PATTERN):
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if payload.get("uid") == QUARANTINE_EXPLORER_UID:
            return True
    return False


def _expected_dashboard_screenshot_pairs(
    screenshot_dir: Path,
    *,
    selected_uids: tuple[str, ...] = (),
) -> list[tuple[Path, Path, str]]:
    pairs: list[tuple[Path, Path, str]] = []
    for dashboard_path in sorted(_DASHBOARD_DIR.glob(DASHBOARD_FILE_PATTERN)):
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
            return (
                {},
                f"could not read dashboard panel contract {dashboard_path}: {exc}",
            )
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


_ALLOWED_TERMINAL_STATES = frozenset(
    {
        "healthy",
        "explicit-error",
        "valid-empty",
        "telemetry-absent",
        "not-applicable",
        "incomplete",
    }
)
_SILVER_BACKEND_HEALTH_TERMINAL = frozenset(
    {"healthy", "explicit-error", "valid-empty"}
)


def _parse_requested_render_context(
    manifest: dict[str, object],
) -> tuple[int, object, str | None]:
    """Return (requested_width, requested_theme, error)."""
    requested = manifest.get("requested")
    if not isinstance(requested, dict):
        return 0, None, "render manifest is missing requested viewport/theme evidence"
    requested_viewport = requested.get("viewport")
    requested_theme = requested.get("theme")
    if not isinstance(requested_viewport, dict):
        return 0, None, "render manifest requested.viewport is missing"
    requested_width = requested_viewport.get("width")
    requested_height = requested_viewport.get("height")
    if (
        not isinstance(requested_width, int)
        or requested_width <= 0
        or not isinstance(requested_height, int)
        or requested_height <= 0
    ):
        return (
            0,
            None,
            "render manifest requested.viewport must contain positive width/height",
        )
    if requested_theme not in {"dark", "light"}:
        return 0, None, "render manifest requested.theme must be dark or light"
    if manifest.get("expand_collapsed_rows") is not True:
        return 0, None, "render manifest must prove expand_collapsed_rows=true"
    return requested_width, requested_theme, None


def _validate_global_terminal_state(manifest: dict[str, object]) -> str | None:
    terminal_validation = manifest.get("terminal_state_validation")
    if not isinstance(terminal_validation, dict):
        return "render manifest is missing terminal_state_validation"
    if terminal_validation.get("status") != "ok":
        return (
            "render manifest terminal_state_validation did not pass: "
            f"status={terminal_validation.get('status')!r}"
        )
    return None


def _index_manifest_dashboards(
    manifest: dict[str, object],
) -> tuple[dict[str, dict[str, object]], str | None]:
    dashboard_payload = manifest.get("dashboards")
    if not isinstance(dashboard_payload, list):
        return {}, "render manifest dashboards must be a list"
    dashboards: dict[str, dict[str, object]] = {}
    for item in dashboard_payload:
        if not isinstance(item, dict):
            continue
        uid = item.get("uid")
        if isinstance(uid, str):
            dashboards[uid] = item
    return dashboards, None


def _validate_dashboard_viewport_theme(
    uid: str,
    dashboard: dict[str, object],
    *,
    requested_width: int,
    requested_theme: object,
) -> str | None:
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
    return None


def _extract_panel_states(
    uid: str,
    dashboard: dict[str, object],
) -> tuple[dict[str, object] | None, list[object] | None, str | None]:
    dashboard_terminal = dashboard.get("terminalStateValidation")
    if not isinstance(dashboard_terminal, dict):
        return (
            None,
            None,
            f"render manifest dashboard {uid} lacks terminal panel evidence",
        )
    if dashboard_terminal.get("status") != "ok":
        return None, None, f"render manifest dashboard {uid} terminal validation failed"
    panel_states = dashboard_terminal.get("panelStates")
    if not isinstance(panel_states, list) or not panel_states:
        return (
            None,
            None,
            f"render manifest dashboard {uid} has no required panel states",
        )
    invalid_states = [
        state
        for state in panel_states
        if not isinstance(state, dict)
        or state.get("classification") not in _ALLOWED_TERMINAL_STATES
    ]
    if invalid_states:
        panel_ids = ", ".join(
            str(state.get("id")) if isinstance(state, dict) else "unknown"
            for state in invalid_states
        )
        return (
            None,
            None,
            (
                f"render manifest dashboard {uid} contains non-terminal or "
                f"contradictory required panel(s): {panel_ids}"
            ),
        )
    return dashboard_terminal, panel_states, None


def _validate_dashboard_typography(
    uid: str,
    dashboard: dict[str, object],
) -> str | None:
    typography = dashboard.get("typographyValidation")
    if not isinstance(typography, dict):
        return f"render manifest dashboard {uid} lacks typography evidence"
    if typography.get("status") != "ok":
        return f"render manifest dashboard {uid} typography validation failed"
    body_minimum = typography.get("bodyMinimumPx")
    title_minimum = typography.get("panelTitleMinimumPx")
    grafana_body_minimum = typography.get("grafanaBodyMinimumPx")
    grafana_title_minimum = typography.get("grafanaPanelTitleMinimumPx")
    if (
        not isinstance(body_minimum, (int, float))
        or body_minimum < _MIN_PANEL_BODY_FONT_PX
    ):
        return f"render manifest dashboard {uid} body typography floor drift"
    if (
        not isinstance(title_minimum, (int, float))
        or title_minimum + 0.01 < _MIN_PANEL_TITLE_FONT_PX
    ):
        return f"render manifest dashboard {uid} title typography floor drift"
    if (
        not isinstance(grafana_body_minimum, (int, float))
        or grafana_body_minimum < _MIN_GRAFANA_BODY_FONT_PX
    ):
        return f"render manifest dashboard {uid} Grafana body typography floor drift"
    if (
        not isinstance(grafana_title_minimum, (int, float))
        or grafana_title_minimum < _MIN_GRAFANA_PANEL_TITLE_FONT_PX
    ):
        return f"render manifest dashboard {uid} Grafana title typography floor drift"
    violations = typography.get("violations")
    if not isinstance(violations, list) or violations:
        return f"render manifest dashboard {uid} has typography violations"
    return None


def _validate_dashboard_panel_containment(
    uid: str,
    dashboard: dict[str, object],
) -> str | None:
    """Fail closed on first-window internal overflow when evidence is present."""
    containment = dashboard.get("panelContainment")
    if containment is None:
        return None
    if not isinstance(containment, dict):
        return f"render manifest dashboard {uid} has invalid panel containment evidence"
    if containment.get("status") != "ok":
        overflow = [
            f"panel {item.get('id')}"
            for item in containment.get("panels") or []
            if isinstance(item, dict) and item.get("status") != "ok"
        ]
        detail = ", ".join(overflow) if overflow else "status!=ok"
        return f"render manifest dashboard {uid} first-window panel overflow: {detail}"
    panels = containment.get("panels")
    if not isinstance(panels, list) or not panels:
        return f"render manifest dashboard {uid} lacks first-window containment panels"
    required = (
        "uid",
        "id",
        "title",
        "type",
        "gridPos",
        "clientHeight",
        "scrollHeight",
        "clientWidth",
        "scrollWidth",
        "verticalOverflow",
        "horizontalOverflow",
        "status",
    )
    for item in panels:
        error = _validate_containment_panel(uid, item, required=required)
        if error:
            return error
    return None


def _validate_containment_panel(
    uid: str, item: object, *, required: tuple[str, ...]
) -> str | None:
    if not isinstance(item, dict):
        return f"render manifest dashboard {uid} has a non-object containment panel"
    missing = [field for field in required if field not in item]
    if missing:
        return (
            f"render manifest dashboard {uid} containment panel "
            f"{item.get('id')} missing {missing}"
        )
    if item.get("verticalOverflow") or item.get("horizontalOverflow"):
        return (
            f"render manifest dashboard {uid} first-window overflow on "
            f"panel {item.get('id')}"
        )
    return None


def _validate_panel_id_coverage(
    uid: str,
    *,
    dashboard_terminal: dict[str, object],
    panel_states: list[object],
    expected_ids: tuple[int, ...],
) -> str | None:
    actual_ids = [state.get("id") for state in panel_states if isinstance(state, dict)]
    if any(not isinstance(panel_id, int) for panel_id in actual_ids):
        return f"render manifest dashboard {uid} has non-integer panel IDs"
    integer_ids = [panel_id for panel_id in actual_ids if isinstance(panel_id, int)]
    if len(integer_ids) != len(set(integer_ids)):
        return f"render manifest dashboard {uid} repeats panel evidence"
    if set(integer_ids) != set(expected_ids):
        missing_ids = sorted(set(expected_ids) - set(integer_ids))
        extra_ids = sorted(set(integer_ids) - set(expected_ids))
        return (
            f"render manifest dashboard {uid} panel coverage drift: "
            f"missing={missing_ids} extra={extra_ids}"
        )
    if dashboard_terminal.get("requiredPanelCount") != len(expected_ids):
        return f"render manifest dashboard {uid} requiredPanelCount drift"
    if dashboard_terminal.get("checkedPanelCount") != len(expected_ids):
        return f"render manifest dashboard {uid} checkedPanelCount drift"
    return None


def _validate_silver_backend_health_panel(panel_states: list[object]) -> str | None:
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
    if backend_health.get("classification") not in _SILVER_BACKEND_HEALTH_TERMINAL:
        return (
            "Silver Backend Health panel 13 is not terminal: "
            f"{backend_health.get('classification')!r}"
        )
    return None


def _validate_screenshot_evidence(
    uid: str,
    dashboard: dict[str, object],
    *,
    requested_width: int,
    screenshot_dir: Path,
) -> str | None:
    file_name = dashboard.get("file")
    evidence = dashboard.get("screenshotEvidence")
    if (
        not isinstance(file_name, str)
        or file_name != f"{uid}.png"
        or not isinstance(evidence, dict)
    ):
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


def _validate_fixture_state_provenance(fixture_state: object) -> str | None:
    if not isinstance(fixture_state, dict):
        return "render manifest fixture-state provenance must be a mapping"
    fixture_path = fixture_state.get("path")
    if not isinstance(fixture_path, str) or not fixture_path:
        return "render manifest fixture-state path is missing"
    relative_path = Path(fixture_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return "render manifest fixture-state path is outside repository root"
    try:
        expected = rerender_screenshots._fixture_state_evidence_from_path(
            _REPO_ROOT / relative_path
        )
    except ValueError as exc:
        return f"render manifest fixture-state registry is invalid: {exc}"
    if fixture_state.get("contract") != expected["contract"]:
        return "render manifest fixture-state contract is invalid"
    if fixture_state.get("sha256") != expected["sha256"]:
        return "render manifest fixture-state SHA does not match registry"
    if fixture_state.get("cases") != expected["cases"]:
        return "render manifest fixture-state cases do not match registry"
    if fixture_state.get("fixtures") != expected["fixtures"]:
        return "render manifest fixture-state fixture evidence does not match registry"
    return None


def _validate_manifest_file_sets(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    dashboards: dict[str, dict[str, object]],
    screenshot_dir: Path,
) -> str | None:
    expected_uid_set = set(expected_uids)
    actual_uid_set = set(dashboards)
    if actual_uid_set != expected_uid_set:
        return (
            "render manifest dashboard file-set drift: "
            f"expected={sorted(expected_uid_set)} actual={sorted(actual_uid_set)}"
        )

    expected_files = sorted(f"{uid}.png" for uid in expected_uids)
    manifest_files = manifest.get("file_set")
    if manifest_files != expected_files:
        return (
            "render manifest file_set drift: "
            f"expected={expected_files} actual={manifest_files!r}"
        )
    if manifest.get("file_count") != len(expected_files):
        return "render manifest file_count drift"
    actual_files = sorted(path.name for path in screenshot_dir.glob("*.png"))
    if actual_files != expected_files:
        return (
            "render directory PNG file-set drift: "
            f"expected={expected_files} actual={actual_files}"
        )
    return None


def _all_shipped_uids() -> set[str]:
    all_shipped_uids: set[str] = set()
    for dashboard_path in sorted(_DASHBOARD_DIR.glob(DASHBOARD_FILE_PATTERN)):
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uid = payload.get("uid")
        if isinstance(uid, str) and uid:
            all_shipped_uids.add(uid)
    return all_shipped_uids


def _validate_manifest_identity(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    screenshot_dir: Path,
) -> str | None:
    expected_uid_set = set(expected_uids)
    all_shipped_uids = _all_shipped_uids()
    expected_kind = (
        "full-set"
        if all_shipped_uids and expected_uid_set == all_shipped_uids
        else "selected-subset"
    )
    if manifest.get("manifest_kind") != expected_kind:
        return (
            "render manifest kind drift: "
            f"expected={expected_kind!r} actual={manifest.get('manifest_kind')!r}"
        )

    capture_id = manifest.get("capture_id")
    immutable_name = manifest.get("immutable_manifest")
    if not isinstance(capture_id, str) or not capture_id:
        return "render manifest lacks capture_id"
    expected_immutable = f"render-manifest--{expected_kind}--{capture_id}.json"
    if immutable_name != expected_immutable:
        return "render manifest immutable filename drift"
    immutable_path = screenshot_dir / expected_immutable
    canonical_path = screenshot_dir / "render-manifest.json"
    try:
        if immutable_path.read_bytes() != canonical_path.read_bytes():
            return "render manifest immutable copy drift"
    except OSError as exc:
        return f"render manifest immutable copy is unreadable: {exc}"
    return None


def _validate_dashboard_sources(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    dashboards: dict[str, dict[str, object]],
) -> str | None:
    source = manifest.get("source")
    if not isinstance(source, dict):
        return "render manifest lacks source provenance"
    commit_sha = source.get("commit_sha")
    if not isinstance(commit_sha, str) or not _COMMIT_SHA_PATTERN.fullmatch(commit_sha):
        return "render manifest commit SHA is missing or invalid"
    source_dashboards = source.get("dashboards")
    if not isinstance(source_dashboards, dict):
        return "render manifest lacks dashboard source provenance"
    for uid in expected_uids:
        dashboard_source = dashboards[uid].get("dashboardSource")
        top_source = source_dashboards.get(uid)
        if not isinstance(dashboard_source, dict) or dashboard_source != top_source:
            return f"render manifest dashboard {uid} source provenance drift"
        source_path = dashboard_source.get("path")
        source_sha = dashboard_source.get("sha256")
        version = dashboard_source.get("version")
        if not isinstance(source_path, str) or not source_path.endswith(".json"):
            return f"render manifest dashboard {uid} lacks JSON source path"
        if not isinstance(source_sha, str) or not _RUNTIME_SOURCE_ID_PATTERN.fullmatch(
            source_sha
        ):
            return f"render manifest dashboard {uid} source SHA is invalid"
        if not isinstance(version, int):
            return f"render manifest dashboard {uid} version is missing"
    return None


def _validate_capture_context(manifest: dict[str, object]) -> str | None:
    capture_context = manifest.get("capture_context")
    if not isinstance(capture_context, dict):
        return "render manifest lacks capture context"
    time_range = capture_context.get("time_range")
    variables = capture_context.get("variables")
    row_state = capture_context.get("row_state")
    if not isinstance(time_range, dict) or not {
        "from",
        "to",
        "timezone",
    }.issubset(time_range):
        return "render manifest lacks time-range provenance"
    if not isinstance(variables, dict) or not {
        "workflow",
        "pipeline",
        "run_type",
        "run_id",
    }.issubset(variables):
        return "render manifest lacks variable provenance"
    if not isinstance(row_state, dict) or not isinstance(
        row_state.get("expand_collapsed_rows"), bool
    ):
        return "render manifest lacks row-state provenance"
    fixture_state = capture_context.get("fixture_state")
    if fixture_state is not None:
        fixture_error = _validate_fixture_state_provenance(fixture_state)
        if fixture_error is not None:
            return fixture_error
    return None


def _validate_browser_context(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    dashboards: dict[str, dict[str, object]],
) -> str | None:
    requested = manifest.get("requested")
    if not isinstance(requested, dict):
        return "render manifest lacks requested browser context"
    requested_zoom = requested.get("browser_zoom")
    requested_kiosk = requested.get("kiosk_mode")
    if not isinstance(requested_zoom, int) or not isinstance(requested_kiosk, str):
        return "render manifest lacks requested zoom/kiosk provenance"
    for uid in expected_uids:
        browser_state = dashboards[uid].get("browserState")
        if not isinstance(browser_state, dict):
            return f"render manifest dashboard {uid} lacks actual browser state"
        if browser_state.get("requestedZoom") != requested_zoom:
            return f"render manifest dashboard {uid} browser zoom drift"
        if browser_state.get("actualKiosk") != requested_kiosk:
            return f"render manifest dashboard {uid} kiosk state drift"
        if browser_state.get("cssZoom") in {None, ""}:
            return f"render manifest dashboard {uid} lacks actual CSS zoom"
        if requested_zoom > 100 and browser_state.get("zoomEmulation") != (
            "layout-viewport-and-device-scale-factor"
        ):
            return f"render manifest dashboard {uid} lacks reflow zoom evidence"
        if requested_zoom > 100 and not isinstance(
            browser_state.get("layoutViewport"), dict
        ):
            return f"render manifest dashboard {uid} lacks zoom layout viewport"
    return None


def _validate_manifest_provenance(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    dashboards: dict[str, dict[str, object]],
    screenshot_dir: Path,
) -> str | None:
    """Validate render manifest provenance against dashboard sources."""
    error = _validate_manifest_file_sets(
        manifest,
        expected_uids=expected_uids,
        dashboards=dashboards,
        screenshot_dir=screenshot_dir,
    )
    if error:
        return error
    error = _validate_manifest_identity(
        manifest,
        expected_uids=expected_uids,
        screenshot_dir=screenshot_dir,
    )
    if error:
        return error
    error = _validate_dashboard_sources(
        manifest,
        expected_uids=expected_uids,
        dashboards=dashboards,
    )
    if error:
        return error
    error = _validate_capture_context(manifest)
    if error:
        return error
    return _validate_browser_context(
        manifest,
        expected_uids=expected_uids,
        dashboards=dashboards,
    )


def _validate_one_dashboard_render(
    uid: str,
    dashboard: dict[str, object],
    *,
    requested_width: int,
    requested_theme: object,
    expected_panel_ids: dict[str, tuple[int, ...]] | None,
    screenshot_dir: Path | None,
) -> str | None:
    viewport_error = _validate_dashboard_viewport_theme(
        uid,
        dashboard,
        requested_width=requested_width,
        requested_theme=requested_theme,
    )
    if viewport_error:
        return viewport_error

    typography_error = _validate_dashboard_typography(uid, dashboard)
    if typography_error:
        return typography_error

    containment_error = _validate_dashboard_panel_containment(uid, dashboard)
    if containment_error:
        return containment_error

    panel_error = _validate_dashboard_panel_states(
        uid, dashboard, expected_panel_ids=expected_panel_ids
    )
    if panel_error:
        return panel_error

    if screenshot_dir is not None:
        return _validate_screenshot_evidence(
            uid,
            dashboard,
            requested_width=requested_width,
            screenshot_dir=screenshot_dir,
        )
    return None


def _validate_dashboard_panel_states(
    uid: str,
    dashboard: dict[str, object],
    *,
    expected_panel_ids: dict[str, tuple[int, ...]] | None,
) -> str | None:
    dashboard_terminal, panel_states, panel_error = _extract_panel_states(
        uid, dashboard
    )
    if panel_error:
        return panel_error
    assert dashboard_terminal is not None and panel_states is not None
    if expected_panel_ids is not None:
        expected_ids = expected_panel_ids.get(uid)
        if expected_ids is None:
            return f"dashboard panel contract is missing for {uid}"
        coverage_error = _validate_panel_id_coverage(
            uid,
            dashboard_terminal=dashboard_terminal,
            panel_states=panel_states,
            expected_ids=expected_ids,
        )
        if coverage_error:
            return coverage_error
    if uid == "bioetl-silver-reject-explorer":
        return _validate_silver_backend_health_panel(panel_states)
    return None


def _validate_manifest_render_contract(
    manifest: dict[str, object],
    *,
    expected_uids: tuple[str, ...],
    expected_panel_ids: dict[str, tuple[int, ...]] | None = None,
    screenshot_dir: Path | None = None,
) -> str | None:
    requested_width, requested_theme, request_error = _parse_requested_render_context(
        manifest
    )
    if request_error:
        return request_error

    terminal_error = _validate_global_terminal_state(manifest)
    if terminal_error:
        return terminal_error

    dashboards, index_error = _index_manifest_dashboards(manifest)
    if index_error:
        return index_error

    if screenshot_dir is not None:
        provenance_error = _validate_manifest_provenance(
            manifest,
            expected_uids=expected_uids,
            dashboards=dashboards,
            screenshot_dir=screenshot_dir,
        )
        if provenance_error:
            return provenance_error

    for uid in expected_uids:
        dashboard = dashboards.get(uid)
        if not isinstance(dashboard, dict):
            return f"render manifest is missing dashboard evidence for {uid}"
        dashboard_error = _validate_one_dashboard_render(
            uid,
            dashboard,
            requested_width=requested_width,
            requested_theme=requested_theme,
            expected_panel_ids=expected_panel_ids,
            screenshot_dir=screenshot_dir,
        )
        if dashboard_error:
            return dashboard_error
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


def classify_ops_http_bootstrap(payload: object) -> PreflightCheck:
    """Classify Grafana bootstrap status without talking to Docker."""
    if not isinstance(payload, dict):
        return PreflightCheck(
            name="ops-http-bootstrap",
            status="error",
            detail="Grafana bioetl-bootstrap-status.json is missing or not an object",
        )
    ops_http = str(payload.get("ops_http") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if ops_http in {"deferred", "failed"}:
        return PreflightCheck(
            name="ops-http-bootstrap",
            status="error",
            detail=(
                f"Grafana Ops HTTP bootstrap is {ops_http} "
                f"({reason or 'unspecified'}); panel 3010 cannot be a truthful "
                "healthy/valid-empty render"
            ),
        )
    if ops_http != "ready":
        return PreflightCheck(
            name="ops-http-bootstrap",
            status="error",
            detail=f"Grafana Ops HTTP bootstrap is {ops_http or 'missing'}",
        )
    return PreflightCheck(
        name="ops-http-bootstrap",
        status="ok",
        detail=f"ops_http=ready ({reason or 'identity_matched'})",
    )


def classify_ops_http_datasource_uid(
    *,
    http_status: int,
    payload: object,
) -> PreflightCheck:
    """Classify GET /api/datasources/uid/bioetl-ops-http without live Grafana."""
    if http_status == 404 or http_status >= 400:
        return PreflightCheck(
            name="ops-http-datasource",
            status="error",
            detail=(
                f"GET /api/datasources/uid/{OPS_HTTP_DATASOURCE_UID} returned "
                f"HTTP {http_status}; panel 3010 cannot be healthy/valid-empty"
            ),
        )
    if not isinstance(payload, dict):
        return PreflightCheck(
            name="ops-http-datasource",
            status="error",
            detail="datasource payload is missing or not an object",
        )
    uid = str(payload.get("uid") or "").strip()
    ds_type = str(payload.get("type") or "").strip()
    if uid != OPS_HTTP_DATASOURCE_UID:
        return PreflightCheck(
            name="ops-http-datasource",
            status="error",
            detail=f"datasource uid {uid or 'missing'} is not {OPS_HTTP_DATASOURCE_UID}",
        )
    return PreflightCheck(
        name="ops-http-datasource",
        status="ok",
        detail=f"uid={uid} type={ds_type or 'unknown'}",
    )


def classify_panel_3010_terminal_contract() -> PreflightCheck:
    """Document 3010 Playwright terminal states (no live I/O)."""
    return PreflightCheck(
        name="panel-3010-terminal-states",
        status="ok",
        detail=(
            "3010 positive render must classify healthy; successful empty must "
            "classify valid-empty (noValue starts with VALID EMPTY); a visible "
            "TREE_MISSING / LAYOUT_UNHEALTHY / IDENTITY_UNHEALTHY row is a "
            "healthy fail-closed bind/origin state (HTTP 200), not "
            "explicit-error. Missing datasource or bootstrap deferred/failed "
            "must classify explicit-error. explicit-error is not success for "
            "positive 3010 renders. Use --fallback playwright (Grafana Render "
            "API leaves terminal state not-checked)."
        ),
    )


def _read_grafana_bootstrap_status_live() -> object:
    """Opt-in live read; unit tests must call classify_ops_http_bootstrap."""
    import subprocess

    completed = subprocess.run(
        [
            "docker",
            "exec",
            "bioetl-grafana",
            "cat",
            GRAFANA_BOOTSTRAP_STATUS_PATH,
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=10.0,
    )
    if completed.returncode != 0:
        return None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None


def _check_ops_http_datasource_live(
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
    url = f"{config.base_url}/api/datasources/uid/{OPS_HTTP_DATASOURCE_UID}"
    try:
        payload = rerender_screenshots._request_json(
            url,
            headers=rerender_screenshots._auth_headers(config),
            timeout_seconds=timeout_seconds,
        )
        return classify_ops_http_datasource_uid(http_status=200, payload=payload)
    except error.HTTPError as exc:
        return classify_ops_http_datasource_uid(http_status=exc.code, payload=None)
    except Exception as exc:  # pragma: no cover - exercised by callers
        return PreflightCheck(
            name="ops-http-datasource",
            status="error",
            detail=f"{url} failed: {exc}",
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
    include_render_checks: bool = True,
    include_semantic_checks: bool = True,
    screenshot_uids: tuple[str, ...] = (),
) -> list[PreflightCheck]:
    """Run all preflight checks for Grafana dashboard audit readiness.

    NOSONAR - S3776: complexity 21 exceeds 15; extraction would obscure preflight check orchestration logic
    """
    checks = [
        _check_http_json(
            name="grafana",
            url=f"{grafana_base_url.rstrip('/')}/api/health",
            timeout_seconds=timeout_seconds,
        )
    ]

    if include_render_checks:
        checks.append(
            _check_grafana_render_auth(
                grafana_base_url=grafana_base_url,
                grafana_username=grafana_username,
                grafana_password=grafana_password,
                timeout_seconds=timeout_seconds,
            )
        )
        # Live Ops HTTP bootstrap/UID probes are opt-in with render checks
        # (monitoring already requested). Default CI uses skip-render-checks.
        checks.append(
            classify_ops_http_bootstrap(_read_grafana_bootstrap_status_live())
        )
        checks.append(
            _check_ops_http_datasource_live(
                grafana_base_url=grafana_base_url,
                grafana_username=grafana_username,
                grafana_password=grafana_password,
                timeout_seconds=timeout_seconds,
            )
        )
    if include_semantic_checks:
        checks.append(classify_panel_3010_terminal_contract())
        checks.append(
            _check_http_json(
                name="prometheus",
                url=f"{prometheus_base_url.rstrip('/')}/api/v1/status/runtimeinfo",
                timeout_seconds=timeout_seconds,
            )
        )
    if include_render_checks:
        playwright_check = _check_playwright_runtime(timeout_seconds)
        checks.extend([playwright_check, _check_expanded_row_capture(playwright_check)])

    if include_semantic_checks:
        if not _quarantine_explorer_is_applicable():
            checks.append(
                PreflightCheck(
                    name="quarantine-explorer",
                    status="not_applicable",
                    detail=(
                        "Quarantine Explorer HTTP/UI surface is retired from the "
                        "shipped dashboard portfolio; domain quarantine write/storage "
                        "remains unchanged."
                    ),
                )
            )
        else:
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
                            "canonical health probe reachable via "
                            f"{resolved_app_base_url}"
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
        default=_resolve_grafana_username(),
        help=(
            "Grafana username. Defaults to GRAFANA_USERNAME / "
            "GF_SECURITY_ADMIN_USER / admin. No password is ever hard-coded."
        ),
    )
    parser.add_argument(
        "--grafana-password",
        default=_resolve_grafana_password(),
        help=(
            "Grafana password. Defaults to GF_SECURITY_ADMIN_PASSWORD / "
            "GRAFANA_PASSWORD / GRAFANA_ADMIN_PASSWORD. Prefer "
            "GRAFANA_SERVICE_ACCOUNT_TOKEN when available."
        ),
    )
    parser.add_argument(
        "--prometheus-base-url",
        default=DEFAULT_PROMETHEUS_BASE_URL,
        help="Prometheus base URL. Default: http://localhost:9090",
    )
    parser.add_argument(
        "--ops-http-base-url",
        default=DEFAULT_OPS_HTTP_BASE_URL,
        help="BioETL Ops HTTP base URL. Default: http://localhost:8000",
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
        "--skip-render-checks",
        action="store_true",
        help=(
            "Run only datasource/backend semantic readiness checks; skip Grafana "
            "render auth, Playwright, and expanded-row capture checks."
        ),
    )
    parser.add_argument(
        "--skip-semantic-checks",
        action="store_true",
        help=(
            "Run only Grafana/render readiness and screenshot contract checks; "
            "skip Prometheus and Quarantine Explorer semantic readiness checks."
        ),
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


def _exit_code_for_checks(checks: list[PreflightCheck]) -> int:
    """Map failed checks to distinct non-zero outcomes for operator triage."""
    if all(check.status in {"ok", "not_applicable"} for check in checks):
        return EXIT_OK
    by_name = {check.name: check for check in checks}
    outcomes = (
        ("credentials", EXIT_CREDENTIALS),
        ("grafana", EXIT_GRAFANA_HEALTH),
        ("grafana-render-auth", EXIT_RENDER_AUTH),
        ("playwright-runtime", EXIT_PLAYWRIGHT),
        ("expanded-row-capture", EXIT_EXPANDED_ROW),
        ("prometheus", EXIT_PROMETHEUS),
        ("bioetl-control-plane-source", EXIT_BIOETL_SOURCE),
        ("bioetl-prometheus-target", EXIT_BIOETL_TARGET),
        ("ops-http-bootstrap", EXIT_OPS_HTTP_BOOTSTRAP),
        ("ops-http-datasource", EXIT_OPS_HTTP_BOOTSTRAP),
        ("quarantine-explorer", EXIT_QUARANTINE),
        ("screenshots", EXIT_SCREENSHOTS),
    )
    for name, exit_code in outcomes:
        if by_name.get(name, PreflightCheck("", "ok", "")).status != "ok":
            return exit_code
    return EXIT_GENERIC


def _check_bioetl_prometheus_target(
    *,
    prometheus_base_url: str,
    timeout_seconds: float,
) -> PreflightCheck:
    """Fail closed when the configured BioETL scrape target is not UP."""
    url = f"{prometheus_base_url.rstrip('/')}/api/v1/targets"
    try:
        payload = _fetch_json(url, timeout_seconds)
    except error.HTTPError as exc:
        return PreflightCheck(
            name="bioetl-prometheus-target",
            status="error",
            detail=f"{url} returned HTTP {exc.code}",
        )
    except Exception as exc:  # pragma: no cover - exercised by callers
        return PreflightCheck(
            name="bioetl-prometheus-target",
            status="error",
            detail=f"{url} failed: {exc}",
        )
    if not isinstance(payload, dict):
        return PreflightCheck(
            name="bioetl-prometheus-target",
            status="error",
            detail=f"{url} did not return a JSON object",
        )
    data = payload.get("data")
    active = []
    if isinstance(data, dict):
        raw_active = data.get("activeTargets")
        if isinstance(raw_active, list):
            active = raw_active
    bioetl_targets = [
        target
        for target in active
        if isinstance(target, dict)
        and (
            str(target.get("labels", {}).get("job", "")) == "bioetl"
            or "bioetl:8000" in str(target.get("scrapeUrl", ""))
            or "bioetl:8000" in str(target.get("labels", {}).get("instance", ""))
        )
    ]
    if not bioetl_targets:
        return PreflightCheck(
            name="bioetl-prometheus-target",
            status="error",
            detail=(
                "Prometheus has no active bioetl scrape target; "
                "canonical config expects job=bioetl scraping bioetl:8000"
            ),
        )
    unhealthy = [
        target
        for target in bioetl_targets
        if str(target.get("health", "")).lower() != "up"
    ]
    if unhealthy:
        details = ", ".join(
            f"{target.get('scrapeUrl', '<unknown>')} health={target.get('health')!r} "
            f"lastError={target.get('lastError')!r}"
            for target in unhealthy
        )
        return PreflightCheck(
            name="bioetl-prometheus-target",
            status="error",
            detail=f"BioETL Prometheus target is not UP: {details}",
        )
    return PreflightCheck(
        name="bioetl-prometheus-target",
        status="ok",
        detail="active bioetl scrape target health=up",
    )


def _check_bioetl_control_plane_source(
    *,
    ops_http_base_url: str,
    expected_runtime_source_id: str,
    timeout_seconds: float,
    expected_resolution_state: str = IDENTITY_STATE_ALIGNED,
) -> PreflightCheck:
    """Fail closed when Ops HTTP serves a different runtime/data origin."""
    if expected_resolution_state != IDENTITY_STATE_ALIGNED:
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail=(
                "Expected runtime source identity resolution is not aligned: "
                f"{expected_resolution_state}"
            ),
        )
    url = f"{ops_http_base_url.rstrip('/')}/ops/control-plane/ready"
    if not _RUNTIME_SOURCE_ID_PATTERN.fullmatch(expected_runtime_source_id):
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail="expected runtime source identity is missing or unmanaged",
        )
    try:
        payload = _fetch_json(url, timeout_seconds)
    except error.HTTPError as exc:
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail=f"{url} returned HTTP {exc.code}",
        )
    except Exception as exc:  # pragma: no cover - exercised by callers
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail=f"{url} failed: {exc}",
        )
    if not isinstance(payload, dict):
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail=f"{url} did not return a JSON object",
        )
    actual_identity = payload.get("runtime_source_id")
    comparison = compare_runtime_source_identity(
        expected=expected_runtime_source_id,
        actual=actual_identity,
    )
    if comparison.state != IDENTITY_STATE_ALIGNED:
        reason = {
            IDENTITY_STATE_MISSING: "is missing",
            IDENTITY_STATE_INVALID: "is invalid",
            IDENTITY_STATE_FOREIGN: "belongs to another checkout",
        }.get(comparison.state, "does not match")
        return PreflightCheck(
            name="bioetl-control-plane-source",
            status="error",
            detail=(
                f"Ops HTTP runtime source identity {reason}; the backend may "
                "be serving another checkout or stale artifact mounts"
            ),
        )
    return PreflightCheck(
        name="bioetl-control-plane-source",
        status="ok",
        detail="Ops HTTP runtime source identity matches the selected runtime root",
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    username = str(args.grafana_username)
    password = str(args.grafana_password)
    include_render_checks = not args.skip_render_checks

    if include_render_checks and not _has_grafana_auth_material(
        username=username, password=password
    ):
        missing = PreflightCheck(
            name="credentials",
            status="error",
            detail=(
                "Grafana render auth requires GF_SECURITY_ADMIN_PASSWORD / "
                "GRAFANA_PASSWORD / GRAFANA_ADMIN_PASSWORD or "
                "GRAFANA_SERVICE_ACCOUNT_TOKEN; no committed default password is "
                "used. Prefer GRAFANA_PASSWORD for the password that already "
                "exists on the Grafana volume (GF_SECURITY_ADMIN_PASSWORD is "
                "first-boot only and may not match a long-lived volume)."
            ),
        )
        if args.json:
            print(json.dumps({"checks": [asdict(missing)]}, indent=2))
        else:
            print(_format_text([missing]))
        return EXIT_CREDENTIALS

    checks = run_checks(
        grafana_base_url=args.grafana_base_url,
        prometheus_base_url=args.prometheus_base_url,
        app_base_url=args.app_base_url,
        grafana_username=username,
        grafana_password=password,
        timeout_seconds=args.timeout_seconds,
        screenshot_dir=args.screenshot_dir,
        include_screenshot_check=not args.skip_screenshot_check,
        include_render_checks=include_render_checks,
        include_semantic_checks=not args.skip_semantic_checks,
        screenshot_uids=tuple(str(uid) for uid in args.screenshot_uids),
    )
    if not args.skip_semantic_checks:
        expected_source_resolution = _resolve_expected_runtime_source_identity()
        checks.append(
            _check_bioetl_control_plane_source(
                ops_http_base_url=args.ops_http_base_url,
                expected_runtime_source_id=expected_source_resolution.value or "",
                timeout_seconds=args.timeout_seconds,
                expected_resolution_state=expected_source_resolution.state,
            )
        )
        checks.append(
            _check_bioetl_prometheus_target(
                prometheus_base_url=args.prometheus_base_url,
                timeout_seconds=args.timeout_seconds,
            )
        )

    if args.json:
        print(json.dumps({"checks": [asdict(check) for check in checks]}, indent=2))
    else:
        print(_format_text(checks))

    return _exit_code_for_checks(checks)


if __name__ == "__main__":
    raise SystemExit(main())
