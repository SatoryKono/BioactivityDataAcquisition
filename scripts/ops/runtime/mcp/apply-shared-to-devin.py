#!/usr/bin/env python3
"""Materialize machine-local Devin MCP projection onto the shared HTTP plane.

Writes only ``.devin/config.local.json`` (gitignored). Tracked
``.devin/config.json`` stays full portable stdio SSOT.

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
LOCAL_PATH = REPO_ROOT / _DEVIN_DIR / "config.local.json"
TRACKED_PATH = REPO_ROOT / _DEVIN_DIR / "config.json"

# Gateway thrash leaders — omit from daily multi-client Devin local projection.
DAILY_DISABLE = frozenset(
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
        "github-actions",
    }
)

type JsonObject = dict[str, Any]


def _load_catalog() -> JsonObject:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"MCP catalog must contain an object: {CATALOG_PATH}")
    return cast(JsonObject, payload)


def _endpoint(entry: JsonObject) -> str:
    path = entry.get("path") or "/mcp"
    return f"http://127.0.0.1:{int(entry['port'])}{path}"


def _http_entry(url: str, *, timeout: int = 60) -> JsonObject:
    return {
        "type": "http",
        "url": url,
        "startup_timeout_sec": timeout,
    }


def _normalize_tracked_host_entry(entry: JsonObject) -> JsonObject:
    """Prefer bash wrappers on Linux local for PowerShell-oriented tracked entries."""
    normalized = dict(entry)
    args = normalized.get("args")
    if isinstance(args, list) and args and str(args[0]).endswith(".ps1"):
        normalized["command"] = "bash"
        normalized["args"] = [str(args[0]).replace(".ps1", ".sh")]
    return normalized


def _seed_tracked_host_servers(tracked: JsonObject) -> dict[str, JsonObject]:
    servers: dict[str, JsonObject] = {}
    for name in ("memory", "filesystem"):
        entry = tracked.get(name)
        if isinstance(entry, dict):
            servers[name] = _normalize_tracked_host_entry(cast(JsonObject, entry))
    return servers


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
    # Prefer tracked portable inventory for non-catalog host wrappers that
    # remain useful (memory/filesystem) when present.
    servers = _seed_tracked_host_servers(_load_tracked_servers())

    catalog_servers = catalog.get("servers")
    if not isinstance(catalog_servers, dict):
        raise ValueError(f"MCP catalog lacks a servers object: {CATALOG_PATH}")
    for name, entry_raw in catalog_servers.items():
        if not isinstance(name, str) or not isinstance(entry_raw, dict):
            continue
        entry = cast(JsonObject, entry_raw)
        is_daily = entry.get("daily", True) is not False
        if not include_optional and not is_daily:
            continue
        if name in DAILY_DISABLE:
            continue
        servers[name] = _http_entry(_endpoint(entry))

    # Explicitly document disabled thrash leaders so operators see intent.
    # (Devin may still merge tracked; absence is the daily contract.)
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
    local_path = root / _DEVIN_DIR / "config.local.json"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    existing: JsonObject = {}
    if local_path.is_file():
        try:
            raw_existing = json.loads(local_path.read_text(encoding="utf-8"))
            existing = (
                cast(JsonObject, raw_existing)
                if isinstance(raw_existing, dict)
                else {}
            )
        except json.JSONDecodeError:
            existing = {}

    servers = build_local_servers(include_optional=args.include_optional)
    # Preserve non-mcp keys (permissions, etc.) from existing local config.
    payload = dict(existing)
    payload["mcpServers"] = servers
    if "permissions" not in payload:
        payload["permissions"] = {
            "allow": [
                "Exec(gh)",
                "Exec(git)",
                "Exec(python)",
                "Exec(python3)",
                "Exec(pytest)",
                "Exec(uv run)",
                "Exec(ls)",
                "Exec(find)",
            ]
        }

    rendered = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    local_path.write_text(rendered, encoding="utf-8")
    print(f"Wrote {local_path} ({len(servers)} mcpServers)")
    http_names = sorted(
        n for n, s in servers.items() if s.get("type") == "http" or s.get("url")
    )
    print("HTTP:", ", ".join(http_names) or "(none)")
    disabled = sorted(DAILY_DISABLE)
    print("Daily-disabled thrash leaders:", ", ".join(disabled))
    print("Restart Devin to load config.local.json.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
