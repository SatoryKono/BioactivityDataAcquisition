"""Rerender Grafana dashboard screenshots through the Grafana render API."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from urllib import parse
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bioetl.infrastructure.storage.support.atomic_ops import (
    atomic_write_bytes,
    atomic_write_text,
)

_LOCAL_HTTP = "http"
DEFAULT_BASE_URL = f"{_LOCAL_HTTP}://localhost:3000"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = ""
DEFAULT_OUTPUT_DIR = Path("reports/observability/grafana/screenshots")
DEFAULT_WIDTH = 1600
DEFAULT_HEIGHT = 2200
DEFAULT_THEME = "dark"
DEFAULT_TIMEOUT_SECONDS = 120.0
_RENDER_MANIFEST_JSON = "render-manifest.json"
_CAPTURE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")
_DASHBOARD_VARIABLE_NAME_RE = re.compile(r"[A-Za-z]\w{0,63}\Z", re.ASCII)


def _default_tool_playwright_paths() -> tuple[Path, Path]:
    """Resolve Playwright tool paths under a private temp dir (S5443)."""
    import tempfile

    base = Path(tempfile.gettempdir()) / "bioetl-tools"
    return (
        base / "playwright-runtime" / "node_modules",
        base / "playwright-browsers",
    )


DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES, DEFAULT_TOOL_PLAYWRIGHT_BROWSERS = (
    _default_tool_playwright_paths()
)
LOCAL_PLAYWRIGHT_LIB_DIR = Path(
    ".cache/grafana-screenshot-runtime/root/usr/lib/x86_64-linux-gnu"
)
EXIT_CREDENTIALS = 9


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
    occurrence_id: str = ""
    capture_surface: str = "full"
    kiosk_mode: str = "off"
    browser_zoom: int = 100
    variables: tuple[tuple[str, str], ...] = ()
    navigation_only: bool = False
    fixture_manifest: Path | None = None
    fixture_state: dict[str, object] | None = None
    fixture_case: str = ""


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _repo_relative_path(path: Path, *, root: Path) -> tuple[Path, str]:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        relative = resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(
            f"fixture path must stay under repository root: {path}"
        ) from exc
    return resolved_path, relative.as_posix()


def _git_capture_source() -> dict[str, object]:
    """Return bounded repository provenance without exposing local paths."""
    repo_root = _repo_root()
    if not (repo_root / ".git").exists():
        return {"commit_sha": "UNKNOWN", "working_tree_dirty": None}
    try:
        commit_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            text=True,
            timeout=10,
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return {"commit_sha": "UNKNOWN", "working_tree_dirty": None}
    try:
        dirty = bool(
            subprocess.check_output(
                ["git", "status", "--porcelain", "--untracked-files=no"],
                cwd=repo_root,
                text=True,
                timeout=15,
            ).strip()
        )
    except (OSError, subprocess.SubprocessError):
        dirty = None
    return {"commit_sha": commit_sha, "working_tree_dirty": dirty}


def _dashboard_source_by_uid() -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    repo_root = _repo_root()
    for dashboard_path in sorted(_dashboard_dir().glob("*.json")):
        try:
            payload = json.loads(dashboard_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        uid = payload.get("uid")
        if not isinstance(uid, str) or not uid:
            continue
        try:
            source_path = str(dashboard_path.relative_to(repo_root))
        except ValueError:
            source_path = dashboard_path.name
        result[uid] = {
            "path": source_path,
            "sha256": _sha256_file(dashboard_path),
            "version": payload.get("version"),
        }
    return result


def _capture_id(config: RenderConfig) -> str:
    raw = config.occurrence_id.strip()
    if not raw:
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%S%fZ")
        raw = f"{timestamp}-{uuid.uuid4().hex[:12]}"
    cleaned = _CAPTURE_ID_RE.sub("-", raw).strip("-._")
    return cleaned or uuid.uuid4().hex


def _load_json_object(path: Path, *, description: str) -> tuple[bytes, dict[str, object]]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{description} is unreadable: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must contain a JSON object")
    return raw, payload


def _fixture_case_evidence(
    case: str,
    metadata: dict[str, object],
    *,
    contract: object,
    root: Path,
) -> dict[str, str]:
    fixture_path_value = metadata.get("path")
    if not isinstance(fixture_path_value, str) or not fixture_path_value:
        raise ValueError(f"fixture case {case!r} lacks a repository-relative path")
    fixture_path, fixture_relative_path = _repo_relative_path(
        root / fixture_path_value, root=root
    )
    fixture_bytes, fixture_payload = _load_json_object(
        fixture_path, description=f"fixture case {case!r}"
    )
    if (
        fixture_payload.get("contract") != contract
        or fixture_payload.get("case") != case
    ):
        raise ValueError(f"fixture case {case!r} contract or case value is invalid")
    if fixture_payload.get("classification") != metadata.get("classification"):
        raise ValueError(f"fixture case {case!r} classification does not match registry")
    if fixture_payload.get("http_status") != metadata.get("http_status"):
        raise ValueError(f"fixture case {case!r} HTTP status does not match registry")
    return {
        "path": fixture_relative_path,
        "sha256": _sha256_bytes(fixture_bytes),
    }


def _fixture_state_evidence_from_path(fixture_manifest: Path) -> dict[str, object]:
    """Build immutable fixture provenance from one validated registry snapshot."""
    root = _repo_root()
    registry_path, registry_relative_path = _repo_relative_path(
        fixture_manifest, root=root
    )
    registry_bytes, payload = _load_json_object(
        registry_path, description="fixture manifest"
    )
    contract = payload.get("contract")
    cases = payload.get("cases")
    if contract != "dashboard_state_fixture_v1" or not isinstance(cases, dict):
        raise ValueError(
            "fixture manifest must use dashboard_state_fixture_v1 with a cases mapping"
        )
    fixtures: dict[str, dict[str, str]] = {}
    for case, metadata in sorted(cases.items()):
        if not isinstance(case, str) or not isinstance(metadata, dict):
            raise ValueError("fixture manifest cases must map strings to metadata")
        fixtures[case] = _fixture_case_evidence(
            case, metadata, contract=contract, root=root
        )
    return {
        "contract": contract,
        "path": registry_relative_path,
        "sha256": _sha256_bytes(registry_bytes),
        "cases": sorted(fixtures),
        "fixtures": fixtures,
    }


def _fixture_state_evidence(config: RenderConfig) -> dict[str, object] | None:
    """Вернуть проверяемую provenance привязку optional fixture registry."""
    if config.fixture_manifest is None:
        return None
    return config.fixture_state or _fixture_state_evidence_from_path(
        config.fixture_manifest
    )


def _write_exclusive_text(path: Path, text: str) -> None:
    """Create immutable evidence once; a repeated occurrence must fail closed."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _finalize_manifest(config: RenderConfig, manifest: dict[str, Any]) -> None:
    """Bind one render occurrence to source, files, variables, and row state."""
    dashboards = [
        dict(item) for item in manifest.get("dashboards", []) if isinstance(item, dict)
    ]
    sources = _dashboard_source_by_uid()
    file_set: list[str] = []
    for dashboard in dashboards:
        uid = str(dashboard.get("uid", ""))
        file_name = dashboard.get("file") or dashboard.get("screenshot")
        if isinstance(file_name, str) and file_name:
            dashboard["file"] = file_name
            file_set.append(file_name)
        dashboard["dashboardSource"] = sources.get(
            uid,
            {"path": "UNKNOWN", "sha256": "UNKNOWN", "version": None},
        )
    dashboards.sort(key=lambda item: str(item.get("uid", "")))
    file_set = sorted(set(file_set))
    all_uids = set(sources)
    rendered_uids = {str(item.get("uid", "")) for item in dashboards if item.get("uid")}
    manifest_kind = (
        "full-set" if all_uids and rendered_uids == all_uids else "selected-subset"
    )
    capture_id = _capture_id(config)
    immutable_name = f"render-manifest--{manifest_kind}--{capture_id}.json"
    manifest.update(
        {
            "capture_id": capture_id,
            "occurrence_id": config.occurrence_id,
            "manifest_kind": manifest_kind,
            "immutable_manifest": immutable_name,
            "file_count": len(file_set),
            "file_set": file_set,
            "source": {
                **_git_capture_source(),
                "dashboards": {
                    uid: sources.get(uid, {}) for uid in sorted(rendered_uids)
                },
            },
            "capture_context": {
                "time_range": {
                    "from": f"now-{config.range_hours}h",
                    "to": "now",
                    "timezone": "UTC",
                },
                "variables": {
                    "workflow": config.workflow,
                    "pipeline": config.pipeline,
                    "run_type": config.run_type,
                    "run_id": config.run_id,
                },
                "row_state": {
                    "expand_collapsed_rows": config.expand_collapsed_rows,
                },
                "fixture_state": _fixture_state_evidence(config),
            },
            "dashboards": dashboards,
        }
    )
    text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    _write_exclusive_text(config.output_dir / immutable_name, text)
    atomic_write_text(config.output_dir / _RENDER_MANIFEST_JSON, text)


def _read_env(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _resolve_grafana_password() -> str:
    """Resolve supported runtime credentials without a committed password."""
    for name in (
        "GF_SECURITY_ADMIN_PASSWORD",
        "GRAFANA_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        value = _read_env(name, "")
        if value:
            return value
    return DEFAULT_PASSWORD


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
        "credentials, set GRAFANA_PASSWORD (or GRAFANA_SERVICE_ACCOUNT_TOKEN) to "
        "the password that was active when the Grafana volume was first "
        "initialized — GF_SECURITY_ADMIN_PASSWORD is applied only on first boot "
        "and may not match a long-lived container volume. Reload env via "
        "scripts/ops/support/load_repo_env.sh or pass --username/--password "
        "explicitly. Never commit or log the password."
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


def _build_render_parser() -> argparse.ArgumentParser:
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
        default=_resolve_grafana_password(),
        help=(
            "Grafana password. Defaults to GF_SECURITY_ADMIN_PASSWORD / "
            "GRAFANA_PASSWORD / GRAFANA_ADMIN_PASSWORD. No password is hard-coded."
        ),
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
    parser.add_argument(
        "--fixture-manifest",
        type=Path,
        default=None,
        help=(
            "Optional dashboard_state_fixture_v1 INDEX.json bound into render "
            "evidence provenance without changing the default live render path."
        ),
    )
    parser.add_argument(
        "--fixture-case",
        default="",
        help=(
            "Select one dashboard_state_fixture_v2 case_id. Requires "
            "--fixture-manifest pointing at a v2 INDEX.json. Binds the case "
            "response digest into evidence and fail-closes on digest mismatch. "
            "Does not change the default live render path when omitted."
        ),
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
    parser.add_argument(
        "--var",
        dest="variables",
        action="append",
        default=[],
        type=_parse_dashboard_variable,
        metavar="NAME=VALUE",
        help=(
            "Repeatable additional Grafana dashboard variable. Names must be "
            "bounded identifiers; values are URL-encoded before rendering."
        ),
    )
    parser.add_argument("--range-hours", type=int, default=12)
    parser.add_argument(
        "--occurrence-id",
        default="",
        help="Bind render evidence to one dashboard release occurrence.",
    )
    parser.add_argument(
        "--expand-collapsed-rows",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Expand every collapsed row before terminal-state validation. "
            "Enabled by default for full-surface audit evidence."
        ),
    )
    parser.add_argument(
        "--capture-surface",
        choices=("viewport", "full"),
        default="full",
        help="Capture only the requested viewport or the full dashboard surface.",
    )
    parser.add_argument(
        "--kiosk-mode",
        choices=("off", "full", "tv"),
        default="off",
        help="Explicit Grafana kiosk state to request and verify in Playwright.",
    )
    parser.add_argument(
        "--browser-zoom",
        type=int,
        choices=range(50, 201),
        default=100,
        metavar="PERCENT",
        help="Browser zoom percentage recorded and applied by Playwright.",
    )
    parser.add_argument(
        "--navigation-only",
        action="store_true",
        help=(
            "Render and validate only navigation panel id=1000. This keeps "
            "navigation geometry and typography evidence independent from "
            "optional datasource availability."
        ),
    )
    return parser


def _resolve_render_fixture_state(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[Path | None, dict[str, object] | None, str]:
    fixture_manifest = (
        args.fixture_manifest.resolve() if args.fixture_manifest is not None else None
    )
    fixture_case = str(getattr(args, "fixture_case", "") or "").strip()
    try:
        fixture_state = _load_render_fixture_state(
            fixture_manifest=fixture_manifest,
            fixture_case=fixture_case,
            parser=parser,
        )
    except ValueError as exc:
        parser.error(str(exc))
    return fixture_manifest, fixture_state, fixture_case


def _load_render_fixture_state(
    *,
    fixture_manifest: Path | None,
    fixture_case: str,
    parser: argparse.ArgumentParser,
) -> dict[str, object] | None:
    if fixture_case:
        if fixture_manifest is None:
            parser.error("--fixture-case requires --fixture-manifest")
        from scripts.ops.observability.grafana.dashboard_state_fixture_v2 import (
            fixture_case_evidence,
            load_v2_case,
        )

        return fixture_case_evidence(load_v2_case(fixture_manifest, fixture_case))
    if fixture_manifest is None:
        return None
    return _fixture_state_evidence_from_path(fixture_manifest)


def _parse_args(argv: list[str] | None) -> RenderConfig:
    """Parse command-line arguments for Grafana screenshot rendering."""
    parser = _build_render_parser()
    args = parser.parse_args(argv)
    variables = _deduplicate_dashboard_variables(args.variables, parser=parser)
    fixture_manifest, fixture_state, fixture_case = _resolve_render_fixture_state(
        args, parser
    )
    return RenderConfig(
        base_url=args.base_url.rstrip("/"),
        username=args.username,
        password=args.password,
        service_account_token=args.service_account_token,
        output_dir=args.output_dir.resolve(),
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
        occurrence_id=str(args.occurrence_id).strip(),
        capture_surface=str(args.capture_surface),
        kiosk_mode=str(args.kiosk_mode),
        browser_zoom=int(args.browser_zoom),
        variables=variables,
        navigation_only=bool(args.navigation_only),
        fixture_manifest=fixture_manifest,
        fixture_state=fixture_state,
        fixture_case=fixture_case,
    )


def _parse_dashboard_variable(value: str) -> tuple[str, str]:
    """Parse one bounded ``NAME=VALUE`` dashboard-variable assignment."""
    name, separator, raw_value = value.partition("=")
    name = name.strip()
    if not separator or not _DASHBOARD_VARIABLE_NAME_RE.fullmatch(name):
        raise argparse.ArgumentTypeError(
            "dashboard variables must use NAME=VALUE with a name matching "
            "[A-Za-z][A-Za-z0-9_]{0,63}"
        )
    if not raw_value:
        raise argparse.ArgumentTypeError(
            f"dashboard variable {name!r} must have a non-empty value"
        )
    if len(raw_value) > 1024:
        raise argparse.ArgumentTypeError(
            f"dashboard variable {name!r} exceeds the 1024-character value limit"
        )
    return name, raw_value


def _deduplicate_dashboard_variables(
    assignments: list[tuple[str, str]], *, parser: argparse.ArgumentParser
) -> tuple[tuple[str, str], ...]:
    """Return stable unique assignments and reject conflicting duplicates."""
    values: dict[str, str] = {}
    for name, value in assignments:
        previous = values.get(name)
        if previous is not None and previous != value:
            parser.error(f"dashboard variable {name!r} was assigned conflicting values")
        values[name] = value
    return tuple(sorted(values.items()))


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
    for name, value in config.variables:
        key = f"var-{name}"
        existing = params.get(key)
        if existing is not None and existing != value:
            raise ValueError(
                f"dashboard variable {name!r} conflicts with a dedicated scope option"
            )
        params[key] = value
    if config.kiosk_mode == "full":
        params["kiosk"] = "1"
    elif config.kiosk_mode == "tv":
        params["kiosk"] = "tv"
    return params


def _scope_manifest(config: RenderConfig) -> dict[str, object]:
    """Return structured, reproducible dashboard scope provenance."""
    return {
        "workflow": config.workflow,
        "pipeline": config.pipeline,
        "run_type": config.run_type,
        "run_id": config.run_id,
        "range_hours": config.range_hours,
        "variables": dict(config.variables),
    }


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
    atomic_write_bytes(
        target,
        _download_binary(
            render_url,
            headers=_auth_headers(config),
            timeout_seconds=config.timeout_seconds,
        ),
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
        "occurrence_id": config.occurrence_id,
        "base_url": config.base_url,
        "engine": "grafana-render-api",
        "width": config.width,
        "height": config.height,
        "requested": {
            "viewport": {"width": config.width, "height": config.height},
            "theme": config.theme,
            "capture_surface": config.capture_surface,
            "kiosk_mode": config.kiosk_mode,
            "browser_zoom": config.browser_zoom,
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
        "backend_applicability": {
            "quarantine_explorer": {
                "state": "NOT_APPLICABLE",
                "reason": "Quarantine Explorer HTTP/UI surface is retired from shipping.",
            }
        },
        "selected_uids": list(config.selected_uids),
        "scope": _scope_manifest(config),
        "dashboards": [
            _dashboard_manifest_entry(
                record=record,
                path=path,
                output_dir=config.output_dir,
                viewport=actual_viewports.get(record.uid),
            )
            for record, path in rendered
        ],
        "render_results": [asdict(result) for result in render_results],
    }
    _finalize_manifest(config, manifest)


def _dashboard_manifest_entry(
    *,
    record: DashboardRecord,
    path: Path,
    output_dir: Path,
    viewport: tuple[int, int] | None,
) -> dict[str, object]:
    """Build one dashboard row for the render manifest."""
    rel = str(path.relative_to(output_dir))
    width = viewport[0] if viewport is not None else None
    height = viewport[1] if viewport is not None else None
    return {
        **asdict(record),
        "file": rel,
        "screenshot": rel,
        "screenshotEvidence": {
            "file": rel,
            "bytes": path.stat().st_size,
            "width": width,
            "height": height,
            "sha256": _sha256_file(path),
        },
    }


def _png_dimensions(path: Path) -> tuple[int, int] | None:
    """Return PNG IHDR dimensions without requiring an image dependency."""
    try:
        header = path.read_bytes()[:24]
    except OSError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return int.from_bytes(header[16:20], "big"), int.from_bytes(header[20:24], "big")


def _materially_blank_png_problem(path: Path) -> str | None:
    """Return a problem string when a PNG is too small or near-uniform (#6686)."""
    try:
        payload = path.read_bytes()
    except OSError as exc:
        return f"screenshot is unreadable: {exc}"
    if len(payload) < 1000:
        return "screenshot is materially blank (file too small)"
    sample_step = max(1, len(payload) // 4000)
    counts: dict[int, int] = {}
    samples = 0
    for index in range(0, len(payload), sample_step):
        byte = payload[index]
        counts[byte] = counts.get(byte, 0) + 1
        samples += 1
    if samples < 100:
        return "screenshot is materially blank (insufficient sample)"
    top = max(counts.values())
    dominance = top / samples
    if dominance >= 0.92 and len(counts) <= 24:
        return "screenshot is materially blank (near-uniform pixels)"
    return None


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
    # Prefer a local (non-GDrive) install when present — Chromium launch from
    # network/cloud-synced repo paths is flaky on Windows.
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        local_nm = Path(local_app_data) / "bioetl-playwright" / "node_modules"
        if _path_has_playwright_package(local_nm):
            return str(local_nm)
    repo_node_modules = _repo_root() / "node_modules"
    if _path_has_playwright_package(repo_node_modules):
        return str(repo_node_modules)
    if _path_has_playwright_package(DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES):
        return str(DEFAULT_TOOL_PLAYWRIGHT_NODE_MODULES)
    return ""


def _default_playwright_browsers_path() -> str:
    # Prefer a local non-network drive for browser binaries when available.
    # GDrive/WSL /mnt paths make Chromium launch flaky/slow on Windows hosts.
    configured = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured:
        return configured
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        local_ms = Path(local_app_data) / "ms-playwright"
        if local_ms.exists():
            return str(local_ms)
    if DEFAULT_TOOL_PLAYWRIGHT_BROWSERS.exists():
        return str(DEFAULT_TOOL_PLAYWRIGHT_BROWSERS)
    return ""


def _discover_playwright_chromium_executable(browsers_path: str = "") -> str:
    """Locate a Chromium binary under the Playwright browsers cache."""
    configured = (
        os.getenv("PLAYWRIGHT_EXECUTABLE_PATH", "").strip()
        or os.getenv("CHROME_EXE", "").strip()
        or os.getenv("CHROMIUM_PATH", "").strip()
    )
    if configured and Path(configured).exists():
        return configured

    root = Path(browsers_path or _default_playwright_browsers_path())
    if not root.exists():
        return ""

    patterns = (
        "chromium-*/chrome-win/chrome.exe",
        "chromium-*/chrome-win64/chrome.exe",
        "chromium_headless_shell-*/chrome-win/headless_shell.exe",
        "chromium_headless_shell-*/chrome-win64/headless_shell.exe",
        "chromium-*/chrome-linux/chrome",
        "chromium-*/chrome-linux64/chrome",
        "chromium_headless_shell-*/chrome-linux/headless_shell",
        "chromium_headless_shell-*/chrome-linux64/headless_shell",
    )
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(path for path in root.glob(pattern) if path.is_file())
    if not candidates:
        return ""
    # Prefer older stable revisions first when multiple caches exist — the
    # package-pinned revision (e.g. 1148 for playwright 1.49) is more reliable
    # than tip-of-tree builds that may not match the installed package.
    candidates.sort(key=lambda item: item.as_posix())
    return str(candidates[0])


def _playwright_process_cwd() -> str:
    """Use a local temp cwd for Playwright/Chromium; GDrive cwd can hang launch."""
    configured = os.getenv("BIOETL_PLAYWRIGHT_CWD", "").strip()
    if configured:
        path = Path(configured)
        path.mkdir(parents=True, exist_ok=True)
        return str(path)
    import tempfile

    return tempfile.gettempdir()


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

    executable = _discover_playwright_chromium_executable(browsers_path)
    if executable:
        env["PLAYWRIGHT_EXECUTABLE_PATH"] = executable

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
    env["GRAFANA_SCREENSHOT_CAPTURE_SURFACE"] = config.capture_surface
    env["GRAFANA_SCREENSHOT_KIOSK_MODE"] = config.kiosk_mode
    env["GRAFANA_SCREENSHOT_BROWSER_ZOOM"] = str(config.browser_zoom)
    env["GRAFANA_SCREENSHOT_NAVIGATION_ONLY"] = (
        "true" if config.navigation_only else "false"
    )
    if config.fixture_manifest is not None:
        env["GRAFANA_SCREENSHOT_FIXTURE_MANIFEST"] = str(config.fixture_manifest)
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
            "--capture-surface",
            config.capture_surface,
            "--kiosk-mode",
            config.kiosk_mode,
            "--browser-zoom",
            str(config.browser_zoom),
        ]
    )
    if config.navigation_only:
        node_command.append("--navigation-only")
    scope_query = urlencode(_scope_query_params(config))
    if scope_query:
        node_command.extend(["--scope-query", scope_query])
    try:
        # Keep Chromium launch off GDrive paths; the .cjs script resolves the
        # repo from its own __dirname so repo-relative inventory still works.
        result = subprocess.run(
            node_command,
            check=False,
            cwd=_playwright_process_cwd(),
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
        "occurrence_id": config.occurrence_id,
        "engine": "playwright",
        "base_url": config.base_url,
        "scope_query": scope_query,
        "scope": _scope_manifest(config),
        "timeout_ms": int(config.timeout_seconds * 1000),
        "capture_timeout_ms": capture_timeout_ms,
        "requested": {
            "viewport": {"width": config.width, "height": config.height},
            "theme": config.theme,
            "capture_surface": config.capture_surface,
            "kiosk_mode": config.kiosk_mode,
            "browser_zoom": config.browser_zoom,
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
        "navigation_only": config.navigation_only,
        "backend_applicability": {
            "quarantine_explorer": {
                "state": "NOT_APPLICABLE",
                "reason": "Quarantine Explorer HTTP/UI surface is retired from shipping.",
            }
        },
        "dashboards": dashboards,
    }
    _finalize_manifest(config, merged)


def _dashboard_render_status_problem(
    dashboard: dict[str, Any], *, uid: str
) -> str | None:
    if dashboard.get("renderStatus") != "rendered":
        return f"dashboard {uid} did not reach rendered status"
    rendered_count = dashboard.get("renderedPanelCount", 0)
    if not isinstance(rendered_count, int) or rendered_count <= 0:
        return f"dashboard {uid} contains no rendered panel markers"
    return None


def _dashboard_screenshot_file_problem(
    dashboard: dict[str, Any],
    *,
    uid: str,
    config: RenderConfig,
) -> tuple[str | None, str | None, Path | None, int | None]:
    """Return (problem, file_name, path, size) for a dashboard screenshot file."""
    file_name = dashboard.get("file") or dashboard.get("screenshot")
    if not isinstance(file_name, str) or not file_name:
        return (
            f"dashboard {uid} does not identify its screenshot file",
            None,
            None,
            None,
        )
    screenshot_path = config.output_dir / file_name
    try:
        screenshot_size = screenshot_path.stat().st_size
    except OSError as exc:
        return f"dashboard {uid} screenshot is unreadable: {exc}", None, None, None
    return None, file_name, screenshot_path, screenshot_size


def _dashboard_screenshot_geometry_problem(
    *,
    uid: str,
    config: RenderConfig,
    screenshot_path: Path,
) -> tuple[str | None, tuple[int, int] | None]:
    dimensions = _png_dimensions(screenshot_path)
    if dimensions is None:
        return f"dashboard {uid} screenshot is not a valid PNG", None
    if dimensions[0] != config.width or dimensions[1] <= 0:
        return (
            f"dashboard {uid} screenshot dimensions drift: "
            f"requested_width={config.width} actual={dimensions}"
        ), None
    return None, dimensions


def _dashboard_screenshot_evidence_problem(
    dashboard: dict[str, Any],
    *,
    uid: str,
    file_name: str,
    screenshot_size: int,
    dimensions: tuple[int, int],
) -> str | None:
    evidence = dashboard.get("screenshotEvidence")
    if not isinstance(evidence, dict):
        return f"dashboard {uid} lacks screenshotEvidence"
    if evidence.get("file") != file_name:
        return f"dashboard {uid} screenshot filename evidence drift"
    if evidence.get("bytes") != screenshot_size:
        return f"dashboard {uid} screenshot byte-size evidence drift"
    if (
        evidence.get("width") != dimensions[0]
        or evidence.get("height") != dimensions[1]
    ):
        return f"dashboard {uid} screenshot dimension evidence drift"
    return None


def _one_dashboard_screenshot_problem(
    dashboard: object,
    *,
    config: RenderConfig,
) -> str | None:
    if not isinstance(dashboard, dict):
        return "render manifest contains a malformed dashboard record"
    uid = str(dashboard.get("uid", "unknown"))
    status_problem = _dashboard_render_status_problem(dashboard, uid=uid)
    if status_problem is not None:
        return status_problem
    file_problem, file_name, screenshot_path, screenshot_size = (
        _dashboard_screenshot_file_problem(dashboard, uid=uid, config=config)
    )
    if file_problem is not None:
        return file_problem
    assert file_name is not None and screenshot_path is not None
    assert screenshot_size is not None
    geometry_problem, dimensions = _dashboard_screenshot_geometry_problem(
        uid=uid,
        config=config,
        screenshot_path=screenshot_path,
    )
    if geometry_problem is not None:
        return geometry_problem
    assert dimensions is not None
    evidence_problem = _dashboard_screenshot_evidence_problem(
        dashboard,
        uid=uid,
        file_name=file_name,
        screenshot_size=screenshot_size,
        dimensions=dimensions,
    )
    if evidence_problem is not None:
        return evidence_problem
    blank_problem = _materially_blank_png_problem(screenshot_path)
    if blank_problem is not None:
        return f"dashboard {uid} {blank_problem}"
    return None


def _playwright_manifest_screenshot_problem(
    config: RenderConfig, manifest: dict[str, Any]
) -> str | None:
    dashboards = manifest.get("dashboards", [])
    if not isinstance(dashboards, list) or not dashboards:
        return "render manifest contains no dashboard screenshot evidence"

    for dashboard in dashboards:
        problem = _one_dashboard_screenshot_problem(dashboard, config=config)
        if problem is not None:
            return problem
    return None


def _run_playwright_with_retry(
    config: RenderConfig,
) -> tuple[int, dict[str, Any] | None]:
    for attempt in range(2):
        result = _run_playwright_process(config)
        if result != 0:
            return result, None
        try:
            manifest = _read_playwright_manifest(
                config.output_dir / _RENDER_MANIFEST_JSON
            )
        except RuntimeError as exc:
            print(str(exc))
            return 1, None
        problem = _playwright_manifest_screenshot_problem(config, manifest)
        if problem is None:
            return 0, manifest
        if attempt == 1:
            print(f"Playwright screenshot validation failed after retry: {problem}")
            return 1, None
        print(f"Retrying Playwright render once after screenshot validation: {problem}")
        time.sleep(2.0)
    return 1, None


def _run_playwright_fallback(config: RenderConfig) -> int:
    dashboards = _load_dashboards(config)
    if len(dashboards) <= 1:
        result, manifest = _run_playwright_with_retry(config)
        if result != 0 or manifest is None:
            return result or 1
        _write_merged_playwright_manifest(config, [manifest])
        return 0

    manifests: list[dict[str, Any]] = []
    for dashboard in dashboards:
        single_config = cast(
            RenderConfig,
            replace(config, selected_uids=(dashboard.uid,)),
        )
        result, manifest = _run_playwright_with_retry(single_config)
        if result != 0 or manifest is None:
            return result or 1
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
        # Launch from a local temp cwd: GDrive/repo cwd can hang Chromium on Windows.
        probe_cwd = _playwright_process_cwd()
        result = subprocess.run(
            [
                node_path,
                "-e",
                (
                    "const { chromium } = require('playwright');"
                    "(async () => {"
                    " const opts = { headless: true, args: "
                    "['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'] };"
                    " const exe = process.env.PLAYWRIGHT_EXECUTABLE_PATH || '';"
                    " if (exe) { opts.executablePath = exe; }"
                    " const browser = await chromium.launch(opts);"
                    " process.stdout.write(exe || chromium.executablePath());"
                    " await browser.close();"
                    "})().catch((error) => {"
                    " console.error(String(error && error.message ? error.message : error));"
                    " process.exit(1);"
                    "});"
                ),
            ],
            check=False,
            cwd=probe_cwd,
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


def _missing_credentials_message() -> str:
    return (
        "Grafana render credentials are missing. Set "
        "GF_SECURITY_ADMIN_PASSWORD / GRAFANA_PASSWORD / "
        "GRAFANA_ADMIN_PASSWORD or GRAFANA_SERVICE_ACCOUNT_TOKEN."
    )


def _maybe_playwright_fallback(config: RenderConfig) -> int:
    if config.fallback == "auto":
        return _run_playwright_fallback(config)
    return 1


def _handle_render_api_failure(config: RenderConfig, exc: RenderApiFailure) -> int:
    print(
        _render_failure_message(
            config,
            prefix=str(exc),
            auto_fallback=config.fallback == "auto",
        )
    )
    return _maybe_playwright_fallback(config)


def _handle_render_http_error(config: RenderConfig, exc: HTTPError) -> int:
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
    return _maybe_playwright_fallback(config)


def main(argv: list[str] | None = None) -> int:
    config = _parse_args(argv)
    if not config.service_account_token and not config.password:
        print(_missing_credentials_message())
        return EXIT_CREDENTIALS
    config.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if config.fallback == "playwright":
            return _run_playwright_fallback(config)
        _render_via_api(config)
    except RenderApiFailure as exc:
        return _handle_render_api_failure(config, exc)
    except HTTPError as exc:
        return _handle_render_http_error(config, exc)
    except URLError as exc:
        # URLError subclasses OSError — handle before generic OSError (S1045).
        print(f"URL error: {exc.reason}")
        if config.fallback == "auto":
            print("Falling back to Playwright screenshot capture.")
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
    except RuntimeError as exc:
        print(str(exc))
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
