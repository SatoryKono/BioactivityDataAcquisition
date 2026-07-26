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
MANAGED_BLOCK_BEGIN = "# === BEGIN MANAGED MCP SERVERS ==="
MANAGED_BLOCK_END = "# === END MANAGED MCP SERVERS ==="
CACHE_DIR_NAME = ".cache"
CODEX_RUNTIME_CACHE_DIR_NAME = "bioetl-mcp"
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
    "deepwiki",
    "ref",
)
# Multi-client daily: host-stable set + docker thrash servers that live on the
# shared HTTP plane (must match scripts/ops/runtime/mcp/shared-servers.json).
MCP_PROFILE_SHARED = MCP_PROFILE_STABLE + (
    "brave-search",
    "prometheus",
    "grafana",
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

# Localhost Streamable HTTP endpoints for multi-client shared plane (#6563/#6589).
# Keep in sync with scripts/ops/runtime/mcp/shared-servers.json (unit-tested).
MCP_SHARED_SERVER_ENDPOINTS: dict[str, str] = {
    "brave-search": "http://127.0.0.1:8811/mcp",
    "adr-analysis": "http://127.0.0.1:8813/mcp",
    "deja": "http://127.0.0.1:8814/mcp",
    "context7": "http://127.0.0.1:8815/mcp",
    "ast-grep": "http://127.0.0.1:8816/mcp",
    "github": "http://127.0.0.1:8820/mcp",
    "fetch": "http://127.0.0.1:8821/mcp",
    "prometheus": "http://127.0.0.1:8822/mcp",
    "grafana": "http://127.0.0.1:8823/mcp",
}
TRANSPORT_MODES = frozenset({"stdio", "shared", "hybrid"})
# Multi-client daily defaults for Codex ensure / local projections.
DEFAULT_LOCAL_PROFILE = "shared"
DEFAULT_LOCAL_TRANSPORT_MODE = "shared"
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
) -> dict[str, Any]:
    is_windows = os.name == "nt"
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
            f"Unknown MCP profile {profile!r}; expected one of "
            f"{sorted(MCP_PROFILES)}"
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
    servers: dict[str, dict[str, Any]] = {
        "memory": _npx_server(
            "@modelcontextprotocol/server-memory@2026.1.26",
            npm_cache_dir=npm_cache_dir,
        ),
        # Resolve repo root inside the wrapper so portable configs never pass
        # client-rewritten "." / foreign-OS absolute paths into Node path.resolve.
        "filesystem": _wrapper_command(
            "mcp_filesystem_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "fetch": _wrapper_command(
            "mcp_fetch_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "github": _wrapper_command(
            "github-mcp-wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "docker": _wrapper_command(
            "mcp_docker_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "context7": _wrapper_command(
            "mcp_context7_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "ast-grep": _wrapper_command(
            "mcp_ast_grep_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "mcp-code-interpreter": _wrapper_command(
            "mcp_code_interpreter_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "prometheus": _wrapper_command(
            "mcp_prometheus_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "grafana": _wrapper_command(
            "mcp_grafana_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "brave-search": _wrapper_command(
            "mcp_brave_search_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "neo4j-cypher": _wrapper_command(
            "mcp_neo4j_cypher_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "neo4j-memory": _wrapper_command(
            "mcp_neo4j_memory_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "mermaid": _wrapper_command(
            "mcp_mermaid_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "deja": _wrapper_command(
            "mcp_deja_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "adr-analysis": _wrapper_command(
            "mcp_adr_analysis_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "mutmut": _wrapper_command(
            "mcp_mutmut_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "code-analyzer": _wrapper_command(
            "mcp_code_analyzer_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "github-actions": _wrapper_command(
            "mcp_github_actions_wrapper",
            workspace_root,
            portable_workspace_paths=portable_workspace_paths,
        ),
        "deepwiki": _http_server("https://mcp.deepwiki.com/mcp"),
        "ref": _http_server("https://api.ref.tools/mcp"),
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
    servers["memory"]["env"]["MEMORY_FILE_PATH"] = str(memory_file_path)
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

    safe_path = ensure_path_within_root(path, allowed_root or REPO_ROOT)
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


def _write_devin_config(output_root: Path, workspace_root: Path) -> Path:
    """Write tracked Devin portable MCP projection (always full inventory)."""
    settings_path = output_root / ".devin" / "config.json"
    settings_path.parent.mkdir(parents=True, exist_ok=True)

    existing = _load_existing_json_object(settings_path, label="Devin workspace config")
    if not isinstance(existing.get("devin"), dict):
        existing["devin"] = {"org_id": "bioetl"}
    else:
        existing["devin"].setdefault("org_id", "bioetl")

    if not isinstance(existing.get("shell"), dict):
        existing["shell"] = {"setup_complete": True}
    else:
        existing["shell"].setdefault("setup_complete", True)

    # Tracked Devin config always materializes the full portable inventory.
    servers = deepcopy(
        _canonical_servers(
            workspace_root, portable_workspace_paths=True, profile="full"
        )
    )
    ref_server = servers.get("ref")
    if isinstance(ref_server, dict):
        ref_server.pop("env_http_headers", None)
        ref_server["headers"] = {
            "x-ref-api-key": f"${REF_API_KEY_ENV_VAR}",
        }
    existing["mcpServers"] = servers
    _write_json(settings_path, existing, allowed_root=output_root)
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
    # Tracked portable SSOT stays full stdio. Local IDE projections may be
    # profiled and optionally rewritten to localhost shared HTTP.
    full_servers = _canonical_servers(
        workspace_root,
        portable_workspace_paths=True,
        profile="full",
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
    vscode_path = output_root / ".vscode" / "mcp.json"
    cursor_path = output_root / ".cursor" / "mcp.json"
    qodo_path = output_root / ".qodo" / "mcp.json"
    zed_path = output_root / ".zed" / "mcp.json"
    codex_settings_path: Path | None = None
    devin_config_path: Path | None = None
    if not qodo_only:
        codex_settings_path = _write_workspace_codex_settings(
            output_root,
            workspace_root,
            profile=profile,
            transport_mode=transport_mode,
        )
        devin_config_path = _write_devin_config(output_root, workspace_root)
        _write_json(mcp_path, codex_payload, allowed_root=output_root)
        if output_root.resolve() == workspace_root.resolve():
            _write_json(
                scripts_ai_mcp_path, codex_payload, allowed_root=output_root
            )
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


def _render_codex_mcp_toml(servers: dict[str, dict[str, Any]]) -> str:
    lines = [
        MANAGED_BLOCK_BEGIN,
        "# Generated by scripts/ai/codex/setup_mcp.py. Do not edit this block manually.",
    ]
    for name, server in servers.items():
        key = _toml_key(name)
        lines.append("")
        lines.append(f"[mcp_servers.{key}]")
        if "enabled" in server:
            lines.append(
                f"enabled = {'true' if bool(server['enabled']) else 'false'}"
            )
        if "url" in server:
            lines.append(f"url = {_toml_string(str(server['url']))}")
        else:
            lines.append(f"command = {_toml_string(str(server['command']))}")
            lines.append(f"args = {_toml_array(server.get('args', []))}")

        if "startup_timeout_sec" in server:
            lines.append(f"startup_timeout_sec = {int(server['startup_timeout_sec'])}")

        env_http_headers = server.get("env_http_headers")
        if env_http_headers:
            lines.append(
                f"env_http_headers = {_toml_inline_string_table(env_http_headers)}"
            )

        env = server.get("env")
        if env:
            lines.append("")
            lines.append(f"[mcp_servers.{key}.env]")
            for env_key in sorted(env):
                lines.append(
                    f"{_toml_key(env_key)} = {_toml_string(str(env[env_key]))}"
                )

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
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.toml"

    existing = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    managed_or_retired_names = set(servers) | set(REMOVED_MCP_SERVER_NAMES)
    preserved = _strip_managed_mcp_blocks(existing, managed_or_retired_names)
    managed_block = _render_codex_mcp_toml(servers)

    if preserved:
        rendered = preserved.rstrip() + "\n\n" + managed_block
    else:
        rendered = managed_block

    config_path.write_text(rendered, encoding="utf-8")
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help=(
            "Directory where .mcp.json, .vscode/mcp.json, .cursor/mcp.json, "
            ".qodo/mcp.json, .zed/mcp.json, .codex/settings.json, and .devin/config.json "
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
        # Multi-client daily default: shared plane profile (not full inventory).
        # Docker thrash servers (grafana/prometheus/brave) ride shared HTTP.
        default=DEFAULT_LOCAL_PROFILE,
        help=(
            "Least-privilege local materialization profile for IDE/Codex local "
            "projections (stable|shared|core|ops|graph|full). "
            f"Default: {DEFAULT_LOCAL_PROFILE}. "
            "Tracked portable inventory (.mcp.json, scripts/ai/.mcp.json, "
            ".zed/mcp.json, .devin/config.json) always stays full. "
            "Use stable on 32 GiB Docker Desktop hosts to drop gateway MCP. "
            "Use shared + --transport-mode shared for multi-client HTTP plane."
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
    args = parser.parse_args(list(argv) if argv is not None else None)

    output_root = args.root.absolute()
    workspace_root = args.workspace_root.absolute()
    if args.qodo_only:
        args.skip_codex = True
        args.skip_codex_config = True
        args.skip_gemini_settings = True
    if args.skip_codex:
        args.skip_codex_config = True

    (
        mcp_path,
        vscode_path,
        cursor_path,
        qodo_path,
        zed_path,
        codex_settings_path,
        devin_config_path,
    ) = _write_configs(
        output_root,
        workspace_root,
        qodo_only=args.qodo_only,
        profile=args.profile,
        transport_mode=args.transport_mode,
    )
    if mcp_path is not None and not args.qodo_only:
        print(f"Wrote {mcp_path}")
    if vscode_path is not None and not args.qodo_only:
        print(f"Wrote {vscode_path}")
    if cursor_path is not None and not args.qodo_only:
        print(f"Wrote {cursor_path}")
    print(f"Wrote {qodo_path}")
    if zed_path is not None and not args.qodo_only:
        print(f"Wrote {zed_path}")
    if codex_settings_path is not None and not args.qodo_only:
        print(f"Wrote {codex_settings_path}")
    if devin_config_path is not None and not args.qodo_only:
        print(f"Wrote {devin_config_path}")
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

    if not args.skip_codex and not args.skip_codex_validation:
        _run_codex_validation(workspace_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
