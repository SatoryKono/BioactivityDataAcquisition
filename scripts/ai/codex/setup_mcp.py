#!/usr/bin/env python3
"""Canonical entrypoint for AI assistant MCP workspace setup."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
# ``python scripts/ai/codex/setup_mcp.py`` (Zed task) does not put the repo root
# on sys.path, so ``import scripts...`` fails without this bootstrap.
_REPO_ROOT_STR = str(REPO_ROOT)
if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)

from scripts.ai.mcp.wrappers import load_wrapper_specs
from scripts.engineering.common.platform import detect_platform

MANAGED_BLOCK_BEGIN = "# === BEGIN MANAGED MCP SERVERS ==="
MANAGED_BLOCK_END = "# === END MANAGED MCP SERVERS ==="
MCP_JSON_FILENAME = "mcp.json"
DEVIN_MCP_CONFIG_FILENAME = "mcp_config.json"
CACHE_DIR_NAME = ".cache"
CODEX_RUNTIME_CACHE_DIR_NAME = "bioetl-mcp"
DEEPWIKI_API_KEY_ENV_VAR = "DEEPWIKI_API_KEY"
DEEPWIKI_ORGANISATION_ID_ENV_VAR = "DEEPWIKI_ORGANISATION_ID"
REF_API_KEY_ENV_VAR = "REF_TOOL_API_KEY"
REMOVED_MCP_SERVER_NAMES = frozenset(
    {
        "sonarqube",
        "chembl",
        "pubchem",
        "pubmed",
        "sequential-thinking",
        "openaiDeveloperDocs",
        "needle",
        "docker-docs",
        "dockerhub",
        "pdf",
        "paper-search",
        "biomoltechDocs",
        "mintlify",
    }
)

# Least-privilege local materialization profiles. Tracked portable inventory
# stays full unless a separate reviewed change says otherwise.
#
# Docker-backed MCP (stdio `docker run` / `docker mcp gateway`) multiplies
# containers per AI client session and is a primary thrash source on 32 GiB
# hosts. Prefer `stable` or `core` for daily work; enable graph/full only when
# the task needs those tools.
MCP_PROFILE_STABLE = (
    # No Docker/gateway/stdio container MCP — host process or remote HTTP only.
    "memory",
    "filesystem",
    "fetch",
    "github",
    "context7",
    "ast-grep",
    "deja",
    "adr-analysis",
    "code-analyzer",
    "ref",
)
# Multi-client default: every sanctioned local server is projected to the
# shared HTTP plane. Remote HTTP servers remain remote and are naturally
# multi-client. Keep membership explicit so profile drift is reviewable.
MCP_PROFILE_SHARED = MCP_PROFILE_STABLE + (
    # Credentialed remote research is opt-in, never part of daily doctor.
    "deepwiki",
    "brave-search",
    "prometheus",
    "grafana",
    "docker",
    "mermaid",
    "mcp-code-interpreter",
    "neo4j-cypher",
    "neo4j-memory",
    "mutmut",
    "github-actions",
)
MCP_PROFILE_CORE = MCP_PROFILE_STABLE + (
    # mermaid still uses docker mcp gateway under stdio; HTTP when shared plane.
    "mermaid",
)
MCP_PROFILE_OPS = MCP_PROFILE_CORE + (
    "prometheus",
    "grafana",
    "github-actions",
)
MCP_PROFILE_GRAPH = MCP_PROFILE_OPS + (
    "neo4j-cypher",
    "neo4j-memory",
    "brave-search",
    "mutmut",
    "mcp-code-interpreter",
    "docker",
)
MCP_PROFILES: dict[str, tuple[str, ...] | None] = {
    "stable": MCP_PROFILE_STABLE,
    "shared": MCP_PROFILE_SHARED,
    "core": MCP_PROFILE_CORE,
    "ops": MCP_PROFILE_OPS,
    "graph": MCP_PROFILE_GRAPH,
    # full = entire sanctioned inventory from _canonical_servers
    "full": None,
}

# Live readiness is intentionally narrower than materialization. A profile may
# expose optional tools without making them part of the launch gate. `stable`
# is the daily capability set; `core` is the explicit diagram profile, `ops`
# requires only operations services, and `graph` requires only graph add-ons.
# `full` is explicit and therefore requires the complete selected inventory.
MCP_PROFILE_REQUIRED: dict[str, tuple[str, ...] | None] = {
    "stable": MCP_PROFILE_STABLE,
    "shared": MCP_PROFILE_STABLE,
    "core": MCP_PROFILE_STABLE + ("mermaid",),
    "ops": MCP_PROFILE_STABLE + ("prometheus", "grafana", "github-actions"),
    "graph": MCP_PROFILE_STABLE + ("neo4j-cypher", "neo4j-memory"),
    "full": None,
}


def mcp_profile_requirements(
    profile: str, selected_servers: tuple[str, ...] | list[str] | set[str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return deterministic required/optional server names for *profile*."""

    if profile not in MCP_PROFILES:
        raise ValueError(
            f"Unknown MCP profile {profile!r}; expected one of {sorted(MCP_PROFILES)}"
        )
    selected = set(selected_servers)
    configured_required = MCP_PROFILE_REQUIRED[profile]
    required = selected if configured_required is None else set(configured_required)
    unknown_required = required - selected
    if unknown_required:
        raise ValueError(
            f"MCP profile {profile!r} requires unselected servers: "
            f"{sorted(unknown_required)}"
        )
    return tuple(sorted(required)), tuple(sorted(selected - required))


SHARED_SERVER_CATALOG_PATH = REPO_ROOT / "scripts/ops/runtime/mcp/shared-servers.json"


def _load_shared_server_endpoints(
    catalog_path: Path = SHARED_SERVER_CATALOG_PATH,
) -> dict[str, str]:
    """Load localhost endpoints from the shared runtime SSOT."""
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    servers = payload.get("servers")
    if not isinstance(servers, dict) or not servers:
        raise ValueError(f"Shared MCP catalog has no servers: {catalog_path}")
    endpoints: dict[str, str] = {}
    ports: set[int] = set()
    for name, entry in servers.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            raise ValueError(f"Invalid shared MCP catalog entry: {name!r}")
        port = int(entry["port"])
        if port in ports:
            raise ValueError(f"Duplicate shared MCP port {port}")
        ports.add(port)
        path = str(entry.get("path") or "/mcp")
        if not path.startswith("/"):
            raise ValueError(f"Shared MCP path must start with '/': {name}={path!r}")
        endpoints[name] = f"http://127.0.0.1:{port}{path}"
    return endpoints


# Localhost Streamable HTTP endpoints for multi-client shared plane (#6563/#6589).
# The JSON catalog is the single source of truth for names, ports, and paths.
MCP_SHARED_SERVER_ENDPOINTS = _load_shared_server_endpoints()
TRANSPORT_MODES = frozenset({"stdio", "shared", "hybrid"})
# Multi-client daily defaults for Codex ensure / local projections.
DEFAULT_LOCAL_PROFILE = "stable"
DEFAULT_LOCAL_TRANSPORT_MODE = "shared"
# Tracked Devin projection stays full sanctioned inventory.
DEVIN_TRACKED_PROFILE = "full"
# Devin daily multi-client: omit gateway thrash leaders (use graph/full when needed).
DEVIN_DAILY_DISABLE_SERVERS = frozenset(
    {
        "docker",
        "mermaid",
        "dockerhub",
        "mcp-code-interpreter",
        "neo4j-cypher",
        "neo4j-memory",
        "mutmut",
        "sonarqube",
        "needle",
    }
)


def _add_startup_timeouts(servers: dict[str, dict[str, Any]]) -> None:
    startup_timeouts = {
        "fetch": 300,
        "context7": 240,
        "docker": 240,
        "mermaid": 300,
        "memory": 120,
        "github": 180,
        "brave-search": 180,
        "prometheus": 240,
        "grafana": 240,
        "github-actions": 180,
        "ast-grep": 120,
        "mcp-code-interpreter": 240,
        "neo4j-cypher": 120,
        "neo4j-memory": 120,
        "code-analyzer": 120,
        "adr-analysis": 120,
        "mutmut": 120,
        "deja": 120,
        "deepwiki": 240,
        "ref": 120,
    }
    for server_name, timeout in startup_timeouts.items():
        if server_name in servers:
            servers[server_name]["startup_timeout_sec"] = timeout


# Allowlist of approved remote MCP server base URLs for security governance.
# Any new remote HTTP MCP server must be added to this allowlist after security review.
APPROVED_REMOTE_MCP_BASE_URLS = frozenset(
    {
        "https://mcp.deepwiki.com/mcp",
        "https://api.ref.tools/mcp",
    }
)

# Local shared plane only — never treat these as remote SaaS MCP.
APPROVED_LOCAL_MCP_BASE_URL_PREFIXES = (
    "http://127.0.0.1:",
    "http://localhost:",
)


def _config_path(
    path: Path,
    workspace_root: Path,
    *,
    portable_workspace_paths: bool,
) -> str:
    resolved_workspace = workspace_root.resolve()
    resolved_path = path.resolve()
    if not portable_workspace_paths:
        return str(resolved_path)
    if resolved_path == resolved_workspace:
        return "."
    return resolved_path.relative_to(resolved_workspace).as_posix()


def _wrapper_command(
    script_name: str,
    workspace_root: Path,
    *,
    portable_workspace_paths: bool,
    wrapper_platform: str | None = None,
) -> dict[str, Any]:
    """Build a stdio MCP wrapper invocation.

    ``wrapper_platform``:
      * ``None`` — host OS (``os.name``)
      * ``\"posix\"`` — always bash + ``.sh`` (tracked portable SSOT)
      * ``\"nt\"`` — always PowerShell + ``.ps1``
    """
    platform = wrapper_platform or detect_platform().wrapper_platform
    if platform not in {"nt", "posix"}:
        raise ValueError(
            f"Unknown wrapper_platform {wrapper_platform!r}; expected 'nt', 'posix', or None"
        )
    is_windows = platform == "nt"
    shell = "powershell" if is_windows else "bash"
    suffix = ".ps1" if is_windows else ".sh"
    wrapper = (workspace_root / "scripts/ai/mcp" / script_name).with_suffix(suffix)
    wrapper_arg = _config_path(
        wrapper,
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )

    return {"command": shell, "args": [wrapper_arg]}


def _http_server(url: str) -> dict[str, Any]:
    if url not in APPROVED_REMOTE_MCP_BASE_URLS:
        raise ValueError(
            f"Remote MCP server URL not in approved allowlist: {url}. "
            f"Approved URLs: {sorted(APPROVED_REMOTE_MCP_BASE_URLS)}. "
            "Add new remote MCP servers to APPROVED_REMOTE_MCP_BASE_URLS after security review."
        )
    return {"type": "http", "url": url}


def _local_http_server(url: str, *, startup_timeout_sec: int = 30) -> dict[str, Any]:
    """Emit a localhost shared-plane HTTP MCP entry (not remote SaaS)."""
    if not url.startswith(APPROVED_LOCAL_MCP_BASE_URL_PREFIXES):
        raise ValueError(
            f"Local shared MCP URL not under approved localhost prefixes: {url}. "
            f"Allowed prefixes: {APPROVED_LOCAL_MCP_BASE_URL_PREFIXES}"
        )
    return {
        "type": "http",
        "url": url,
        "startup_timeout_sec": startup_timeout_sec,
    }


def _apply_shared_transport(
    servers: dict[str, dict[str, Any]],
    *,
    transport_mode: str,
) -> dict[str, dict[str, Any]]:
    """Rewrite shared-capable servers to localhost HTTP when mode is shared/hybrid.

    Tracked portable projections must call this with transport_mode='stdio' only.
    """
    if transport_mode not in TRANSPORT_MODES:
        raise ValueError(
            f"Unknown transport mode {transport_mode!r}; expected one of "
            f"{sorted(TRANSPORT_MODES)}"
        )
    if transport_mode == "stdio":
        return servers
    rewritten = deepcopy(servers)
    for name, url in MCP_SHARED_SERVER_ENDPOINTS.items():
        if name not in rewritten:
            continue
        timeout = int(rewritten[name].get("startup_timeout_sec", 30))
        rewritten[name] = _local_http_server(url, startup_timeout_sec=timeout)
    return rewritten


def _npx_server(*args: str, npm_cache_dir: str) -> dict[str, Any]:
    return {
        "command": "npx",
        "args": ["-y", *args],
        "env": {"NPM_CONFIG_CACHE": npm_cache_dir},
    }


def _filter_servers_for_profile(
    servers: dict[str, dict[str, Any]],
    *,
    profile: str,
) -> dict[str, dict[str, Any]]:
    """Return a profile-filtered copy of *servers* (never emits retired names)."""
    if profile not in MCP_PROFILES:
        raise ValueError(
            f"Unknown MCP profile {profile!r}; expected one of {sorted(MCP_PROFILES)}"
        )
    allowed = MCP_PROFILES[profile]
    if allowed is None:
        filtered = {
            name: cfg
            for name, cfg in servers.items()
            if name not in REMOVED_MCP_SERVER_NAMES
        }
    else:
        allowed_set = set(allowed)
        missing = sorted(allowed_set - set(servers))
        if missing:
            raise ValueError(
                f"MCP profile {profile!r} references unknown servers: {missing}"
            )
        filtered = {
            name: cfg
            for name, cfg in servers.items()
            if name in allowed_set and name not in REMOVED_MCP_SERVER_NAMES
        }
    return filtered


def _canonical_servers(
    workspace_root: Path,
    *,
    portable_workspace_paths: bool = False,
    profile: str = "full",
    wrapper_platform: str | None = None,
) -> dict[str, dict[str, Any]]:
    workspace_root_str = _config_path(
        workspace_root,
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    memory_file_path = _config_path(
        workspace_root / "docs/00-project/ai/memory/mcp-memory.json",
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    adr_path = _config_path(
        workspace_root / "docs/02-architecture/decisions",
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    cache_root = workspace_root / CACHE_DIR_NAME

    npm_cache_dir = _config_path(
        cache_root / "npm-cache",
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    uv_cache_dir = _config_path(
        cache_root / "uv-cache",
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    uv_tool_dir = _config_path(
        cache_root / "uv-tools",
        workspace_root,
        portable_workspace_paths=portable_workspace_paths,
    )
    # Wrapper ownership comes from shared-servers.json.  The retained shell and
    # PowerShell implementations are compatibility backends during migration;
    # setup no longer carries a parallel hand-maintained mapping.
    servers: dict[str, dict[str, Any]] = {
        server_name: _wrapper_command(
            spec.wrapper_stem,
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
            wrapper_platform=wrapper_platform,
        )
        for server_name, spec in load_wrapper_specs().items()
    }
    servers.update(
        {
            "deepwiki": _http_server("https://mcp.deepwiki.com/mcp"),
            "ref": _http_server("https://api.ref.tools/mcp"),
        }
    )
    servers["deepwiki"]["env_http_headers"] = {
        "x-deepwiki-api-key": DEEPWIKI_API_KEY_ENV_VAR,
        "x-deepwiki-organisation-id": DEEPWIKI_ORGANISATION_ID_ENV_VAR,
    }
    servers["ref"]["env_http_headers"] = {
        "x-ref-api-key": REF_API_KEY_ENV_VAR,
    }

    # Preserve the committed config shape where wrappers receive npm cache.
    servers["filesystem"]["env"] = {"NPM_CONFIG_CACHE": npm_cache_dir}
    servers["fetch"]["env"] = {
        "UV_CACHE_DIR": uv_cache_dir,
        "UV_TOOL_DIR": uv_tool_dir,
        "NPM_CONFIG_CACHE": npm_cache_dir,
    }
    servers["github"]["env"] = {"NPM_CONFIG_CACHE": npm_cache_dir}
    servers["memory"]["env"] = {
        "NPM_CONFIG_CACHE": npm_cache_dir,
        "MEMORY_FILE_PATH": str(memory_file_path),
    }
    servers["deja"]["env"] = {"NPM_CONFIG_CACHE": npm_cache_dir}
    servers["adr-analysis"]["env"] = {
        "PROJECT_PATH": workspace_root_str,
        "ADR_PATH": adr_path,
    }
    if "mutmut" in servers:
        servers["mutmut"]["env"] = {"MUTMUT_PROJECT_PATH": workspace_root_str}
    if "code-analyzer" in servers:
        servers["code-analyzer"]["env"] = {"PROJECT_PATH": workspace_root_str}
    _add_startup_timeouts(servers)
    return _filter_servers_for_profile(servers, profile=profile)


def _codex_runtime_servers(
    workspace_root: Path,
    *,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> dict[str, dict[str, Any]]:
    """Return local Codex servers with WSL-safe runtime cache paths.

    Tracked MCP projections keep repo-relative cache paths for portability.  The
    Codex user runtime must not put npm/uv caches on a Windows-mounted workspace,
    where atomic rename and cleanup operations are unreliable under WSL.
    """
    servers = _apply_shared_transport(
        deepcopy(_canonical_servers(workspace_root, profile=profile)),
        transport_mode=transport_mode,
    )
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    cache_home = (
        Path(xdg_cache_home).expanduser()
        if xdg_cache_home
        else Path.home() / CACHE_DIR_NAME
    )
    runtime_cache_root = cache_home / CODEX_RUNTIME_CACHE_DIR_NAME
    npm_cache_dir = str(runtime_cache_root / "npm-cache")
    npm_backed_servers = {
        "memory",
        "filesystem",
        "fetch",
        "github",
        "context7",
        "ast-grep",
        "mcp-code-interpreter",
        "neo4j-cypher",
        "neo4j-memory",
        "mermaid",
        "deja",
        "adr-analysis",
        "mutmut",
        "code-analyzer",
        "github-actions",
    }

    def _is_http_server(server: dict[str, Any]) -> bool:
        """Streamable HTTP / remote entries must not carry stdio env tables.

        Codex rejects ``env`` on ``streamable_http`` (url-based) servers.
        """
        if server.get("type") == "http":
            return True
        return bool(server.get("url")) and "command" not in server

    for server_name in npm_backed_servers:
        if server_name not in servers:
            continue
        if _is_http_server(servers[server_name]):
            # Shared-plane HTTP: cache env belongs to the long-lived proxy, not the client.
            servers[server_name].pop("env", None)
            continue
        server_env = servers[server_name].setdefault("env", {})
        server_env["NPM_CONFIG_CACHE"] = npm_cache_dir

    if "fetch" in servers and not _is_http_server(servers["fetch"]):
        fetch_env = servers["fetch"].setdefault("env", {})
        fetch_env["UV_CACHE_DIR"] = str(runtime_cache_root / "uv-cache")
        fetch_env["UV_TOOL_DIR"] = str(runtime_cache_root / "uv-tools")
    _add_startup_timeouts(servers)

    return servers


def _write_json(
    path: Path,
    payload: dict[str, Any],
    *,
    allowed_root: Path | None = None,
) -> None:
    """Write JSON under ``allowed_root`` (defaults to the repository root).

    Tests and ``--root`` projections may intentionally target an output
    directory outside the checkout; pass that directory as ``allowed_root``.
    """
    from scripts.engineering.common.repo_paths import (
        REPO_ROOT,
        ensure_path_within_root,
    )

    safe_root = (allowed_root or REPO_ROOT).expanduser().resolve(strict=False)
    confined_path = ensure_path_within_root(path, safe_root)
    relative_path = confined_path.relative_to(safe_root)
    safe_path = safe_root.joinpath(*relative_path.parts)
    safe_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    safe_path.write_text(rendered, encoding="utf-8")


def _load_existing_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.exists():
        return {}

    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}

    existing = json.loads(raw)
    if not isinstance(existing, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return existing


def _write_workspace_codex_settings(
    output_root: Path,
    workspace_root: Path,
    *,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> Path:
    settings_path = output_root / ".codex" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_json_object(
        settings_path, label="Codex workspace settings"
    )
    existing["mcpServers"] = deepcopy(
        _codex_runtime_servers(
            workspace_root, profile=profile, transport_mode=transport_mode
        )
    )
    _write_json(settings_path, existing, allowed_root=output_root)
    return settings_path


def _write_local_profile_state(
    output_root: Path,
    *,
    profile: str,
    transport_mode: str,
) -> Path:
    """Persist the selected machine-local profile for idempotent ensure runs."""
    state_path = output_root / ".codex" / "mcp-profile.json"
    _write_json(
        state_path,
        {"profile": profile, "transport_mode": transport_mode},
        allowed_root=output_root,
    )
    return state_path


def _write_devin_config(
    output_root: Path,
    workspace_root: Path,
    *,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> Path:
    """Write current Devin project settings and its dedicated MCP inventory."""
    settings_path = output_root / ".devin" / "config.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_json_object(settings_path, label="Devin workspace config")
    supported_keys = {"version", "permissions", "read_config_from", "hooks"}
    settings = {
        key: deepcopy(value) for key, value in existing.items() if key in supported_keys
    }
    settings.setdefault("version", 1)
    permissions = settings.setdefault("permissions", {})
    if not isinstance(permissions, dict):
        raise ValueError("Devin project permissions must be a JSON object")
    ask = permissions.setdefault("ask", [])
    if not isinstance(ask, list):
        raise ValueError("Devin project permissions.ask must be a JSON array")
    for rule in ("Read(**/.env*)", "Write(**/.env*)"):
        if rule not in ask:
            ask.append(rule)
    settings.setdefault("read_config_from", {"agents_standard": True})
    _write_json(settings_path, settings, allowed_root=output_root)

    # Devin CLI >=3000.3 reads MCP servers from a dedicated project file.
    del profile, transport_mode
    mcp_path = output_root / ".devin" / DEVIN_MCP_CONFIG_FILENAME
    _write_json(
        mcp_path,
        _render_devin_mcp_payload(workspace_root),
        allowed_root=output_root,
    )
    return settings_path


def _write_configs(
    output_root: Path,
    workspace_root: Path,
    *,
    qodo_only: bool = False,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> tuple[
    Path | None, Path | None, Path | None, Path, Path | None, Path | None, Path | None
]:
    # Tracked portable SSOT stays full stdio with POSIX wrappers so Windows and
    # Linux checkouts share one deterministic inventory (bash + .sh).
    # Local IDE projections may be profiled, host-native wrappers, and HTTP.
    full_servers = _canonical_servers(
        workspace_root,
        portable_workspace_paths=True,
        profile="full",
        wrapper_platform="posix",
    )
    local_servers = _apply_shared_transport(
        _canonical_servers(
            workspace_root,
            portable_workspace_paths=True,
            profile=profile,
        ),
        transport_mode=transport_mode,
    )
    codex_payload = {"mcpServers": deepcopy(full_servers)}
    vscode_payload = {"servers": deepcopy(local_servers)}
    cursor_payload = {"mcpServers": deepcopy(local_servers)}
    qodo_payload = {"mcpServers": deepcopy(local_servers)}
    zed_payload = {"mcpServers": deepcopy(full_servers)}

    mcp_path = output_root / ".mcp.json"
    scripts_ai_mcp_path = output_root / "scripts" / "ai" / ".mcp.json"
    vscode_path = output_root / ".vscode" / MCP_JSON_FILENAME
    cursor_path = output_root / ".cursor" / MCP_JSON_FILENAME
    qodo_path = output_root / ".qodo" / MCP_JSON_FILENAME
    zed_path = output_root / ".zed" / MCP_JSON_FILENAME
    codex_settings_path: Path | None = None
    devin_config_path: Path | None = None
    if not qodo_only:
        codex_settings_path = _write_workspace_codex_settings(
            output_root,
            workspace_root,
            profile=profile,
            transport_mode=transport_mode,
        )
        devin_config_path = _write_devin_config(
            output_root,
            workspace_root,
            profile=profile,
            transport_mode=transport_mode,
        )
        _write_json(mcp_path, codex_payload, allowed_root=output_root)
        if output_root.resolve() == workspace_root.resolve():
            _write_json(scripts_ai_mcp_path, codex_payload, allowed_root=output_root)
        _write_json(vscode_path, vscode_payload, allowed_root=output_root)
        _write_json(cursor_path, cursor_payload, allowed_root=output_root)
        _write_json(zed_path, zed_payload, allowed_root=output_root)
    _write_json(qodo_path, qodo_payload, allowed_root=output_root)
    return (
        mcp_path,
        vscode_path,
        cursor_path,
        qodo_path,
        zed_path,
        codex_settings_path,
        devin_config_path,
    )


def _gemini_server_config(server: dict[str, Any]) -> dict[str, Any]:
    rendered = deepcopy(server)
    startup_timeout_sec = rendered.pop("startup_timeout_sec", None)
    if startup_timeout_sec is not None:
        rendered["timeout"] = int(startup_timeout_sec) * 1000
    env_http_headers = rendered.pop("env_http_headers", None)
    if env_http_headers is not None:
        rendered["headers"] = {
            header: f"${env_name}" for header, env_name in env_http_headers.items()
        }
    if rendered.get("type") == "http" and "url" in rendered:
        rendered["httpUrl"] = rendered.pop("url")
        rendered.pop("type", None)
    return rendered


def _write_gemini_settings(
    output_root: Path,
    workspace_root: Path,
    *,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> Path:
    settings_path = output_root / ".gemini" / "settings.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_json_object(settings_path, label="Gemini settings")
    existing_servers = existing.get("mcpServers", {})
    if existing_servers and not isinstance(existing_servers, dict):
        raise ValueError(f"Gemini mcpServers must be a JSON object: {settings_path}")

    merged_servers = {
        name: server
        for name, server in existing_servers.items()
        if name not in REMOVED_MCP_SERVER_NAMES
    }
    local_servers = _apply_shared_transport(
        _canonical_servers(workspace_root, profile=profile),
        transport_mode=transport_mode,
    )
    for name, server in local_servers.items():
        merged_servers[name] = _gemini_server_config(server)
    # Drop only managed servers that are outside the selected local profile.
    # User-defined Gemini servers are outside our inventory and must survive.
    if profile != "full":
        allowed = set(local_servers)
        managed = set(_canonical_servers(workspace_root, profile="full"))
        merged_servers = {
            name: cfg
            for name, cfg in merged_servers.items()
            if name not in managed or name in allowed
        }

    existing["mcpServers"] = merged_servers
    _write_json(settings_path, existing, allowed_root=output_root)
    return settings_path


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _toml_key(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]+", value):
        return value
    return _toml_string(value)


def _toml_array(values: Sequence[Any]) -> str:
    rendered = []
    for value in values:
        if not isinstance(value, str):
            raise TypeError(
                f"Only string MCP args are supported in TOML output: {value!r}"
            )
        rendered.append(_toml_string(value))
    return "[" + ", ".join(rendered) + "]"


def _toml_inline_string_table(values: dict[str, Any]) -> str:
    rendered = [
        f"{_toml_key(key)} = {_toml_string(str(value))}"
        for key, value in values.items()
    ]
    return "{ " + ", ".join(rendered) + " }"


def _render_server_transport_lines(server: dict[str, Any]) -> list[str]:
    """Render command/url/args lines for one MCP server entry."""
    if "url" in server:
        return [f"url = {_toml_string(str(server['url']))}"]
    return [
        f"command = {_toml_string(str(server['command']))}",
        f"args = {_toml_array(server.get('args', []))}",
    ]


def _render_server_env_section(key: str, env: dict[str, Any]) -> list[str]:
    """Render the nested ``[mcp_servers.<key>.env]`` table."""
    lines = ["", f"[mcp_servers.{key}.env]"]
    for env_key in sorted(env):
        lines.append(f"{_toml_key(env_key)} = {_toml_string(str(env[env_key]))}")
    return lines


def _render_one_mcp_server_toml(name: str, server: dict[str, Any]) -> list[str]:
    """Render TOML lines for a single managed MCP server."""
    key = _toml_key(name)
    lines = ["", f"[mcp_servers.{key}]"]
    if "enabled" in server:
        lines.append(f"enabled = {'true' if bool(server['enabled']) else 'false'}")
    lines.extend(_render_server_transport_lines(server))
    if "startup_timeout_sec" in server:
        lines.append(f"startup_timeout_sec = {int(server['startup_timeout_sec'])}")
    env_http_headers = server.get("env_http_headers")
    if env_http_headers:
        lines.append(
            f"env_http_headers = {_toml_inline_string_table(env_http_headers)}"
        )
    env = server.get("env")
    if env:
        lines.extend(_render_server_env_section(key, env))
    return lines


def _render_codex_mcp_toml(servers: dict[str, dict[str, Any]]) -> str:
    lines = [
        MANAGED_BLOCK_BEGIN,
        "# Generated by scripts/ai/codex/setup_mcp.py. Do not edit this block manually.",
    ]
    for name, server in servers.items():
        lines.extend(_render_one_mcp_server_toml(name, server))

    lines.append("")
    lines.append(MANAGED_BLOCK_END)
    lines.append("")
    return "\n".join(lines)


def _strip_managed_mcp_blocks(content: str, managed_server_names: set[str]) -> str:
    section_re = re.compile(r"^\[mcp_servers\.([A-Za-z0-9_-]+)(?:\.env)?\]\s*$")
    kept: list[str] = []
    skip = False
    skip_marker_block = False

    for line in content.splitlines():
        stripped = line.strip()
        if stripped == MANAGED_BLOCK_BEGIN:
            skip_marker_block = True
            skip = False
            continue
        if skip_marker_block:
            if stripped == MANAGED_BLOCK_END:
                skip_marker_block = False
            continue

        section_match = section_re.match(stripped)
        if stripped.startswith("["):
            skip = bool(
                section_match and section_match.group(1) in managed_server_names
            )

        if not skip:
            kept.append(line)

    while kept and not kept[-1].strip():
        kept.pop()
    return "\n".join(kept)


def _write_codex_config(
    workspace_root: Path,
    *,
    profile: str = "full",
    transport_mode: str = "stdio",
) -> Path:
    servers = _codex_runtime_servers(
        workspace_root, profile=profile, transport_mode=transport_mode
    )
    config_dir = Path.home() / ".codex"
    config_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(config_dir, 0o700)
    config_path = config_dir / "config.toml"

    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    managed_or_retired_names = set(
        _canonical_servers(workspace_root, profile="full")
    ) | set(REMOVED_MCP_SERVER_NAMES)
    preserved = _strip_managed_mcp_blocks(existing, managed_or_retired_names)
    managed_block = _render_codex_mcp_toml(servers)

    if preserved:
        rendered = preserved.rstrip() + "\n\n" + managed_block
    else:
        rendered = managed_block

    config_path.write_text(rendered, encoding="utf-8")
    os.chmod(config_path, 0o600)
    return config_path


def _run_codex_validation(workspace_root: Path) -> None:
    codex_bin = shutil.which("codex")
    if codex_bin is None:
        print("codex CLI not found; wrote workspace configs only.")
        return
    result = subprocess.run(
        [codex_bin, "mcp", "list"],
        cwd=workspace_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"codex mcp list failed after writing configs: {stderr}")
    print("codex mcp list succeeded.")


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(argv) if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help=(
            "Directory where .mcp.json, .vscode/mcp.json, .cursor/mcp.json, "
            ".qodo/mcp.json, .zed/mcp.json, .codex/settings.json, "
            ".devin/config.json, and .devin/mcp_config.json "
            "should be written."
        ),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=REPO_ROOT,
        help="Workspace directory referenced inside the generated MCP server config.",
    )
    parser.add_argument(
        "--skip-codex",
        action="store_true",
        help=(
            "Skip Codex user-home config updates and post-write CLI validation; "
            "workspace .codex/settings.json is still written."
        ),
    )
    parser.add_argument(
        "--skip-codex-validation",
        action="store_true",
        help=(
            "Skip post-write Codex CLI validation while still updating "
            "~/.codex/config.toml unless --skip-codex-config is also passed."
        ),
    )
    parser.add_argument(
        "--skip-codex-config",
        action="store_true",
        help="Do not update ~/.codex/config.toml with the generated MCP servers.",
    )
    parser.add_argument(
        "--codex-only",
        action="store_true",
        help=(
            "Update only the managed MCP block in ~/.codex/config.toml; do not "
            "write workspace or other client projections."
        ),
    )
    parser.add_argument(
        "--skip-gemini-settings",
        action="store_true",
        help="Do not update .gemini/settings.json with the generated MCP servers.",
    )
    parser.add_argument(
        "--qodo-only",
        action="store_true",
        help="Write only .qodo/mcp.json and skip Codex/Gemini side effects.",
    )
    parser.add_argument(
        "--profile",
        choices=sorted(MCP_PROFILES),
        # Daily least-privilege default for local IDE projections.
        default=DEFAULT_LOCAL_PROFILE,
        help=(
            "Least-privilege local materialization profile for IDE/Codex local "
            "projections (stable|shared|core|ops|graph|full). "
            f"Default: {DEFAULT_LOCAL_PROFILE} (daily least-privilege local IDE). "
            "Tracked portable inventory (.mcp.json, scripts/ai/.mcp.json, "
            ".zed/mcp.json) and tracked .devin/mcp_config.json always stay full. "
            "Use --profile shared|graph|full when multi-client heavy tools are needed. "
            "Default transport remains shared HTTP for multi-client localhost plane."
        ),
    )
    parser.add_argument(
        "--transport-mode",
        choices=sorted(TRANSPORT_MODES),
        default=DEFAULT_LOCAL_TRANSPORT_MODE,
        help=(
            "Local projection transport: shared (default localhost HTTP for "
            "shared-servers catalog), stdio (wrappers; multiplies docker run per "
            "client), hybrid (catalog HTTP + others stdio). "
            "Tracked portable inventory always stays stdio."
        ),
    )
    parser.add_argument(
        "--persist-local-profile",
        action="store_true",
        help=(
            "Persist the selected profile/transport in the machine-local "
            ".codex/mcp-profile.json so future ensure runs keep this explicit "
            "operator choice. Implicit/default setup calls do not overwrite it."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Read-only parity check for tracked portable MCP projections "
            "(.mcp.json, scripts/ai/.mcp.json, .zed/mcp.json). Exits 0 when "
            "they match the canonical portable render; exits non-zero with a "
            "bounded diff summary otherwise. Performs no writes."
        ),
    )
    parser.add_argument(
        "--check-local",
        action="store_true",
        help=(
            "Read-only exact-parity check for profile-filtered local MCP "
            "projections. Uses .codex/mcp-profile.json when profile/transport "
            "are not supplied explicitly, preserves custom Gemini servers, "
            "and performs no writes or service startup."
        ),
    )
    args = parser.parse_args(raw_argv)
    _apply_setup_mcp_flag_shortcuts(args)
    output_root = args.root.absolute()
    workspace_root = args.workspace_root.absolute()
    if args.check and args.check_local:
        parser.error("--check and --check-local are mutually exclusive")
    if args.codex_only:
        if (
            args.check
            or args.check_local
            or args.qodo_only
            or args.persist_local_profile
        ):
            parser.error(
                "--codex-only cannot be combined with --check, --check-local, "
                "--qodo-only, or --persist-local-profile"
            )
        if args.skip_codex or args.skip_codex_config:
            parser.error("--codex-only cannot be combined with Codex skip flags")
        _write_codex_config(
            workspace_root,
            profile=args.profile,
            transport_mode=args.transport_mode,
        )
        print("Updated the private Codex user MCP managed block.")
        if not args.skip_codex_validation:
            _run_codex_validation(workspace_root)
        return 0
    if args.check:
        return _check_tracked_portable_projections(
            output_root,
            workspace_root,
            qodo_only=args.qodo_only,
        )
    if args.check_local:
        if args.qodo_only or args.persist_local_profile:
            parser.error(
                "--check-local cannot be combined with --qodo-only or "
                "--persist-local-profile"
            )
        profile, transport_mode = _resolve_local_check_selection(
            output_root,
            profile=args.profile,
            transport_mode=args.transport_mode,
            profile_explicit=_cli_option_was_provided(raw_argv, "--profile"),
            transport_explicit=_cli_option_was_provided(raw_argv, "--transport-mode"),
        )
        return _check_local_profile_projections(
            output_root,
            workspace_root,
            profile=profile,
            transport_mode=transport_mode,
        )
    written_paths = _write_configs(
        output_root,
        workspace_root,
        qodo_only=args.qodo_only,
        profile=args.profile,
        transport_mode=args.transport_mode,
    )
    if not args.qodo_only and args.persist_local_profile:
        profile_state_path = _write_local_profile_state(
            output_root,
            profile=args.profile,
            transport_mode=args.transport_mode,
        )
        print(f"Wrote {profile_state_path}")
    _print_written_mcp_paths(written_paths, qodo_only=args.qodo_only)
    _write_optional_side_configs(args, output_root, workspace_root)
    if not args.skip_codex and not args.skip_codex_validation:
        _run_codex_validation(workspace_root)
    return 0


def _apply_setup_mcp_flag_shortcuts(args: argparse.Namespace) -> None:
    if args.qodo_only:
        args.skip_codex = True
        args.skip_codex_config = True
        args.skip_gemini_settings = True
    if args.skip_codex:
        args.skip_codex_config = True


def _cli_option_was_provided(argv: Sequence[str], option: str) -> bool:
    """Return whether an argparse option was supplied in split or ``=`` form."""
    return any(
        argument == option or argument.startswith(f"{option}=") for argument in argv
    )


def _resolve_local_check_selection(
    output_root: Path,
    *,
    profile: str,
    transport_mode: str,
    profile_explicit: bool,
    transport_explicit: bool,
) -> tuple[str, str]:
    """Resolve check selection from explicit flags, then persisted local state."""
    state_path = output_root / ".codex" / "mcp-profile.json"
    if (profile_explicit and transport_explicit) or not state_path.is_file():
        return profile, transport_mode

    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid persisted MCP profile state: {state_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Persisted MCP profile state must be an object: {state_path}")

    resolved_profile = profile if profile_explicit else payload.get("profile", profile)
    resolved_transport = (
        transport_mode
        if transport_explicit
        else payload.get("transport_mode", transport_mode)
    )
    if resolved_profile not in MCP_PROFILES:
        raise ValueError(
            f"Invalid persisted MCP profile {resolved_profile!r}: {state_path}"
        )
    if resolved_transport not in TRANSPORT_MODES:
        raise ValueError(
            f"Invalid persisted MCP transport {resolved_transport!r}: {state_path}"
        )
    return str(resolved_profile), str(resolved_transport)


def _render_portable_mcp_payload(workspace_root: Path) -> dict[str, Any]:
    """Canonical tracked portable inventory (full profile, POSIX wrappers)."""
    full_servers = _canonical_servers(
        workspace_root,
        portable_workspace_paths=True,
        profile="full",
        wrapper_platform="posix",
    )
    return {"mcpServers": deepcopy(full_servers)}


def _render_devin_mcp_payload(workspace_root: Path) -> dict[str, Any]:
    """Canonical full Devin inventory using shared HTTP and Devin env syntax."""
    servers = _apply_shared_transport(
        _canonical_servers(
            workspace_root,
            portable_workspace_paths=True,
            profile=DEVIN_TRACKED_PROFILE,
            wrapper_platform="posix",
        ),
        transport_mode="shared",
    )
    for server in servers.values():
        server.pop("type", None)
        server.pop("startup_timeout_sec", None)
        env_http_headers = server.pop("env_http_headers", None)
        if isinstance(env_http_headers, dict):
            server["headers"] = {
                header: f"${{env:{env_name}}}"
                for header, env_name in env_http_headers.items()
            }
    return {"mcpServers": servers}


def _check_tracked_portable_projections(
    output_root: Path,
    workspace_root: Path,
    *,
    qodo_only: bool = False,
) -> int:
    """Compare tracked portable MCP projections without writing files.

    Returns 0 when all checked projections match the canonical render.
    """
    del qodo_only  # tracked portable check is independent of qodo-only mode
    expected_text = (
        json.dumps(
            _render_portable_mcp_payload(workspace_root),
            indent=2,
            ensure_ascii=True,
        )
        + "\n"
    )
    relative_paths = (
        Path(".mcp.json"),
        Path("scripts") / "ai" / ".mcp.json",
        Path(".zed") / MCP_JSON_FILENAME,
    )
    mismatches: list[str] = []
    for relative in relative_paths:
        path = output_root / relative
        if not path.is_file():
            mismatches.append(f"missing: {relative.as_posix()}")
            continue
        actual = path.read_text(encoding="utf-8")
        if actual != expected_text:
            actual_obj = json.loads(actual) if actual.strip() else {}
            expected_obj = json.loads(expected_text)
            actual_names = set(actual_obj.get("mcpServers") or {})
            expected_names = set(expected_obj.get("mcpServers") or {})
            only_actual = sorted(actual_names - expected_names)
            only_expected = sorted(expected_names - actual_names)
            shared_drift = sorted(
                name
                for name in (actual_names & expected_names)
                if (actual_obj.get("mcpServers") or {}).get(name)
                != (expected_obj.get("mcpServers") or {}).get(name)
            )
            detail_parts = [
                f"stale: {relative.as_posix()}",
                f"bytes actual={len(actual)} expected={len(expected_text)}",
            ]
            if only_actual:
                detail_parts.append(f"only_in_file={only_actual[:8]}")
            if only_expected:
                detail_parts.append(f"only_in_canonical={only_expected[:8]}")
            if shared_drift:
                detail_parts.append(f"server_drift={shared_drift[:12]}")
            mismatches.append("; ".join(detail_parts))

    devin_relative = Path(".devin") / DEVIN_MCP_CONFIG_FILENAME
    devin_path = output_root / devin_relative
    devin_expected_text = (
        json.dumps(
            _render_devin_mcp_payload(workspace_root),
            indent=2,
            ensure_ascii=True,
        )
        + "\n"
    )
    if not devin_path.is_file():
        mismatches.append(f"missing: {devin_relative.as_posix()}")
    elif devin_path.read_text(encoding="utf-8") != devin_expected_text:
        mismatches.append(
            f"stale: {devin_relative.as_posix()}; dedicated Devin MCP projection drift"
        )

    devin_settings_relative = Path(".devin") / "config.json"
    devin_settings_path = output_root / devin_settings_relative
    if not devin_settings_path.is_file():
        mismatches.append(f"missing: {devin_settings_relative.as_posix()}")
    else:
        devin_settings = json.loads(devin_settings_path.read_text(encoding="utf-8"))
        unsupported_keys = sorted(
            set(devin_settings)
            - {"version", "permissions", "read_config_from", "hooks"}
        )
        if unsupported_keys:
            mismatches.append(
                f"unsupported Devin project config keys: {unsupported_keys}"
            )
        if "mcpServers" in devin_settings:
            mismatches.append(
                "legacy Devin mcpServers must live in .devin/mcp_config.json"
            )

    if not mismatches:
        print(
            "[setup_mcp --check] ok: tracked portable MCP projections match "
            "canonical full/stdio/posix render"
        )
        for relative in relative_paths:
            print(f"  ok {relative.as_posix()}")
        print(f"  ok {devin_settings_relative.as_posix()}")
        print(f"  ok {devin_relative.as_posix()}")
        return 0

    print("[setup_mcp --check] FAIL: tracked portable MCP projections are stale")
    for item in mismatches:
        print(f"  - {item}")
    print(
        "Recovery: re-run Generate: MCP tracked manifests "
        "(scripts/ai/codex/setup_mcp.py --skip-codex --skip-gemini-settings)"
    )
    return 1


def _transport_signature(server: Any, *, gemini: bool = False) -> tuple[str, str]:
    """Return a secret-free transport signature for bounded drift reporting."""
    if not isinstance(server, dict):
        return ("invalid", "")
    url_key = "httpUrl" if gemini else "url"
    if server.get(url_key):
        return ("http", str(server[url_key]))
    if server.get("url"):
        return ("http", str(server["url"]))
    return ("stdio", str(server.get("command") or ""))


def _local_surface_mismatch(
    *,
    relative: Path,
    actual: dict[str, Any],
    expected: dict[str, Any],
    gemini: bool = False,
    managed_names: set[str] | None = None,
) -> str | None:
    """Return a bounded membership/transport delta for one local surface."""
    compared_actual = actual
    if managed_names is not None:
        compared_actual = {
            name: server for name, server in actual.items() if name in managed_names
        }

    actual_names = set(compared_actual)
    expected_names = set(expected)
    missing = sorted(expected_names - actual_names)
    extra = sorted(actual_names - expected_names)
    shared_names = actual_names & expected_names
    transport_drift = sorted(
        name
        for name in shared_names
        if _transport_signature(compared_actual[name], gemini=gemini)
        != _transport_signature(expected[name], gemini=gemini)
    )
    server_drift = sorted(
        name
        for name in shared_names
        if compared_actual[name] != expected[name] and name not in transport_drift
    )
    if not (missing or extra or transport_drift or server_drift):
        return None

    details = [f"stale: {relative.as_posix()}"]
    if missing:
        details.append(f"missing={missing[:12]}")
    if extra:
        details.append(f"extra={extra[:12]}")
    if transport_drift:
        details.append(f"transport_drift={transport_drift[:12]}")
    if server_drift:
        details.append(f"server_drift={server_drift[:12]}")
    return "; ".join(details)


def _read_local_server_mapping(
    path: Path,
    *,
    relative: Path,
    key: str,
) -> tuple[dict[str, Any] | None, str | None]:
    """Load one local JSON projection without exposing its values on failure."""
    if not path.is_file():
        return None, f"missing: {relative.as_posix()}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, f"invalid_json: {relative.as_posix()}"
    if not isinstance(payload, dict) or not isinstance(payload.get(key), dict):
        return None, f"invalid_mapping: {relative.as_posix()} key={key}"
    return payload[key], None


def _check_local_profile_projections(
    output_root: Path,
    workspace_root: Path,
    *,
    profile: str,
    transport_mode: str,
) -> int:
    """Check exact local profile/transport parity without writes or startup."""
    portable_expected = _apply_shared_transport(
        _canonical_servers(
            workspace_root,
            portable_workspace_paths=True,
            profile=profile,
        ),
        transport_mode=transport_mode,
    )
    codex_expected = _codex_runtime_servers(
        workspace_root,
        profile=profile,
        transport_mode=transport_mode,
    )
    gemini_expected = {
        name: _gemini_server_config(server)
        for name, server in _apply_shared_transport(
            _canonical_servers(workspace_root, profile=profile),
            transport_mode=transport_mode,
        ).items()
    }
    managed_gemini_names = set(
        _canonical_servers(workspace_root, profile="full")
    ) | set(REMOVED_MCP_SERVER_NAMES)

    surfaces = (
        (Path(".codex/settings.json"), "mcpServers", codex_expected),
        (Path(".vscode/mcp.json"), "servers", portable_expected),
        (Path(".cursor/mcp.json"), "mcpServers", portable_expected),
        (Path(".qodo/mcp.json"), "mcpServers", portable_expected),
    )
    mismatches: list[str] = []
    checked: list[Path] = []
    for relative, key, expected in surfaces:
        actual, load_error = _read_local_server_mapping(
            output_root / relative,
            relative=relative,
            key=key,
        )
        if load_error is not None:
            mismatches.append(load_error)
            continue
        assert actual is not None
        checked.append(relative)
        mismatch = _local_surface_mismatch(
            relative=relative,
            actual=actual,
            expected=expected,
        )
        if mismatch is not None:
            mismatches.append(mismatch)

    gemini_relative = Path(".gemini/settings.json")
    gemini_path = output_root / gemini_relative
    if gemini_path.exists():
        actual, load_error = _read_local_server_mapping(
            gemini_path,
            relative=gemini_relative,
            key="mcpServers",
        )
        if load_error is not None:
            mismatches.append(load_error)
        else:
            assert actual is not None
            checked.append(gemini_relative)
            mismatch = _local_surface_mismatch(
                relative=gemini_relative,
                actual=actual,
                expected=gemini_expected,
                gemini=True,
                managed_names=managed_gemini_names,
            )
            if mismatch is not None:
                mismatches.append(mismatch)

    selection = f"{profile}/{transport_mode}"
    if not mismatches:
        print(f"[setup_mcp --check-local] ok: local MCP projections match {selection}")
        for relative in checked:
            print(f"  ok {relative.as_posix()}")
        return 0

    print(
        "[setup_mcp --check-local] FAIL: local MCP projections do not match "
        f"{selection}"
    )
    for item in mismatches[:12]:
        print(f"  - {item}")
    print(
        "Recovery: re-run setup_mcp.py with the persisted --profile and "
        "--transport-mode, then restart clients that cache MCP configuration"
    )
    return 1


def _print_written_mcp_paths(
    written_paths: tuple[Path | None, ...], *, qodo_only: bool
) -> None:
    (
        mcp_path,
        vscode_path,
        cursor_path,
        qodo_path,
        zed_path,
        codex_settings_path,
        devin_config_path,
    ) = written_paths
    optional_paths = (
        mcp_path,
        vscode_path,
        cursor_path,
        zed_path,
        codex_settings_path,
        devin_config_path,
    )
    if not qodo_only:
        for path in optional_paths:
            if path is not None:
                print(f"Wrote {path}")
        if devin_config_path is not None:
            print(f"Wrote {devin_config_path.with_name(DEVIN_MCP_CONFIG_FILENAME)}")
    print(f"Wrote {qodo_path}")


def _write_optional_side_configs(
    args: argparse.Namespace, output_root: Path, workspace_root: Path
) -> None:
    if not args.skip_codex_config:
        codex_config_path = _write_codex_config(
            workspace_root,
            profile=args.profile,
            transport_mode=args.transport_mode,
        )
        print(f"Wrote {codex_config_path}")
    if not args.skip_gemini_settings:
        gemini_settings_path = _write_gemini_settings(
            output_root,
            workspace_root,
            profile=args.profile,
            transport_mode=args.transport_mode,
        )
        print(f"Wrote {gemini_settings_path}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
