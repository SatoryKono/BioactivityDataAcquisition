"""Load explicit machine-local MCP transport routes without embedding host values in Git."""

from __future__ import annotations

import fnmatch
import json
import os
from copy import deepcopy
from pathlib import Path

FLAGS = (
    "enabled",
    "disabled",
    "alwaysAllow",
    "autoApprove",
    "enabled_tools",
    "disabled_tools",
    "allowedTools",
    "disabledTools",
    "startup_timeout_sec",
    "tool_timeout_sec",
    "timeout",
)


def load_host_routes(workspace_root: Path, *, marker: Path | None = None) -> dict:
    marker = marker or Path(
        os.environ.get("PC_AGENT_MCP_ROUTES_FILE")
        or Path.home() / ".config/pc-agent/mcp-routes.json"
    )
    if not marker.is_file():
        return {}
    seen = set()
    for _ in range(3):
        resolved = marker.resolve()
        if resolved in seen:
            raise ValueError("Host MCP route indirection cycle")
        seen.add(resolved)
        data = json.loads(marker.read_text(encoding="utf-8-sig"))
        if "source" not in data:
            break
        source = Path(data["source"])
        marker = source if source.is_absolute() else marker.parent / source
    else:
        raise ValueError("Too many host MCP route indirections")
    root = workspace_root.resolve().as_posix().casefold().rstrip("/")
    result = {}
    for scope in data.get("workspaces", []):
        roots = [
            str(value).replace("\\", "/").casefold().rstrip("/")
            for value in scope.get("roots", [])
        ]
        patterns = [
            str(value).replace("\\", "/").casefold()
            for value in scope.get("patterns", [])
        ]
        if root not in roots and not any(
            fnmatch.fnmatchcase(root, pattern) for pattern in patterns
        ):
            continue
        for name, entry in scope.get("entries", {}).items():
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("command"), str)
                or not isinstance(entry.get("args"), list)
                or not all(isinstance(x, str) for x in entry["args"])
            ):
                raise ValueError("Invalid machine-local MCP transport entry")
            if "env" in entry or "headers" in entry:
                raise ValueError(
                    "Machine route must not contain credentials or headers"
                )
            result[name] = deepcopy(entry)
    return result


def merge_host_routes(
    servers: dict, workspace_root: Path, *, allowed: set[str]
) -> dict:
    result = deepcopy(servers)
    for name, entry in load_host_routes(workspace_root).items():
        if name not in allowed:
            raise ValueError("Host transport is outside the shared catalogue")
        if name not in result:
            continue
        projected = deepcopy(entry)
        for flag in FLAGS:
            if flag in result[name]:
                projected[flag] = deepcopy(result[name][flag])
        result[name] = projected
    return result
