#!/usr/bin/env python3
"""Materialize local MCP JSON configs onto the shared HTTP plane (single instance).

Tracked portable inventory is normally stdio. On multi-client hosts, rewrite
workspace MCP JSON files to localhost Streamable HTTP URLs from
shared-servers.json so Zed/Cursor/Grok do not spawn N× stdio children.

Does not start the shared plane. Does not commit anything.
"""

from __future__ import annotations

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
            "url": f"http://127.0.0.1:{port}{path}",
            "startup_timeout_sec": timeout,
        }
    return servers


def _merge_tracked_https_servers(
    servers: dict[str, dict[str, object]],
    tracked_path: Path,
) -> None:
    if not tracked_path.is_file():
        return
    tracked = json.loads(tracked_path.read_text(encoding="utf-8"))
    for name, cfg in (tracked.get("mcpServers") or {}).items():
        if not isinstance(cfg, dict):
            continue
        url = str(cfg.get("url") or "")
        if url.startswith("https://"):
            servers[name] = {"type": "http", "url": url}


def _write_targets(text: str, *, server_count: int) -> None:
    for target in TARGETS:
        if not target.parent.is_dir():
            continue
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)} ({server_count} servers)")


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    servers = _catalog_http_servers(catalog)
    # Preserve approved remote HTTPS servers from tracked .mcp.json when present.
    _merge_tracked_https_servers(servers, ROOT / _DOT_MCP_JSON)

    payload = {"mcpServers": servers}
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    _write_targets(text, server_count=len(servers))
    print("sample memory=", servers.get("memory"))
    print("sample mutmut=", servers.get("mutmut"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
