#!/usr/bin/env python3
"""Materialize the machine-local Devin MCP projection for the shared plane.

Writes only ``.devin/mcp_config.local.json`` (gitignored). Tracked project
settings remain in ``.devin/config.json`` and the full shared MCP inventory
remains in ``.devin/mcp_config.json``.

Usage (from repo root)::

    PYTHONPATH=. python3 scripts/ops/runtime/mcp/apply-shared-to-devin.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

REPO_ROOT = Path(__file__).resolve().parents[4]
_DEVIN_DIR = ".devin"
CATALOG_PATH = REPO_ROOT / "scripts/ops/runtime/mcp/shared-servers.json"
LOCAL_PATH = REPO_ROOT / _DEVIN_DIR / "mcp_config.local.json"
TRACKED_PATH = REPO_ROOT / _DEVIN_DIR / "mcp_config.json"

type JsonObject = dict[str, Any]


def _load_catalog() -> JsonObject:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"MCP catalog must contain an object: {CATALOG_PATH}")
    return cast(JsonObject, payload)


def _endpoint(entry: JsonObject) -> str:
    path = entry.get("path") or "/mcp"
    return f"http://127.0.0.1:{int(entry['port'])}{path}"


def _http_entry(url: str) -> JsonObject:
    return {"url": url}


def _load_tracked_servers() -> JsonObject:
    if not TRACKED_PATH.is_file():
        return {}
    raw = json.loads(TRACKED_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    servers = raw.get("mcpServers")
    return cast(JsonObject, servers) if isinstance(servers, dict) else {}


def build_local_servers(
    *,
    include_optional: bool = False,
) -> dict[str, JsonObject]:
    catalog = _load_catalog()
    servers = {
        name: dict(cast(JsonObject, entry))
        for name, entry in _load_tracked_servers().items()
        if isinstance(name, str) and isinstance(entry, dict)
    }

    catalog_servers = catalog.get("servers")
    if not isinstance(catalog_servers, dict):
        raise ValueError(f"MCP catalog lacks a servers object: {CATALOG_PATH}")
    for name, entry_raw in catalog_servers.items():
        if not isinstance(name, str) or not isinstance(entry_raw, dict):
            continue
        entry = cast(JsonObject, entry_raw)
        is_daily = entry.get("daily", True) is not False
        rendered = _http_entry(_endpoint(entry))
        if not include_optional and not is_daily:
            rendered["disabled"] = True
        servers[name] = rendered

    return servers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="Include catalog servers with daily=false (e.g. deja).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Repository root (default: detected).",
    )
    args = parser.parse_args(argv)
    root = args.root.resolve()
    local_path = root / _DEVIN_DIR / "mcp_config.local.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    servers = build_local_servers(include_optional=args.include_optional)
    payload: JsonObject = {"mcpServers": servers}

    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    local_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {local_path} ({len(servers)} mcpServers)")
    http_names = sorted(
        n for n, s in servers.items() if s.get("type") == "http" or s.get("url")
    )
    print("HTTP:", ", ".join(http_names) or "(none)")
    disabled = sorted(
        name for name, server in servers.items() if server.get("disabled")
    )
    print("Daily-disabled optional servers:", ", ".join(disabled) or "(none)")
    print("Restart Devin to load mcp_config.local.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
