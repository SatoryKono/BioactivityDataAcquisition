#!/usr/bin/env python3
"""Materialize local MCP JSON configs onto the shared HTTP plane (single instance).

Tracked portable inventory is normally stdio. On multi-client hosts, rewrite
workspace MCP JSON files to localhost Streamable HTTP URLs from
shared-servers.json so Zed/Cursor/Grok do not spawn N× stdio children.

Does not start the shared plane. Does not commit anything.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CATALOG = ROOT / "scripts/ops/runtime/mcp/shared-servers.json"
_DOT_MCP_JSON = ".mcp.json"
_MCP_JSON = "mcp.json"
TARGETS = (
    ROOT / _DOT_MCP_JSON,
    ROOT / ".zed" / _MCP_JSON,
    ROOT / "scripts" / "ai" / _DOT_MCP_JSON,
    ROOT / ".vscode" / _MCP_JSON,
    ROOT / ".cursor" / _MCP_JSON,
    ROOT / ".qodo" / _MCP_JSON,
)


def _catalog_http_servers(catalog: dict[str, object]) -> dict[str, dict[str, object]]:
    servers: dict[str, dict[str, object]] = {}
    raw_servers = catalog.get("servers") or {}
    if not isinstance(raw_servers, dict):
        return servers
    for name, entry in raw_servers.items():
        if not isinstance(entry, dict):
            continue
        port = int(entry["port"])
        path = str(entry.get("path") or "/mcp")
        timeout = int(entry.get("readiness_timeout_sec") or 180)
        servers[str(name)] = {
            "type": "http",
            "url": f"http://127.0.0.1:{port}{path}",
            "startup_timeout_sec": timeout,
        }
    return servers


def _client_headers_from_env_http_headers(
    env_http_headers: object,
) -> dict[str, str] | None:
    """Convert Codex-style env_http_headers to Grok/Cursor headers with ${VAR}.

    Tracked portable inventory keeps env_http_headers (env *names* only). Local
    multi-client JSON projections need expanded ``headers`` values so clients
    that do not understand env_http_headers still authenticate remote HTTPS
    servers (ref, deepwiki) when the process environment provides the keys.
    """
    if not isinstance(env_http_headers, dict):
        return None
    headers: dict[str, str] = {}
    for header, env_name in env_http_headers.items():
        name = str(env_name).strip()
        if not name:
            continue
        headers[str(header)] = f"${{{name}}}"
    return headers or None


def _tracked_https_entry(cfg: object) -> dict[str, object] | None:
    if not isinstance(cfg, dict):
        return None
    url = str(cfg.get("url") or "")
    if not url.startswith("https://"):
        return None
    entry: dict[str, object] = {"type": "http", "url": url}
    timeout = cfg.get("startup_timeout_sec")
    if isinstance(timeout, int) and timeout > 0:
        entry["startup_timeout_sec"] = timeout
    headers = cfg.get("headers")
    if isinstance(headers, dict) and headers:
        entry["headers"] = {str(key): str(value) for key, value in headers.items()}
        return entry
    projected = _client_headers_from_env_http_headers(cfg.get("env_http_headers"))
    if projected:
        entry["headers"] = projected
    return entry


def _merge_tracked_https_servers(
    servers: dict[str, dict[str, object]],
    tracked_path: Path,
) -> None:
    if not tracked_path.is_file():
        return
    tracked = json.loads(tracked_path.read_text(encoding="utf-8"))
    for name, cfg in (tracked.get("mcpServers") or {}).items():
        entry = _tracked_https_entry(cfg)
        if entry is not None:
            servers[name] = entry


def _payload_for_target(
    target: Path,
    servers: dict[str, dict[str, object]],
) -> dict[str, object]:
    key = "servers" if target.parent.name == ".vscode" else "mcpServers"
    return {key: servers}


def _write_targets(
    servers: dict[str, dict[str, object]],
    *,
    server_count: int,
) -> None:
    for target in TARGETS:
        if not target.parent.is_dir():
            continue
        payload = _payload_for_target(target, servers)
        text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)} ({server_count} servers)")


def selected_payload(payload: dict, entries: dict) -> dict:
    """Project approved entries only; preserve every unrelated server and setting."""
    result = deepcopy(payload)
    for key in ("mcpServers", "servers", "mcp_servers"):
        servers = result.get(key)
        if isinstance(servers, dict):
            for name, entry in entries.items():
                if name in servers:
                    previous = servers[name]
                    projected = deepcopy(entry)
                    for flag in ("enabled", "disabled", "alwaysAllow", "autoApprove", "enabled_tools", "disabled_tools", "allowedTools", "disabledTools", "startup_timeout_sec", "tool_timeout_sec", "timeout"):
                        if isinstance(previous, dict) and flag in previous:
                            projected[flag] = deepcopy(previous[flag])
                    servers[name] = projected
            return result
    raise ValueError("Target has no recognized MCP server map")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selected-entries", type=Path)
    args = parser.parse_args()
    if args.selected_entries is not None:
        entries = json.loads(args.selected_entries.read_text(encoding="utf-8"))
        selective_targets = (*TARGETS, ROOT / ".codex" / "settings.json", ROOT / ".devin" / "mcp_config.json")
        for target in selective_targets:
            if not target.is_file():
                continue
            original = target.read_bytes()
            payload = selected_payload(json.loads(original.decode("utf-8-sig")), entries)
            encoded = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            if encoded == original:
                continue
            if target.read_bytes() != original:
                raise RuntimeError("Concurrent config edit; projection stopped")
            target.write_bytes(encoded)
            print(f"projected selected entries: {target}")
        return 0
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    servers = _catalog_http_servers(catalog)
    local_file = ROOT / ".codex" / "mcp-local-transports.json"
    if local_file.is_file():
        for name, entry in json.loads(local_file.read_text(encoding="utf-8")).items():
            if name not in servers:
                raise ValueError("Local transport is outside the shared catalog")
            servers[name] = deepcopy(entry)
    # Preserve approved remote HTTPS servers from tracked .mcp.json when present.
    _merge_tracked_https_servers(servers, ROOT / _DOT_MCP_JSON)

    _write_targets(servers, server_count=len(servers))
    print("sample memory=", servers.get("memory"))
    print("sample mutmut=", servers.get("mutmut"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
