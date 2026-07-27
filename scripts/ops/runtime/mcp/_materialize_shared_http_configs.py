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
TARGETS = (
    ROOT / ".mcp.json",
    ROOT / ".zed" / "mcp.json",
    ROOT / "scripts" / "ai" / ".mcp.json",
    ROOT / ".vscode" / "mcp.json",
    ROOT / ".cursor" / "mcp.json",
    ROOT / ".qodo" / "mcp.json",
)


def main() -> int:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    servers: dict[str, dict[str, object]] = {}
    for name, entry in catalog["servers"].items():
        port = int(entry["port"])
        path = str(entry.get("path") or "/mcp")
        timeout = int(entry.get("readiness_timeout_sec") or 180)
        servers[name] = {
            "url": f"http://127.0.0.1:{port}{path}",
            "startup_timeout_sec": timeout,
        }

    # Preserve approved remote HTTPS servers from tracked .mcp.json when present.
    tracked_path = ROOT / ".mcp.json"
    if tracked_path.is_file():
        tracked = json.loads(tracked_path.read_text(encoding="utf-8"))
        for name, cfg in (tracked.get("mcpServers") or {}).items():
            if isinstance(cfg, dict):
                url = str(cfg.get("url") or "")
                if url.startswith("https://"):
                    servers[name] = {"type": "http", "url": url}

    payload = {"mcpServers": servers}
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    for target in TARGETS:
        if not target.parent.is_dir():
            continue
        target.write_text(text, encoding="utf-8")
        print(f"wrote {target.relative_to(ROOT)} ({len(servers)} servers)")
    print("sample memory=", servers.get("memory"))
    print("sample mutmut=", servers.get("mutmut"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
